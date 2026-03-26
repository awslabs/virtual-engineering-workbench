import importlib
import json
import unittest
from datetime import datetime, timezone
from urllib.parse import quote

import assertpy
import pytest

from app.provisioning.domain.commands.product_provisioning import (
    launch_product_command,
)
from app.provisioning.domain.model import (
    product_status,
    provisioned_product,
    provisioned_product_output,
    provisioning_parameter,
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
    product_type_value_object,
    product_version_name_value_object,
    project_id_value_object,
    provisioned_product_stage_value_object,
    provisioned_product_type_value_object,
    region_value_object,
    user_id_value_object,
    version_stage_value_object,
)
from app.provisioning.entrypoints.s2s_api import bootstrapper
from app.provisioning.entrypoints.s2s_api.model import api_model
from app.shared.adapters.message_bus import in_memory_command_bus
from app.shared.middleware import authorization

TEST_OS_VERSION = "Ubuntu 24"
TEST_COMPONENT_VERSION_DETAILS = [
    component_version_detail.ComponentVersionDetail(
        componentName="VS Code",
        componentVersionType=component_version_detail.ComponentVersionEntryType.Main,
        softwareVendor="Microsoft",
        softwareVersion="1.87.0",
    )
]


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
            isVersionRetired=True,
            versionRetiredDate=None,
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
def mocked_dependencies(
    mocked_products_domain_query_service,
    mocked_versions_domain_query_service,
    mocked_launch_provisioned_product_handler,
    mocked_virtual_targets_domain_query_service,
) -> bootstrapper.Dependencies:
    return bootstrapper.Dependencies(
        command_bus=in_memory_command_bus.InMemoryCommandBus(
            logger=unittest.mock.MagicMock(),
        ).register_handler(
            launch_product_command.LaunchProductCommand,
            mocked_launch_provisioned_product_handler,
        ),
        products_domain_qry_srv=mocked_products_domain_query_service,
        versions_domain_qry_srv=mocked_versions_domain_query_service,
        virtual_targets_domain_qry_srv=mocked_virtual_targets_domain_query_service,
    )


@pytest.fixture
def mocked_launch_provisioned_product_handler():
    return unittest.mock.MagicMock()


