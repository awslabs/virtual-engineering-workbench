import importlib
import json
import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from urllib.parse import quote

import assertpy
import pytest

from app.provisioning.domain.commands.product_provisioning import (
    authorize_user_ip_address_command,
    launch_product_command,
    remove_provisioned_product_command,
    remove_provisioned_products_command,
    start_provisioned_product_update_command,
)
from app.provisioning.domain.commands.provisioned_product_state import (
    initiate_provisioned_product_start_command,
    initiate_provisioned_product_stop_command,
    initiate_provisioned_products_stop_command,
)
from app.provisioning.domain.commands.user_profile import update_user_profile_command
from app.provisioning.domain.model import (
    additional_configuration,
    maintenance_window,
    network_subnet,
    product_status,
    provisioned_product,
    provisioned_product_output,
    provisioning_parameter,
    user_credential,
    user_profile,
)
from app.provisioning.domain.query_services import (
    products_domain_query_service,
    provisioned_products_domain_query_service,
    provisioning_infrastructure_domain_query_service,
    user_profile_domain_query_service,
    versions_domain_query_service,
)
from app.provisioning.domain.read_models import (
    component_version_detail,
    product,
    version,
)
from app.provisioning.domain.value_objects import (
    product_id_value_object,
    product_name_value_object,
    product_status_value_object,
    product_version_name_value_object,
    project_id_value_object,
    provisioned_product_id_value_object,
    provisioned_product_stage_value_object,
    provisioned_product_type_value_object,
    region_value_object,
    user_id_value_object,
    version_stage_value_object,
)
from app.provisioning.entrypoints.api import bootstrapper
from app.provisioning.entrypoints.api.model import api_model
from app.shared.adapters.feature_toggling import (
    frontend_feature,
    frontend_feature_toggles,
)
from app.shared.adapters.message_bus import in_memory_command_bus

TEST_OS_VERSION = "Ubuntu 24"
TEST_COMPONENT_VERSION_DETAILS = [
    component_version_detail.ComponentVersionDetail(
        componentName="VS Code",
        componentVersionType=component_version_detail.ComponentVersionEntryType.Main,
        softwareVendor="Microsoft",
        softwareVersion="1.87.0",
    )
]
TEST_COMPONENT_VERSION_DETAILS_DUMPED = [cvd.model_dump() for cvd in TEST_COMPONENT_VERSION_DETAILS]


@pytest.fixture
def mocked_products_domain_query_service() -> products_domain_query_service.ProductsDomainQueryService:
    products_domain_query_service_mock = unittest.mock.create_autospec(
        spec=products_domain_query_service.ProductsDomainQueryService
    )
    products_domain_query_service_mock.get_available_products.return_value = [
        product.Product(
            projectId="proj-12345",
            productId=f"prod-{str(i)}",
            technologyId="tech-1",
            technologyName="Test technology",
            productName=f"Product {str(i)}",
            productType=product.ProductType.VirtualTarget,
            availableStages=[
                product.ProductStage.DEV,
                product.ProductStage.QA,
                product.ProductStage.PROD,
            ],
            availableRegions=["us-east-1", "eu-west-3"],
            availableTools=set(["VS Code", "Pied Piper"]),
            availableOSVersions=set(["Ubuntu 24"]),
            lastUpdateDate=datetime.now(timezone.utc).isoformat(),
        )
        for i in range(5)
    ]

    return products_domain_query_service_mock


@pytest.fixture()
def mock_provisioned_product():
    def _mock_provisioned_product(provisioned_product_id, product_id, user_id):
        return provisioned_product.ProvisionedProduct(
            projectId="proj-12345",
            provisionedProductId=provisioned_product_id,
            provisionedProductName="vt-name",
            provisionedProductType=provisioned_product.ProvisionedProductType.VirtualTarget,
            userId=user_id,
            userDomains=["mock-user-domain"],
            status=product_status.ProductStatus.Running,
            statusReason=None,
            productId=product_id,
            productName="Product Name",
            technologyId="tech-12345",
            versionId="vers-1",
            versionName="vers-name",
            newVersionName="new-vers-name",
            newVersionId="new-vers-id",
            awsAccountId="12345678912",
            accountId="0987654321",
            stage=provisioned_product.ProvisionedProductStage.QA,
            region="us-east-1",
            amiId="mock-ami-id",
            scProductId="sc-product-id",
            scProvisioningArtifactId="sc-vers-id",
            scProvisionedProductId=None,
            provisioningParameters=[provisioning_parameter.ProvisioningParameter(key="mock-param-key")],
            outputs=[
                provisioned_product_output.ProvisionedProductOutput(
                    outputKey="outputs-key",
                    outputValue="outputs-value",
                )
            ],
            sshKeyPath="test",
            userCredentialName="test2",
            experimental=True,
            componentVersionDetails=TEST_COMPONENT_VERSION_DETAILS,
            osVersion=TEST_OS_VERSION,
            createDate="2023-09-01T00:00:00+00:00",
            lastUpdateDate="2023-09-01T00:00:00+00:00",
            createdBy=user_id,
            lastUpdatedBy=user_id,
        )

    return _mock_provisioned_product


@pytest.fixture
def mocked_versions_domain_query_service(
    mock_product_version,
) -> versions_domain_query_service.VersionsDomainQueryService:
    versions_domain_query_service_mock = unittest.mock.create_autospec(
        spec=versions_domain_query_service.VersionsDomainQueryService
    )
    versions_domain_query_service_mock.get_versions_ready_for_provisioning.return_value = [
        mock_product_version(),
        mock_product_version(),
    ]
    return versions_domain_query_service_mock