@unittest.mock.patch(
    "app.provisioning.domain.query_services.products_domain_query_service.ProductsDomainQueryService",
    autospec=True,
)
def test_get_available_products(products_domain_qs, lambda_context, authenticated_event):
    # ARRANGE
    products_domain_qs.return_value.get_available_products.return_value = [
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

    from app.provisioning.entrypoints.s2s_api import handler

    importlib.reload(handler)

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
    response = api_model.GetAvailableProductsResponse.parse_obj(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.availableProducts).is_not_none()
    assertpy.assert_that(len(response.availableProducts)).is_equal_to(5)
    products_domain_qs.return_value.get_available_products.assert_called_once_with(
        project_id=project_id_value_object.ProjectIdValueObject(value="proj-12345"),
        user_roles=[authorization.VirtualWorkbenchRoles.Admin],
        product_type=product_type_value_object.ProductTypeValueObject(value="VIRTUAL_TARGET"),
        product_id_filter=[product_id_value_object.ProductIdValueObject(value="p-123")],
    )


@unittest.mock.patch(
    "app.provisioning.domain.command_handlers.product_provisioning.launch.handle",
    autospec=True,
)
@unittest.mock.patch(
    "app.provisioning.domain.model.internal.id_generators.generate_provisioned_product_id",
    return_value="pp-123",
)
def test_launch_product(
    id_gen,
    mocked_launch_provisioned_product_handler,
    lambda_context,
    authenticated_event,
):
    # ARRANGE
    from app.provisioning.entrypoints.s2s_api import handler

    importlib.reload(handler)

    project_id = "proj-12345"
    request = api_model.LaunchProductRequest(
        productType="VirtualTarget",
        productId="prod-123",
        versionId="vers-123",
        provisioningParameters=[api_model.ProvisioningParameter(key="a", value="b")],
        stage="dev",
        region="us-east-1",
        userName="TestUser",
    )
    minimal_event = authenticated_event(
        request.json(),
        f"/projects/{project_id}/products/provisioned",
        "POST",
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(202)
    response = api_model.LaunchProductResponse.parse_obj(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.provisionedProductId).is_equal_to("pp-123")
    mocked_launch_provisioned_product_handler.assert_called_once()
    cmd = mocked_launch_provisioned_product_handler.call_args.kwargs.get("command")
    assertpy.assert_that(cmd.deployment_option.value).is_equal_to("MULTI_AZ")


@unittest.mock.patch(
    "app.provisioning.domain.query_services.versions_domain_query_service.VersionsDomainQueryService",
    autospec=True,
)
def test_get_available_product_version(versions_domain_qs, lambda_context, authenticated_event, mock_product_version):
    # ARRANGE
    versions_domain_qs.return_value.get_versions_ready_for_provisioning.return_value = [
        mock_product_version(),
        mock_product_version(),
    ]

    from app.provisioning.entrypoints.s2s_api import handler

    importlib.reload(handler)

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
    versions_domain_qs.return_value.get_versions_ready_for_provisioning.assert_called_with(
        product_id=product_id_value_object.from_str("prod-123"),
        stage=version_stage_value_object.from_str("dev"),
        region=region_value_object.from_str("us-east-1"),
        return_technical_params=False,
    )
    response = api_model.GetAvailableProductVersionsResponse.parse_obj(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.availableProductVersions).is_not_none()
    assertpy.assert_that(response.availableProductVersions).is_length(2)
    assertpy.assert_that(response.availableProductVersions[0].dict()).is_equal_to(
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


@unittest.mock.patch(
    "app.provisioning.domain.query_services.provisioned_products_domain_query_service.ProvisionedProductsDomainQueryService",
    autospec=True,
)
def test_get_provisioned_product(
    pp_domain_qs,
    lambda_context,
    authenticated_event,
    mock_provisioned_product,
    mock_product_version,
):
    # ARRANGE

    pp_domain_qs.return_value.get_provisioned_product.return_value = (
        mock_provisioned_product("vt-1", "prod-1", "user-1"),
        mock_product_version(),
    )

    from app.provisioning.entrypoints.s2s_api import handler

    importlib.reload(handler)

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
    response = api_model.GetProvisionedProductResponse.parse_obj(json.loads(result["body"]))
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
            versionRetiredDate=None,
            stage=provisioned_product.ProvisionedProductStage.QA,
            region="us-east-1",
            provisioningParameters=[provisioning_parameter.ProvisioningParameter(key="mock-param-key")],
            createDate="2023-09-01T00:00:00+00:00",
            lastUpdateDate="2023-09-01T00:00:00+00:00",
            outputs=[
                provisioned_product_output.ProvisionedProductOutput(
                    outputKey="outputs-key",
                    outputValue="outputs-value",
                    description=None,
                    outputType=None,
                )
            ],
            sshEnabled=True,
            usernamePasswordLoginEnabled=True,
            experimental=True,
            componentVersionDetails=TEST_COMPONENT_VERSION_DETAILS,
            osVersion=TEST_OS_VERSION,
            awsAccountId="12345678912",
        )
    )
    assertpy.assert_that(response.versionMetadata).is_not_none()
    assertpy.assert_that(response.versionMetadata.dict()).is_equal_to(
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


@unittest.mock.patch(
    "app.provisioning.domain.command_handlers.provisioned_product_state.initiate_start.handle",
    autospec=True,
)
def test_start_provisioned_product(mock_start_provisioned_product_handler, lambda_context, authenticated_event):
    # ARRANGE
    from app.provisioning.entrypoints.s2s_api import handler

    importlib.reload(handler)

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
    mock_start_provisioned_product_handler.assert_called_once()


@unittest.mock.patch(
    "app.provisioning.domain.command_handlers.provisioned_product_state.initiate_stop.handle",
    autospec=True,
)
def test_stop_provisioned_product(mock_stop_provisioned_product_handler, lambda_context, authenticated_event):
    # ARRANGE
    from app.provisioning.entrypoints.s2s_api import handler

    importlib.reload(handler)

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
    mock_stop_provisioned_product_handler.assert_called_once()


@pytest.fixture
def construct_query_parameters_s2s():  # noqa: C901
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
        query_params = {}  # No userName required for s2s paginated endpoint
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
        (
            None,
            None,
            None,
            None,
            None,
            100,
            None,
            None,
            False,
        ),
        (
            None,
            None,
            None,
            None,
            None,
            0,
            None,
            None,
            False,
        ),
    ],
)
def test_get_project_provisioned_products_paginated(
    start_key,
    product_type,
    owner,
    version_name,
    product_name,
    page_size,
    status,
    stage,
    experimental,
    mocked_s2s_dependencies,
    mocked_virtual_targets_domain_query_service,
    lambda_context,
    authenticated_event,
    mock_provisioned_product,
    construct_query_parameters_s2s,
):
    # ARRANGE
    from app.provisioning.entrypoints.s2s_api import handler

    handler.dependencies = mocked_s2s_dependencies

    project_id = "proj-12345"

    query_params = construct_query_parameters_s2s(
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

    minimal_event = authenticated_event(
        None,
        f"/projects/{project_id}/products/provisioned",
        "GET",
        query_params,
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetPaginatedProvisionedProductsResponse.parse_obj(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.provisionedProducts).is_length(5)

    # Verify the service was called with correct parameters
    expected_paging_key = {"string": "SomeStartKey"} if start_key else None
    expected_page_size = page_size if page_size else 100  # default page size from config
    mocked_virtual_targets_domain_query_service.get_paginated_provisioned_products.assert_called_once_with(
        project_id=project_id_value_object.from_str(project_id),
        page_size=expected_page_size,
        paging_key=expected_paging_key,
        product_name=(product_name_value_object.from_str(product_name) if product_name else None),
        version_name=(product_version_name_value_object.from_str(version_name) if version_name else None),
        owner=user_id_value_object.from_str(owner) if owner else None,
        status=product_status_value_object.from_str(status) if status else None,
        stage=provisioned_product_stage_value_object.from_str(stage) if stage else None,
        provisioned_product_type=(
            provisioned_product_type_value_object.from_str(product_type) if product_type else None
        ),
        experimental=experimental if experimental else None,
    )

    # Verify response structure matches expected format
    assertpy.assert_that(response.provisionedProducts[0].provisionedProductId).is_equal_to("vt-1")
    assertpy.assert_that(response.provisionedProducts[0].userId).is_equal_to("user-1")
    assertpy.assert_that(response.provisionedProducts[4].provisionedProductId).is_equal_to("vt-5")
    assertpy.assert_that(response.provisionedProducts[4].userId).is_equal_to("user-5")
    assertpy.assert_that(response.pagingKey).is_equal_to(json.dumps({"string": "NextPagingKey"}))