@pytest.fixture
def mocked_virtual_targets_domain_query_service(
    mock_provisioned_product,
    mock_product_version,
) -> provisioned_products_domain_query_service.ProvisionedProductsDomainQueryService:
    virtual_targets_domain_query_service_mock = unittest.mock.create_autospec(
        spec=provisioned_products_domain_query_service.ProvisionedProductsDomainQueryService
    )
    virtual_targets_domain_query_service_mock.get_provisioned_products.return_value = [
        mock_provisioned_product(f"vt-{i}", f"prod-{i}", "user-1") for i in range(5)
    ]
    virtual_targets_domain_query_service_mock.get_all_provisioned_products.return_value = [
        mock_provisioned_product(f"vt-{i}", f"prod-{i}", "user-1") for i in range(5)
    ], {"string": "NextPagingKey"}
    virtual_targets_domain_query_service_mock.get_provisioned_product.return_value = (
        mock_provisioned_product("vt-1", "prod-1", "user-1"),
        mock_product_version(),
    )
    virtual_targets_domain_query_service_mock.get_provisioned_product_ssh_key.return_value = "abc"
    virtual_targets_domain_query_service_mock.get_provisioned_product_user_credentials.return_value = (
        user_credential.UserCredential(username="user", password="pwd")
    )
    virtual_targets_domain_query_service_mock.get_paginated_provisioned_products.return_value = [
        mock_provisioned_product(f"vt-{i}", f"prod-{i}", "user-1") for i in range(5)
    ], {"string": "NextPagingKey"}
    return virtual_targets_domain_query_service_mock


@pytest.fixture()
def get_test_user_profile():
    def _inner(
        user_id: str = "T0011AA",
        preferred_region: str = "us-east-1",
    ):
        return user_profile.UserProfile(
            userId=user_id,
            preferredRegion=preferred_region,
            preferredNetwork="x",
            preferredMaintenanceWindows=[
                maintenance_window.MaintenanceWindow(
                    day=maintenance_window.WeekDay.MONDAY,
                    startTime="00:00",
                    endTime="04:00",
                    userId=user_id,
                )
            ],
            createDate="2024-01-18T00:00:00+00:00",
            lastUpdateDate="2024-01-18T00:00:00+00:00",
        )

    return _inner


@pytest.fixture
def mocked_user_profile_domain_query_service(
    get_test_user_profile,
) -> user_profile_domain_query_service.UserProfileDomainQueryService:
    mock_srv = unittest.mock.create_autospec(spec=user_profile_domain_query_service.UserProfileDomainQueryService)
    mock_srv.get_user_configuration.return_value = (
        get_test_user_profile(),
        ["us-east-1", "eu-west-3"],
        [
            frontend_feature.FrontendFeature(
                version="v0.0.0",
                feature="EnabledFeature",
                enabled=True,
            )
        ],
        "3.12",
    )
    mock_srv.get_users_within_maintenance_window.return_value = [
        "T0011AA",
        "T0011AB",
        "T0011AC",
    ]
    return mock_srv


@pytest.fixture
def mock_product_version():
    def _inner(
        stage: version.VersionStage = version.VersionStage.DEV,
        region: str = "us-east-1",
        version_id: str = "ver-123",
    ):
        return version.Version(
            projectId="proj-123",
            productId="prod-123",
            technologyId="tech-123",
            versionId=version_id,
            versionName="v1.0.0",
            versionDescription="Initial release",
            awsAccountId="001234567890",
            accountId="acc-123",
            stage=stage,
            region=region,
            amiId="ami-123",
            scProductId="sc-prod-123",
            scProvisioningArtifactId="sc-pa-123",
            isRecommendedVersion=True,
            componentVersionDetails=TEST_COMPONENT_VERSION_DETAILS,
            osVersion=TEST_OS_VERSION,
            parameters=[
                version.VersionParameter(
                    parameterKey="SomeParam",
                    defaultValue="some-default",
                    parameterType="String",
                    parameterMetaData=version.ParameterMetadata(
                        label="Some Parameter",
                        optionLabels={
                            "val-1": "Value 1",
                            "val-2": "Value 2",
                        },
                        optionWarnings={"val-1": "Some Warning"},
                    ),
                    parameterConstraints=version.ParameterConstraints(allowedValues=["val-1", "val-2"]),
                ),
                version.VersionParameter(
                    parameterKey="SomeTechParam",
                    defaultValue="/workbench/autosar/adaptive/ami-id/v1-3-x",
                    parameterType="AWS::SSM::Parameter::Value<String>",
                ),
            ],
            lastUpdateDate="2023-12-05",
        )

    return _inner


@pytest.fixture
def mocked_feature_service():
    srv = unittest.mock.create_autospec(spec=frontend_feature_toggles.FrontendFeatureToggles)
    return srv


@pytest.fixture
def mocked_provisioning_infra_qs() -> (
    provisioning_infrastructure_domain_query_service.ProvisioningInfrastructureDomainQueryService
):
    m = unittest.mock.create_autospec(
        spec=provisioning_infrastructure_domain_query_service.ProvisioningInfrastructureDomainQueryService
    )
    m.get_provisioning_subnets_in_account.return_value = [
        network_subnet.NetworkSubnet(
            AvailabilityZone="az-123",
            AvailableIpAddressCount=1,
            SubnetId="sub-123",
            Tags=[],
            CidrBlock="192.168.1.0/24",
            VpcId="vpc-123",
        )
    ]
    return m


@pytest.fixture
def mocked_dependencies(
    mocked_products_domain_query_service,
    mocked_versions_domain_query_service,
    mocked_authorize_user_ip_address_handler,
    mocked_launch_provisioned_product_handler,
    mocked_virtual_targets_domain_query_service,
    mocked_remove_provisioned_product_handler,
    mocked_remove_provisioned_products_handler,
    mocked_start_provisioned_product_handler,
    mocked_stop_provisioned_product_handler,
    mocked_stop_provisioned_products_handler,
    mocked_update_user_profile_handler,
    mocked_user_profile_domain_query_service,
    mocked_update_provisioned_product_handler,
    mocked_feature_service,
    mocked_provisioning_infra_qs,
) -> bootstrapper.Dependencies:
    return bootstrapper.Dependencies(
        command_bus=in_memory_command_bus.InMemoryCommandBus(
            logger=unittest.mock.MagicMock(),
        )
        .register_handler(
            authorize_user_ip_address_command.AuthorizeUserIpAddressCommand,
            mocked_authorize_user_ip_address_handler,
        )
        .register_handler(
            launch_product_command.LaunchProductCommand,
            mocked_launch_provisioned_product_handler,
        )
        .register_handler(
            remove_provisioned_product_command.RemoveProvisionedProductCommand,
            mocked_remove_provisioned_product_handler,
        )
        .register_handler(
            remove_provisioned_products_command.RemoveProvisionedProductsCommand,
            mocked_remove_provisioned_products_handler,
        )
        .register_handler(
            initiate_provisioned_product_start_command.InitiateProvisionedProductStartCommand,
            mocked_start_provisioned_product_handler,
        )
        .register_handler(
            initiate_provisioned_product_stop_command.InitiateProvisionedProductStopCommand,
            mocked_stop_provisioned_product_handler,
        )
        .register_handler(
            initiate_provisioned_products_stop_command.InitiateProvisionedProductsStopCommand,
            mocked_stop_provisioned_products_handler,
        )
        .register_handler(
            update_user_profile_command.UpdateUserProfileCommand,
            mocked_update_user_profile_handler,
        )
        .register_handler(
            start_provisioned_product_update_command.StartProvisionedProductUpdateCommand,
            mocked_update_provisioned_product_handler,
        ),
        products_domain_qry_srv=mocked_products_domain_query_service,
        versions_domain_qry_srv=mocked_versions_domain_query_service,
        virtual_targets_domain_qry_srv=mocked_virtual_targets_domain_query_service,
        user_profile_domain_qry_srv=mocked_user_profile_domain_query_service,
        feature_qry_srv=mocked_feature_service,
        application_version_frontend="3.12",
        application_version_backend="3.12",
        prov_infra_qry_srv=mocked_provisioning_infra_qs,
    )


@pytest.fixture
def mocked_authorize_user_ip_address_handler():
    return unittest.mock.MagicMock()


@pytest.fixture
def mocked_launch_provisioned_product_handler():
    return unittest.mock.MagicMock()


@pytest.fixture
def mocked_update_provisioned_product_handler():
    return unittest.mock.MagicMock()


@pytest.fixture
def mocked_remove_provisioned_product_handler():
    return unittest.mock.MagicMock()


@pytest.fixture
def mocked_remove_provisioned_products_handler():
    return unittest.mock.MagicMock()


@pytest.fixture
def mocked_start_provisioned_product_handler():
    return unittest.mock.MagicMock()


@pytest.fixture
def mocked_stop_provisioned_product_handler():
    return unittest.mock.MagicMock()


@pytest.fixture
def mocked_stop_provisioned_products_handler():
    return unittest.mock.MagicMock()


@pytest.fixture
def mocked_update_user_profile_handler():
    return unittest.mock.MagicMock()


def test_get_available_products(lambda_context, authenticated_event, mocked_dependencies):
    # ARRANGE
    from app.provisioning.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    project_id = "proj-12345"
    minimal_event = authenticated_event(
        None,
        f"/projects/{project_id}/products/available",
        "GET",
        {"productType": "VirtualTarget", "filter": "p-123"},
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetAvailableProductsResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.availableProducts).is_not_none()
    assertpy.assert_that(len(response.availableProducts)).is_equal_to(5)


def test_launch_product(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_launch_provisioned_product_handler,
):
    # ARRANGE
    from app.provisioning.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    project_id = "proj-12345"
    request = api_model.LaunchProductRequest(
        productType="VirtualTarget",
        productId="prod-123",
        versionId="vers-123",
        provisioningParameters=[api_model.ProvisioningParameter(key="a", value="b")],
        stage="dev",
        region="us-east-1",
    )
    minimal_event = authenticated_event(
        request.model_dump_json(),
        f"/projects/{project_id}/products/provisioned",
        "POST",
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(202)
    response = api_model.LaunchProductResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    mocked_launch_provisioned_product_handler.assert_called_once()


@patch(
    "app.provisioning.domain.command_handlers.product_provisioning.launch.handle",
    autospec=True,
)
@patch("uuid.uuid4", unittest.mock.MagicMock(return_value="123"))
def test_launch_product_internal(
    command_handler_mock,
    lambda_context,
    authenticated_event,
):
    # ARRANGE
    from app.provisioning.entrypoints.api import handler

    importlib.reload(handler)

    project_id = "proj-12345"
    request = api_model.LaunchProductRequestInternal(
        productType="VirtualTarget",
        productId="prod-123",
        versionId="vers-123",
        provisioningParameters=[api_model.ProvisioningParameter(key="a", value="b")],
        stage="dev",
        region="us-east-1",
        userName="TEST_USER",
        provisionedCompoundProductId="cpp-123",
        deploymentOption=api_model.DeploymentOption.MULTI_AZ,
    )
    minimal_event = authenticated_event(
        request.model_dump_json(),
        f"/internal/projects/{project_id}/products/provisioned",
        "POST",
        iam_auth=True,
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(202)
    response = api_model.LaunchProductResponseInternal.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.provisionedProductId).is_equal_to("vew-pp-123")
    command_handler_mock.assert_called_once()
    cmd = command_handler_mock.call_args.kwargs.get("command")
    assertpy.assert_that(cmd.deployment_option.value).is_equal_to("MULTI_AZ")


@patch(
    "app.provisioning.domain.command_handlers.product_provisioning.launch.handle",
    autospec=True,
)
@patch("uuid.uuid4", unittest.mock.MagicMock(return_value="123"))
def test_launch_product_internal_with_single_az_deployment_option(
    command_handler_mock,
    lambda_context,
    authenticated_event,
):
    # ARRANGE
    from app.provisioning.entrypoints.api import handler

    importlib.reload(handler)

    project_id = "proj-12345"
    request = api_model.LaunchProductRequestInternal(
        productType="VirtualTarget",
        productId="prod-123",
        versionId="vers-123",
        provisioningParameters=[api_model.ProvisioningParameter(key="a", value="b")],
        stage="dev",
        region="us-east-1",
        userName="TEST_USER",
        provisionedCompoundProductId="cpp-123",
        deploymentOption=api_model.DeploymentOption.SINGLE_AZ,
    )
    minimal_event = authenticated_event(
        request.model_dump_json(),
        f"/internal/projects/{project_id}/products/provisioned",
        "POST",
        iam_auth=True,
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(202)
    response = api_model.LaunchProductResponseInternal.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    command_handler_mock.assert_called_once()
    cmd = command_handler_mock.call_args.kwargs.get("command")
    assertpy.assert_that(cmd.deployment_option.value).is_equal_to("SINGLE_AZ")


def test_launch_experimental_product(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_launch_provisioned_product_handler,
):
    # ARRANGE
    from app.provisioning.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    project_id = "proj-12345"
    request = api_model.LaunchProductRequest(
        productType="VirtualTarget",
        productId="prod-123",
        versionId="vers-123",
        provisioningParameters=[api_model.ProvisioningParameter(key="Experimental", value="True")],
        stage="qa",
        region="us-east-1",
    )
    minimal_event = authenticated_event(
        request.model_dump_json(),
        f"/projects/{project_id}/products/provisioned",
        "POST",
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(202)
    response = api_model.LaunchProductResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    mocked_launch_provisioned_product_handler.assert_called_once()


def test_launch_product_with_additional_configurations(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_launch_provisioned_product_handler,
):
    # ARRANGE
    from app.provisioning.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    project_id = "proj-12345"
    request = api_model.LaunchProductRequest(
        productType="VirtualTarget",
        productId="prod-123",
        versionId="vers-123",
        provisioningParameters=[api_model.ProvisioningParameter(key="a", value="b")],
        additionalConfigurations=[
            api_model.AdditionalConfiguration(
                type=additional_configuration.ProvisionedProductConfigurationTypeEnum.VVPLProvisionedProductConfiguration,
                parameters=[api_model.AdditionalConfigurationParameter(key="a", value="b")],
            )
        ],
        stage="dev",
        region="us-east-1",
    )
    minimal_event = authenticated_event(
        request.model_dump_json(),
        f"/projects/{project_id}/products/provisioned",
        "POST",
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(202)
    response = api_model.LaunchProductResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    mocked_launch_provisioned_product_handler.assert_called_once()


def test_update_provisioned_product(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_update_provisioned_product_handler,
):
    # ARRANGE
    from app.provisioning.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    project_id = "proj-12345"
    provisioned_product_id = "pp-123"
    request = api_model.UpdateProvisionedProductRequest(
        provisioningParameters=[api_model.ProvisioningParameter(key="a", value="b")],
        versionId="vers-123",
    )
    minimal_event = authenticated_event(
        request.model_dump_json(),
        f"/projects/{project_id}/products/provisioned/{provisioned_product_id}/update",
        "PUT",
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(202)
    response = api_model.UpdateProvisionedProductResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    mocked_update_provisioned_product_handler.assert_called_once()


def test_remove_provisioned_product(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_remove_provisioned_product_handler,
):
    # ARRANGE
    from app.provisioning.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    project_id = "proj-12345"
    minimal_event = authenticated_event(
        None,
        f"/projects/{project_id}/products/provisioned/123/remove",
        "PUT",
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.RemoveProvisionedProductResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    mocked_remove_provisioned_product_handler.assert_called_once()


@patch(
    "app.provisioning.domain.command_handlers.product_provisioning.remove.handle",
    autospec=True,
)
def test_remove_provisioned_product_internal(command_handler_mock, lambda_context, authenticated_event):
    # ARRANGE
    from app.provisioning.entrypoints.api import handler

    importlib.reload(handler)

    project_id = "proj-12345"
    minimal_event = authenticated_event(
        None,
        f"/internal/projects/{project_id}/products/provisioned/123/remove",
        "PUT",
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    command_handler_mock.assert_called_once()


def test_remove_provisioned_products(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_remove_provisioned_products_handler,
):
    # ARRANGE
    from app.provisioning.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    project_id = "proj-12345"

    request = api_model.RemoveProvisionedProductsRequest(provisionedProductIds=["pp-123", "pp-321"])

    minimal_event = authenticated_event(
        request.model_dump_json(), f"/projects/{project_id}/products/provisioned/remove", "PUT"
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.RemoveProvisionedProductsResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    mocked_remove_provisioned_products_handler.assert_called_once()


def test_get_available_product_version(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_versions_domain_query_service,
):
    # ARRANGE
    from app.provisioning.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    project_id = "proj-12345"
    product_id = "prod-123"
    minimal_event = authenticated_event(
        None,
        f"/projects/{project_id}/products/{product_id}/versions",
        "GET",
        {
            "region": "us-east-1",
            "stage": "dev",
        },
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    mocked_versions_domain_query_service.get_versions_ready_for_provisioning.assert_called_with(
        product_id=product_id_value_object.from_str("prod-123"),
        stage=version_stage_value_object.from_str("dev"),
        region=region_value_object.from_str("us-east-1"),
        return_technical_params=False,
    )
    response = api_model.GetAvailableProductVersionsResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.availableProductVersions).is_not_none()
    assertpy.assert_that(response.availableProductVersions).is_length(2)
    assertpy.assert_that(response.availableProductVersions[0].model_dump()).is_equal_to(
        {
            "isRecommendedVersion": True,
            "parameters": [
                {
                    "parameterKey": "SomeParam",
                    "defaultValue": "some-default",
                    "description": None,
                    "isNoEcho": None,
                    "parameterType": "String",
                    "parameterConstraints": {
                        "allowedPattern": None,
                        "allowedValues": ["val-1", "val-2"],
                        "constraintDescription": None,
                        "maxLength": None,
                        "maxValue": None,
                        "minLength": None,
                        "minValue": None,
                    },
                    "parameterMetaData": {
                        "label": "Some Parameter",
                        "optionLabels": {"val-1": "Value 1", "val-2": "Value 2"},
                        "optionWarnings": {"val-1": "Some Warning"},
                    },
                },
                {
                    "parameterKey": "SomeTechParam",
                    "defaultValue": "/workbench/autosar/adaptive/ami-id/v1-3-x",
                    "description": None,
                    "isNoEcho": None,
                    "parameterType": "AWS::SSM::Parameter::Value<String>",
                    "parameterConstraints": None,
                    "parameterMetaData": None,
                },
            ],
            "versionDescription": "Initial release",
            "versionId": "ver-123",
            "versionName": "v1.0.0",
            "metadata": None,
            "componentVersionDetails": [
                {
                    "componentName": "VS Code",
                    "componentVersionType": "MAIN",
                    "softwareVendor": "Microsoft",
                    "softwareVersion": "1.87.0",
                    "licenseDashboard": None,
                    "notes": None,
                }
            ],
            "osVersion": "Ubuntu 24",
        }
    )


def test_get_user_provisioned_products(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_virtual_targets_domain_query_service,
):
    # ARRANGE
    from app.provisioning.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    project_id = "proj-12345"
    minimal_event = authenticated_event(
        None,
        f"/projects/{project_id}/products/provisioned",
        "GET",
        {
            "productType": "virtualTarget",
        },
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetProvisionedProductsResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.provisionedProducts).is_length(5)
    mocked_virtual_targets_domain_query_service.get_provisioned_products.assert_called_once_with(
        project_id=project_id_value_object.from_str(project_id),
        user_id=user_id_value_object.from_str("T00123122"),
        provisioned_product_type=provisioned_product_type_value_object.from_str("VirtualTarget"),
        exclude_status=[product_status_value_object.from_str(product_status.ProductStatus.Terminated.value)],
        return_technical_params=False,
    )
    assertpy.assert_that(response).is_equal_to(
        api_model.GetProvisionedProductsResponse(
            provisionedProducts=[
                api_model.ProvisionedProduct(
                    projectId="proj-12345",
                    provisionedProductId=f"vt-{i}",
                    provisionedProductName="vt-name",
                    provisionedProductType="VIRTUAL_TARGET",
                    userId="user-1",
                    status=product_status.ProductStatus.Running,
                    productId=f"prod-{i}",
                    productName="Product Name",
                    versionId="vers-1",
                    versionName="vers-name",
                    newVersionName="new-vers-name",
                    newVersionId="new-vers-id",
                    stage=provisioned_product.ProvisionedProductStage.QA,
                    region="us-east-1",
                    provisioningParameters=[
                        provisioning_parameter.ProvisioningParameter(key="mock-param-key").model_dump()
                    ],
                    createDate="2023-09-01T00:00:00+00:00",
                    lastUpdateDate="2023-09-01T00:00:00+00:00",
                    outputs=[
                        provisioned_product_output.ProvisionedProductOutput(
                            outputKey="outputs-key",
                            outputValue="outputs-value",
                            description=None,
                            outputType=None,
                        ).model_dump()
                    ],
                    sshEnabled=True,
                    usernamePasswordLoginEnabled=True,
                    experimental=True,
                    componentVersionDetails=TEST_COMPONENT_VERSION_DETAILS_DUMPED,
                    osVersion=TEST_OS_VERSION,
                    awsAccountId="12345678912",
                    isRetired=False,
                )
                for i in range(5)
            ]
        )
    )


def test_get_project_provisioned_products(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_virtual_targets_domain_query_service,
):
    # ARRANGE
    from app.provisioning.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    project_id = "proj-12345"
    minimal_event = authenticated_event(
        None,
        f"/projects/{project_id}/products/provisioned/all",
        "GET",
        {
            "productType": "virtualTarget",
        },
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetAllProvisionedProductsResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.provisionedProducts).is_length(5)
    mocked_virtual_targets_domain_query_service.get_provisioned_products.assert_called_once_with(
        project_id=project_id_value_object.from_str(project_id),
        exclude_status=[product_status_value_object.from_str(product_status.ProductStatus.Terminated.value)],
        return_technical_params=False,
    )
    assertpy.assert_that(response).is_equal_to(
        api_model.GetAllProvisionedProductsResponse(
            provisionedProducts=[
                api_model.ProvisionedProduct(
                    projectId="proj-12345",
                    provisionedProductId=f"vt-{i}",
                    provisionedProductName="vt-name",
                    provisionedProductType="VIRTUAL_TARGET",
                    userId="user-1",
                    status=product_status.ProductStatus.Running,
                    productId=f"prod-{i}",
                    productName="Product Name",
                    versionId="vers-1",
                    versionName="vers-name",
                    newVersionName="new-vers-name",
                    newVersionId="new-vers-id",
                    stage=provisioned_product.ProvisionedProductStage.QA,
                    region="us-east-1",
                    provisioningParameters=[
                        provisioning_parameter.ProvisioningParameter(key="mock-param-key").model_dump()
                    ],
                    createDate="2023-09-01T00:00:00+00:00",
                    lastUpdateDate="2023-09-01T00:00:00+00:00",
                    outputs=[
                        provisioned_product_output.ProvisionedProductOutput(
                            outputKey="outputs-key",
                            outputValue="outputs-value",
                            description=None,
                            outputType=None,
                        ).model_dump()
                    ],
                    sshEnabled=True,
                    usernamePasswordLoginEnabled=True,
                    experimental=True,
                    componentVersionDetails=TEST_COMPONENT_VERSION_DETAILS_DUMPED,
                    osVersion=TEST_OS_VERSION,
                    awsAccountId="12345678912",
                    isRetired=False,
                )
                for i in range(5)
            ]
        )
    )


def test_get_provisioned_product(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_virtual_targets_domain_query_service,
):
    # ARRANGE
    from app.provisioning.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    project_id = "proj-12345"
    provisioned_product_id = "vt-1234"
    minimal_event = authenticated_event(
        None,
        f"/projects/{project_id}/products/provisioned/{provisioned_product_id}",
        "GET",
        {
            "productType": "virtualTarget",
        },
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetProvisionedProductResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.provisionedProduct).is_equal_to(
        api_model.ProvisionedProduct(
            projectId="proj-12345",
            provisionedProductId="vt-1",
            provisionedProductName="vt-name",
            provisionedProductType="VIRTUAL_TARGET",
            userId="user-1",
            status=product_status.ProductStatus.Running,
            productId="prod-1",
            productName="Product Name",
            versionId="vers-1",
            versionName="vers-name",
            newVersionName="new-vers-name",
            newVersionId="new-vers-id",
            stage=provisioned_product.ProvisionedProductStage.QA,
            region="us-east-1",
            provisioningParameters=[provisioning_parameter.ProvisioningParameter(key="mock-param-key").model_dump()],
            createDate="2023-09-01T00:00:00+00:00",
            lastUpdateDate="2023-09-01T00:00:00+00:00",
            outputs=[
                provisioned_product_output.ProvisionedProductOutput(
                    outputKey="outputs-key",
                    outputValue="outputs-value",
                    description=None,
                    outputType=None,
                ).model_dump()
            ],
            sshEnabled=True,
            usernamePasswordLoginEnabled=True,
            experimental=True,
            componentVersionDetails=TEST_COMPONENT_VERSION_DETAILS_DUMPED,
            osVersion=TEST_OS_VERSION,
            awsAccountId="12345678912",
            isRetired=False,
        )
    )
    assertpy.assert_that(response.versionMetadata).is_not_none()
    assertpy.assert_that(response.versionMetadata.model_dump()).is_equal_to(
        {
            "isRecommendedVersion": True,
            "parameters": [
                {
                    "parameterKey": "SomeParam",
                    "defaultValue": "some-default",
                    "description": None,
                    "isNoEcho": None,
                    "parameterType": "String",
                    "parameterConstraints": {
                        "allowedPattern": None,
                        "allowedValues": ["val-1", "val-2"],
                        "constraintDescription": None,
                        "maxLength": None,
                        "maxValue": None,
                        "minLength": None,
                        "minValue": None,
                    },
                    "parameterMetaData": {
                        "label": "Some Parameter",
                        "optionLabels": {"val-1": "Value 1", "val-2": "Value 2"},
                        "optionWarnings": {"val-1": "Some Warning"},
                    },
                },
                {
                    "parameterKey": "SomeTechParam",
                    "defaultValue": "/workbench/autosar/adaptive/ami-id/v1-3-x",
                    "description": None,
                    "isNoEcho": None,
                    "parameterType": "AWS::SSM::Parameter::Value<String>",
                    "parameterConstraints": None,
                    "parameterMetaData": None,
                },
            ],
            "versionDescription": "Initial release",
            "versionId": "ver-123",
            "versionName": "v1.0.0",
            "metadata": None,
            "componentVersionDetails": [
                {
                    "componentName": "VS Code",
                    "componentVersionType": "MAIN",
                    "softwareVendor": "Microsoft",
                    "softwareVersion": "1.87.0",
                    "licenseDashboard": None,
                    "notes": None,
                }
            ],
            "osVersion": "Ubuntu 24",
        }
    )


def test_internal_get_provisioned_product(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_virtual_targets_domain_query_service,
):
    # ARRANGE
    from app.provisioning.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    project_id = "proj-12345"
    provisioned_product_id = "vt-1234"
    minimal_event = authenticated_event(
        None,
        f"/internal/projects/{project_id}/products/provisioned/{provisioned_product_id}",
        "GET",
        {
            "productType": "virtualTarget",
        },
        iam_auth=True,
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetProvisionedProductResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.provisionedProduct).is_equal_to(
        api_model.ProvisionedProduct(
            projectId="proj-12345",
            provisionedProductId="vt-1",
            provisionedProductName="vt-name",
            provisionedProductType="VIRTUAL_TARGET",
            userId="user-1",
            status=product_status.ProductStatus.Running,
            productId="prod-1",
            productName="Product Name",
            versionId="vers-1",
            versionName="vers-name",
            newVersionName="new-vers-name",
            newVersionId="new-vers-id",
            stage=provisioned_product.ProvisionedProductStage.QA,
            region="us-east-1",
            provisioningParameters=[provisioning_parameter.ProvisioningParameter(key="mock-param-key").model_dump()],
            createDate="2023-09-01T00:00:00+00:00",
            lastUpdateDate="2023-09-01T00:00:00+00:00",
            outputs=[
                provisioned_product_output.ProvisionedProductOutput(
                    outputKey="outputs-key",
                    outputValue="outputs-value",
                    description=None,
                    outputType=None,
                ).model_dump()
            ],
            sshEnabled=True,
            usernamePasswordLoginEnabled=True,
            experimental=True,
            componentVersionDetails=TEST_COMPONENT_VERSION_DETAILS_DUMPED,
            osVersion=TEST_OS_VERSION,
            awsAccountId="12345678912",
            isRetired=False,
        )
    )


@pytest.mark.parametrize("start_key", [None, quote(json.dumps({"string": "SomeStartKey"}))])
def test_internal_get_all_provisioned_products(
    start_key,
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_virtual_targets_domain_query_service,
):
    # ARRANGE
    from app.provisioning.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    if start_key:
        minimal_event = authenticated_event(None, "/internal/products/provisioned/all", "GET", {"pagingKey": start_key})
    else:
        minimal_event = authenticated_event(None, "/internal/products/provisioned/all", "GET")

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetAllProvisionedProductsResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.provisionedProducts).is_length(5)
    mocked_virtual_targets_domain_query_service.get_all_provisioned_products.assert_called_once()
    assertpy.assert_that(response).is_equal_to(
        api_model.GetAllProvisionedProductsResponse(
            provisionedProducts=[
                api_model.ProvisionedProduct(
                    projectId="proj-12345",
                    provisionedProductId=f"vt-{i}",
                    provisionedProductName="vt-name",
                    provisionedProductType="VIRTUAL_TARGET",
                    userId="user-1",
                    status=product_status.ProductStatus.Running,
                    productId=f"prod-{i}",
                    productName="Product Name",
                    versionId="vers-1",
                    versionName="vers-name",
                    newVersionName="new-vers-name",
                    newVersionId="new-vers-id",
                    stage=provisioned_product.ProvisionedProductStage.QA,
                    region="us-east-1",
                    provisioningParameters=[
                        provisioning_parameter.ProvisioningParameter(key="mock-param-key").model_dump()
                    ],
                    createDate="2023-09-01T00:00:00+00:00",
                    lastUpdateDate="2023-09-01T00:00:00+00:00",
                    outputs=[
                        provisioned_product_output.ProvisionedProductOutput(
                            outputKey="outputs-key",
                            outputValue="outputs-value",
                            description=None,
                            outputType=None,
                        ).model_dump()
                    ],
                    sshEnabled=True,
                    usernamePasswordLoginEnabled=True,
                    experimental=True,
                    componentVersionDetails=TEST_COMPONENT_VERSION_DETAILS_DUMPED,
                    osVersion=TEST_OS_VERSION,
                    awsAccountId="12345678912",
                    isRetired=False,
                )
                for i in range(5)
            ],
            pagingKey=json.dumps({"string": "NextPagingKey"}),
        )
    )


def test_get_provisioned_product_ssh_key(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_virtual_targets_domain_query_service,
):
    # ARRANGE
    from app.provisioning.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    project_id = "proj-12345"
    provisioned_product_id = "vt-1234"
    minimal_event = authenticated_event(
        None,
        f"/projects/{project_id}/products/provisioned/{provisioned_product_id}/ssh-key",
        "GET",
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetProvisionedProductSSHKeyResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.sshKey).is_equal_to("abc")
    mocked_virtual_targets_domain_query_service.get_provisioned_product_ssh_key.assert_called_with(
        project_id=project_id_value_object.from_str("proj-12345"),
        provisioned_product_id=provisioned_product_id_value_object.from_str("vt-1234"),
        user_id=user_id_value_object.from_str("T00123122"),
    )


def test_get_provisioned_product_user_credentials(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_virtual_targets_domain_query_service,
):
    # ARRANGE
    from app.provisioning.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    project_id = "proj-12345"
    provisioned_product_id = "vt-1234"
    minimal_event = authenticated_event(
        None,
        f"/projects/{project_id}/products/provisioned/{provisioned_product_id}/user-credentials",
        "GET",
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetProvisionedProductUserSecretResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.username).is_equal_to("user")
    assertpy.assert_that(response.password).is_equal_to("pwd")
    mocked_virtual_targets_domain_query_service.get_provisioned_product_user_credentials.assert_called_with(
        project_id=project_id_value_object.from_str("proj-12345"),
        provisioned_product_id=provisioned_product_id_value_object.from_str("vt-1234"),
        user_id=user_id_value_object.from_str("T00123122"),
    )


def test_start_provisioned_product(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_start_provisioned_product_handler,
):
    # ARRANGE
    from app.provisioning.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    project_id = "proj-12345"
    minimal_event = authenticated_event(
        None,
        f"/projects/{project_id}/products/provisioned/123/start",
        "PATCH",
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.StartProvisionedProductResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    mocked_start_provisioned_product_handler.assert_called_once()


def test_stop_provisioned_product(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_stop_provisioned_product_handler,
):
    # ARRANGE
    from app.provisioning.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    project_id = "proj-12345"
    minimal_event = authenticated_event(
        None,
        f"/projects/{project_id}/products/provisioned/123/stop",
        "PATCH",
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.StopProvisionedProductResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    mocked_stop_provisioned_product_handler.assert_called_once()


def test_stop_provisioned_products(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_stop_provisioned_products_handler,
):
    # ARRANGE
    from app.provisioning.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    project_id = "proj-12345"

    request = api_model.StopProvisionedProductsRequest(provisionedProductIds=["pp-123", "pp-321"])

    minimal_event = authenticated_event(
        request.model_dump_json(),
        f"/projects/{project_id}/products/provisioned/stop",
        "PATCH",
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.StopProvisionedProductsResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    mocked_stop_provisioned_products_handler.assert_called_once()


def test_update_user_profile(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_update_user_profile_handler,
):
    # ARRANGE
    from app.provisioning.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    request = api_model.UpdateUserProfileRequest(
        preferredRegion="us-east-1",
        preferredNetwork="x",
        preferredMaintenanceWindows=[
            api_model.MaintenanceWindow(day="MONDAY", startTime="00:00", endTime="04:00"),
            api_model.MaintenanceWindow(day="THURSDAY", startTime="04:00", endTime="08:00"),
        ],
    )
    minimal_event = authenticated_event(
        request.model_dump_json(),
        "/profile",
        "PUT",
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.UpdateUserProfileResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    mocked_update_user_profile_handler.assert_called_once()


@patch("app.provisioning.entrypoints.api.bootstrapper.parameters")
def test_get_user_profile(
    parameters,
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    get_test_user_profile,
    mocked_user_profile_domain_query_service,
    ssm_mock,
):
    # ARRANGE
    parameters.get_parameter.side_effect = ("3.12", "3.12", "3")
    from app.provisioning.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    minimal_event = authenticated_event(
        None,
        "/profile",
        "GET",
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    test_profile: user_profile.UserProfile = get_test_user_profile()
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetUserProfileResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.preferredRegion).is_equal_to(test_profile.preferredRegion)
    assertpy.assert_that(response.preferredNetwork).is_equal_to(test_profile.preferredNetwork)
    assertpy.assert_that(response.enabledRegions).contains_only("us-east-1", "eu-west-3")
    assertpy.assert_that(response.enabledFeatures).contains_only(
        api_model.GetUserProfileResponseFeature(
            version="v0.0.0",
            feature="EnabledFeature",
            enabled=True,
        )
    )
    assertpy.assert_that(response.applicationVersion).is_equal_to("3.12")
    assertpy.assert_that(response.applicationVersionBackend).is_equal_to("3.12")
    assertpy.assert_that(response.applicationVersionFrontend).is_equal_to("3.12")
    assertpy.assert_that(response.preferredMaintenanceWindows).is_equal_to(
        [api_model.MaintenanceWindow.model_validate(mw.model_dump()) for mw in test_profile.preferredMaintenanceWindows]
    )
    mocked_user_profile_domain_query_service.get_user_configuration.assert_called_once_with(
        user_id=user_id_value_object.from_str("T00123122")
    )


def test_get_swagger_json(lambda_context, authenticated_event, mocked_dependencies, get_test_user_profile):
    # ARRANGE
    from app.provisioning.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    minimal_event = authenticated_event(None, "/_swagger", "GET", query_params={"format": "json"})

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)


def test_get_users_within_maintenance_window(lambda_context, authenticated_event, mocked_dependencies):
    # ARRANGE
    from app.provisioning.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    minimal_event = authenticated_event(
        None,
        "/internal/users/maintenance-windows",
        "GET",
        {"day": "MONDAY", "startHour": "2"},
        iam_auth=True,
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetUsersWithinMaintenanceWindowResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.usersIds).is_length(3)


def test_authorize_user_ip_address(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_authorize_user_ip_address_handler,
):
    # ARRANGE
    from app.provisioning.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    project_id = "proj-12345"
    minimal_event = authenticated_event(
        None,
        f"/projects/{project_id}/products/provisioned/123/user-ip-address",
        "PATCH",
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    mocked_authorize_user_ip_address_handler.assert_called_once()


def test_internal_get_provisioning_subnets(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_provisioning_infra_qs,
):
    # ARRANGE
    from app.provisioning.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    minimal_event = authenticated_event(
        None,
        "/internal/provisioning-subnets",
        "GET",
        {
            "accountId": "001234567890",
            "region": "us-east-1",
        },
        iam_auth=True,
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(json.loads(result.get("body"))).is_equal_to(
        {
            "subnets": [
                {
                    "subnetId": "sub-123",
                    "cidrBlock": "192.168.1.0/24",
                    "vpcId": "vpc-123",
                }
            ]
        }
    )

    mocked_provisioning_infra_qs.get_provisioning_subnets_in_account.assert_called_once()

    passed_args = mocked_provisioning_infra_qs.get_provisioning_subnets_in_account.call_args.kwargs
    assertpy.assert_that(passed_args.get("account_id").value).is_equal_to("001234567890")
    assertpy.assert_that(passed_args.get("region").value).is_equal_to("us-east-1")


@pytest.fixture
def construct_query_parameters():  # noqa: C901
    def __construct_query_parameters(
        product_type: str,
        owner: str,
        version_name: str,
        product_name: str,
        page_size: int,
        status: str,
        stage: str,
        experimental: bool,
        start_key: str,
    ):
        query_params = {}
        if product_type:
            query_params["productType"] = product_type
        if owner:
            query_params["owner"] = owner
        if version_name:
            query_params["versionName"] = version_name
        if product_name:
            query_params["productName"] = product_name
        if page_size:
            query_params["pageSize"] = page_size
        if status:
            query_params["status"] = status
        if stage:
            query_params["stage"] = stage
        if experimental:
            query_params["experimental"] = experimental
        if start_key:
            query_params["pagingKey"] = start_key
        return query_params

    return __construct_query_parameters


@pytest.mark.parametrize(
    "start_key,product_type,owner,version_name,product_name,page_size,status,stage,experimental",
    [
        (
            None,
            "virtualTarget",
            "SF44410",
            "1.0.0",
            "TEST name",
            100,
            "RUNNING",
            "DEV",
            False,
        ),
        (
            None,
            "workbench",
            "SF44410",
            "1.0.0",
            "TEST name",
            100,
            "RUNNING",
            "DEV",
            False,
        ),
        (
            quote(json.dumps({"string": "SomeStartKey"})),
            "virtualTarget",
            "SF44410",
            "1.0.0",
            "TEST name",
            100,
            "RUNNING",
            "DEV",
            False,
        ),
        (None, None, None, None, None, 100, None, None, False),
        (None, None, None, None, None, 0, None, None, False),
    ],
)
def test_get_paginated_project_provisioned_products(
    start_key,
    product_type,
    owner,
    version_name,
    product_name,
    page_size,
    status,
    stage,
    experimental,
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_virtual_targets_domain_query_service,
    construct_query_parameters,
):
    # ARRANGE
    from app.provisioning.entrypoints.api import handler

    query_params = construct_query_parameters(
        start_key=start_key,
        product_type=product_type,
        version_name=version_name,
        product_name=product_name,
        page_size=page_size,
        status=status,
        stage=stage,
        experimental=experimental,
        owner=owner,
    )

    handler.dependencies = mocked_dependencies

    project_id = "proj-12345"

    minimal_event = authenticated_event(
        None,
        f"/projects/{project_id}/products/provisioned/paginated",
        "GET",
        query_params,
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetPaginatedProvisionedProductsResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.provisionedProducts).is_length(5)
    mocked_virtual_targets_domain_query_service.get_paginated_provisioned_products.assert_called_once_with(
        project_id=project_id_value_object.from_str(project_id),
        status=(product_status_value_object.from_str(status) if query_params.get("status") else None),
        stage=(provisioned_product_stage_value_object.from_str(stage) if query_params.get("stage") else None),
        owner=(user_id_value_object.from_str(owner) if query_params.get("owner") else None),
        page_size=(
            query_params.get("pageSize") if query_params.get("pageSize") else int(os.environ.get("DEFAULT_PAGE_SIZE"))
        ),
        product_name=(product_name_value_object.from_str(product_name) if query_params.get("productName") else None),
        version_name=(
            product_version_name_value_object.from_str(version_name) if query_params.get("versionName") else None
        ),
        provisioned_product_type=(
            provisioned_product_type_value_object.from_str(product_type) if query_params.get("productType") else None
        ),
        paging_key={"string": "SomeStartKey"} if start_key else None,
        experimental=experimental if query_params.get("experimental") else None,
    )
    assertpy.assert_that(response).is_equal_to(
        api_model.GetPaginatedProvisionedProductsResponse(
            provisionedProducts=[
                api_model.ProvisionedProduct(
                    projectId="proj-12345",
                    provisionedProductId=f"vt-{i}",
                    provisionedProductName="vt-name",
                    provisionedProductType="VIRTUAL_TARGET",
                    userId="user-1",
                    status=product_status.ProductStatus.Running,
                    productId=f"prod-{i}",
                    productName="Product Name",
                    versionId="vers-1",
                    versionName="vers-name",
                    newVersionName="new-vers-name",
                    newVersionId="new-vers-id",
                    stage=provisioned_product.ProvisionedProductStage.QA,
                    region="us-east-1",
                    provisioningParameters=[
                        provisioning_parameter.ProvisioningParameter(key="mock-param-key").model_dump()
                    ],
                    createDate="2023-09-01T00:00:00+00:00",
                    lastUpdateDate="2023-09-01T00:00:00+00:00",
                    outputs=[
                        provisioned_product_output.ProvisionedProductOutput(
                            outputKey="outputs-key",
                            outputValue="outputs-value",
                            description=None,
                            outputType=None,
                        ).model_dump()
                    ],
                    sshEnabled=True,
                    usernamePasswordLoginEnabled=True,
                    experimental=True,
                    componentVersionDetails=TEST_COMPONENT_VERSION_DETAILS_DUMPED,
                    osVersion=TEST_OS_VERSION,
                    awsAccountId="12345678912",
                    isRetired=False,
                )
                for i in range(5)
            ],
            pagingKey=json.dumps({"string": "NextPagingKey"}),
        )
    )
