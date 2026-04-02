from unittest import mock

import assertpy
import pytest
from aws_lambda_powertools.event_handler.exceptions import NotFoundError

from app.provisioning.domain.exceptions.domain_exception import DomainException
from app.provisioning.domain.model import (
    product_status,
    provisioned_product,
    provisioned_product_output,
    provisioning_parameter,
    user_credential,
)
from app.provisioning.domain.ports import (
    networking_query_service,
    parameter_service,
    provisioned_products_query_service,
    versions_query_service,
)
from app.provisioning.domain.query_services import (
    provisioned_products_domain_query_service,
)
from app.provisioning.domain.read_models import version
from app.provisioning.domain.tests.product_provisioning.conftest import (
    TEST_COMPONENT_VERSION_DETAILS,
    TEST_COMPONENT_VERSION_DETAILS_DUMPED,
    TEST_OS_VERSION,
)
from app.provisioning.domain.value_objects import (
    product_name_value_object,
    product_status_value_object,
    product_version_name_value_object,
    project_id_value_object,
    provisioned_product_id_value_object,
    provisioned_product_stage_value_object,
    provisioned_product_type_value_object,
    user_id_value_object,
)


@pytest.fixture()
def make_sample_provisioned_product():
    def _get_sample_virtual_target(
        provisioned_product_id: str = "vt-1",
        product_id: str = "prod-1",
        user_id: str = "user-1",
        ssh_key_path: str | None = None,
        user_credential_name: str | None = None,
    ):
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
            versionDescription="Test Description",
            awsAccountId="12345678912",
            accountId="0987654321",
            stage=provisioned_product.ProvisionedProductStage.QA,
            region="us-east-1",
            amiId="mock-ami-id",
            scProductId="sc-product-id",
            scProvisioningArtifactId="sc-vers-id",
            scProvisionedProductId=None,
            provisioningParameters=[
                provisioning_parameter.ProvisioningParameter(key="mock-param-key"),
                provisioning_parameter.ProvisioningParameter(
                    key="mock-tech-param-key",
                    value="/workbench/autosar/adaptive/ami-id/v1-3-x",
                    isTechnicalParameter=True,
                ),
            ],
            outputs=[
                provisioned_product_output.ProvisionedProductOutput(
                    outputKey="outputs-key",
                    outputValue="outputs-value",
                )
            ],
            createDate="2023-09-01T00:00:00+00:00",
            lastUpdateDate="2023-09-01T00:00:00+00:00",
            createdBy=user_id,
            lastUpdatedBy=user_id,
            sshKeyPath=ssh_key_path,
            userCredentialName=user_credential_name,
            componentVersionDetails=TEST_COMPONENT_VERSION_DETAILS,
            osVersion=TEST_OS_VERSION,
            containerName=None,
            containerServiceName=None,
        )

    return _get_sample_virtual_target


@pytest.fixture()
def provisioned_product_query_service_mock():
    provisioned_products_srv_mock = mock.create_autospec(
        spec=provisioned_products_query_service.ProvisionedProductsQueryService
    )
    return provisioned_products_srv_mock


@pytest.fixture()
def versions_query_service_mock(get_test_version):
    m = mock.create_autospec(spec=versions_query_service.VersionsQueryService)
    m.get_product_version_distributions.return_value = [get_test_version()]
    m.get_product_version_distribution.return_value = get_test_version()
    return m


@pytest.fixture()
def parameter_service_mock():
    return mock.create_autospec(spec=parameter_service.ParameterService)


@pytest.fixture
def network_qry_srv_mock():
    return mock.create_autospec(spec=networking_query_service.NetworkingQueryService)


def test_get_provisioned_products_returns_provisioned_products_by_user(
    provisioned_product_query_service_mock,
    make_sample_provisioned_product,
    versions_query_service_mock,
    network_qry_srv_mock,
    parameter_service_mock,
):
    # ARRANGE
    sample_provisioned_products = [
        make_sample_provisioned_product(f"vt-{i}", f"prod-{i}", user_id="user-1") for i in range(5)
    ]

    provisioned_product_query_service_mock.get_provisioned_products_by_user_id.return_value = (
        sample_provisioned_products
    )
    products_domain_qry_srv = provisioned_products_domain_query_service.ProvisionedProductsDomainQueryService(
        provisioned_products_qry_srv=provisioned_product_query_service_mock,
        version_qry_srv=versions_query_service_mock,
        networking_qry_srv=network_qry_srv_mock,
        parameter_srv=parameter_service_mock,
    )

    # ACT
    provisioned_products = products_domain_qry_srv.get_provisioned_products(
        project_id=project_id_value_object.from_str("proj-12345"),
        user_id=user_id_value_object.from_str("user-1"),
        provisioned_product_type=provisioned_product_type_value_object.from_str("Workbench"),
    )

    # ASSERT
    assertpy.assert_that(provisioned_products).is_length(5)
    provisioned_product_query_service_mock.get_provisioned_products_by_user_id.assert_called_once()
    assertpy.assert_that(provisioned_products[0].provisioningParameters).is_length(2)


@pytest.mark.parametrize("start_key", [None, {"string": "SomeStartKey"}])
def test_get_all_provisioned_products_returns_all_provisioned_products(
    start_key,
    provisioned_product_query_service_mock,
    make_sample_provisioned_product,
    versions_query_service_mock,
    network_qry_srv_mock,
    parameter_service_mock,
):
    # ARRANGE
    sample_provisioned_products = [make_sample_provisioned_product(f"vt-{i}", f"prod-{i}") for i in range(5)]

    provisioned_product_query_service_mock.get_all_cross_projects_provisioned_products.return_value = (
        sample_provisioned_products
    )
    products_domain_qry_srv = provisioned_products_domain_query_service.ProvisionedProductsDomainQueryService(
        provisioned_products_qry_srv=provisioned_product_query_service_mock,
        version_qry_srv=versions_query_service_mock,
        networking_qry_srv=network_qry_srv_mock,
        parameter_srv=parameter_service_mock,
    )

    # ACT
    provisioned_products = products_domain_qry_srv.get_all_provisioned_products(start_key=start_key)

    # ASSERT
    assertpy.assert_that(provisioned_products).is_length(5)
    provisioned_product_query_service_mock.get_all_cross_projects_provisioned_products.assert_called_once_with(
        start_key=start_key, exclude_terminated=True
    )


def test_get_provisioned_virtual_target_should_return_virtual_target(
    provisioned_product_query_service_mock,
    make_sample_provisioned_product,
    versions_query_service_mock,
    network_qry_srv_mock,
    parameter_service_mock,
):
    # ARRANGE
    provisioned_product_query_service_mock.get_provisioned_product.return_value = make_sample_provisioned_product()
    virtual_target_domain_qry_srv = provisioned_products_domain_query_service.ProvisionedProductsDomainQueryService(
        provisioned_products_qry_srv=provisioned_product_query_service_mock,
        version_qry_srv=versions_query_service_mock,
        networking_qry_srv=network_qry_srv_mock,
        parameter_srv=parameter_service_mock,
    )
    # ACT
    vt, vers_meta = virtual_target_domain_qry_srv.get_provisioned_product(
        project_id=project_id_value_object.from_str("proj-12345"),
        provisioned_product_id=provisioned_product_id_value_object.from_str("vt-1"),
    )
    # ASSERT
    provisioned_product_query_service_mock.get_provisioned_product.assert_called_once_with("proj-12345", "vt-1")
    assertpy.assert_that(vt.model_dump()).is_equal_to(
        {
            "accountId": "0987654321",
            "amiId": "mock-ami-id",
            "awsAccountId": "12345678912",
            "createDate": "2023-09-01T00:00:00+00:00",
            "createdBy": "user-1",
            "instanceId": None,
            "lastUpdateDate": "2023-09-01T00:00:00+00:00",
            "lastUpdatedBy": "user-1",
            "newVersionId": None,
            "newVersionName": None,
            "outputs": [
                {
                    "outputKey": "outputs-key",
                    "outputValue": "outputs-value",
                    "description": None,
                }
            ],
            "privateIp": None,
            "publicIp": None,
            "sshKeyPath": None,
            "userCredentialName": None,
            "productDescription": None,
            "productId": "prod-1",
            "productName": "Product Name",
            "projectId": "proj-12345",
            "provisioningParameters": [
                {
                    "key": "mock-param-key",
                    "value": None,
                    "isTechnicalParameter": False,
                    "parameterType": None,
                    "usePreviousValue": False,
                },
                {
                    "key": "mock-tech-param-key",
                    "value": "/workbench/autosar/adaptive/ami-id/v1-3-x",
                    "isTechnicalParameter": True,
                    "parameterType": None,
                    "usePreviousValue": False,
                },
            ],
            "region": "us-east-1",
            "scProductId": "sc-product-id",
            "scProvisionedProductId": None,
            "scProvisioningArtifactId": "sc-vers-id",
            "stage": provisioned_product.ProvisionedProductStage.QA,
            "status": product_status.ProductStatus.Running,
            "statusReason": None,
            "technologyId": "tech-12345",
            "upgradeAvailable": None,
            "userDomains": ["mock-user-domain"],
            "userId": "user-1",
            "versionId": "vers-1",
            "versionName": "vers-name",
            "versionDescription": "Test Description",
            "provisionedProductId": "vt-1",
            "provisionedProductName": "vt-name",
            "provisionedProductType": provisioned_product.ProvisionedProductType.VirtualTarget,
            "instanceRecommendationReason": None,
            "recommendedInstanceType": None,
            "newProvisioningParameters": None,
            "additionalConfigurations": None,
            "experimental": None,
            "componentVersionDetails": TEST_COMPONENT_VERSION_DETAILS_DUMPED,
            "osVersion": TEST_OS_VERSION,
            "blockDeviceMappings": None,
            "availabilityZonesTriggered": None,
            "userIpAddress": None,
            "containerName": None,
            "containerServiceName": None,
            "containerClusterName": None,
            "containerTaskArn": None,
            "oldInstanceId": None,
            "startDate": None,
            "isRetired": False,
            "provisionedCompoundProductId": None,
            "deploymentOption": None,
            "keyPairId": None,
        }
    )
    assertpy.assert_that(vers_meta.model_dump()).is_equal_to(
        {
            "accountId": "account-id-12345",
            "amiId": "ami-123",
            "awsAccountId": "001234567890",
            "isRecommendedVersion": True,
            "lastUpdateDate": "2000-01-01",
            "parameters": None,
            "productId": "prod-123",
            "projectId": "proj-123",
            "region": "us-east-1",
            "scProductId": "sc-prod-123",
            "scProvisioningArtifactId": "sc-vers-123",
            "stage": version.VersionStage.DEV,
            "technologyId": "t-123",
            "versionDescription": "Test Description",
            "versionId": "vers-123",
            "versionName": "1.0.0",
            "metadata": None,
            "componentVersionDetails": TEST_COMPONENT_VERSION_DETAILS_DUMPED,
            "osVersion": TEST_OS_VERSION,
        }
    )


def test_get_provisioned_virtual_target_should_raise_on_userid_mismatch(
    provisioned_product_query_service_mock,
    make_sample_provisioned_product,
    versions_query_service_mock,
    network_qry_srv_mock,
    parameter_service_mock,
):
    # ARRANGE
    provisioned_product_query_service_mock.get_provisioned_product.return_value = make_sample_provisioned_product(
        user_id="T1234",
    )
    virtual_target_domain_qry_srv = provisioned_products_domain_query_service.ProvisionedProductsDomainQueryService(
        provisioned_products_qry_srv=provisioned_product_query_service_mock,
        version_qry_srv=versions_query_service_mock,
        networking_qry_srv=network_qry_srv_mock,
        parameter_srv=parameter_service_mock,
    )
    # ACT & ASSERT
    with pytest.raises(DomainException) as e:
        virtual_target_domain_qry_srv.get_provisioned_product(
            project_id=project_id_value_object.from_str("proj-12345"),
            provisioned_product_id=provisioned_product_id_value_object.from_str("vt-1"),
            user_id=user_id_value_object.from_str("user-1"),
        )
        assertpy.assert_that(str(e.value)).is_equal_to("You do not have permissions to fetch the provisioned product")


def test_get_provisioned_product_ssh_key_returns_key_from_ssm_param(
    provisioned_product_query_service_mock,
    make_sample_provisioned_product,
    versions_query_service_mock,
    network_qry_srv_mock,
    parameter_service_mock,
):
    # ARRANGE
    parameter_service_mock.get_parameter_value.return_value = "123"

    provisioned_product_query_service_mock.get_provisioned_product.return_value = make_sample_provisioned_product(
        ssh_key_path="/a/b/c"
    )
    virtual_target_domain_qry_srv = provisioned_products_domain_query_service.ProvisionedProductsDomainQueryService(
        provisioned_products_qry_srv=provisioned_product_query_service_mock,
        version_qry_srv=versions_query_service_mock,
        networking_qry_srv=network_qry_srv_mock,
        parameter_srv=parameter_service_mock,
    )
    # ACT
    key = virtual_target_domain_qry_srv.get_provisioned_product_ssh_key(
        project_id=project_id_value_object.from_str("proj-12345"),
        provisioned_product_id=provisioned_product_id_value_object.from_str("vt-1"),
        user_id=user_id_value_object.from_str("user-1"),
    )
    # ASSERT
    assertpy.assert_that(key).is_equal_to("123")
    parameter_service_mock.get_parameter_value.assert_called_with(
        parameter_name="/a/b/c",
        aws_account_id="12345678912",
        region="us-east-1",
        user_id="user-1",
    )


def test_get_provisioned_product_secret_returns_user_credentials_from_parameter_service(
    provisioned_product_query_service_mock,
    make_sample_provisioned_product,
    versions_query_service_mock,
    network_qry_srv_mock,
    parameter_service_mock,
):
    # ARRANGE
    parameter_service_mock.get_secret_value.return_value = '{"username":"a", "password": "b"}'

    provisioned_product_query_service_mock.get_provisioned_product.return_value = make_sample_provisioned_product(
        user_credential_name="SecretId-123"
    )
    virtual_target_domain_qry_srv = provisioned_products_domain_query_service.ProvisionedProductsDomainQueryService(
        provisioned_products_qry_srv=provisioned_product_query_service_mock,
        version_qry_srv=versions_query_service_mock,
        networking_qry_srv=network_qry_srv_mock,
        parameter_srv=parameter_service_mock,
    )
    # ACT
    creds = virtual_target_domain_qry_srv.get_provisioned_product_user_credentials(
        project_id=project_id_value_object.from_str("proj-12345"),
        provisioned_product_id=provisioned_product_id_value_object.from_str("vt-1"),
        user_id=user_id_value_object.from_str("user-1"),
    )
    # ASSERT
    assertpy.assert_that(creds).is_equal_to(
        user_credential.UserCredential.model_validate({"username": "a", "password": "b"})
    )
    parameter_service_mock.get_secret_value.assert_called_with(
        secret_name="SecretId-123",
        aws_account_id="12345678912",
        region="us-east-1",
        user_id="user-1",
    )


def test_get_provisioned_virtual_target_should_return_raise_error_if_no_vt(
    provisioned_product_query_service_mock,
    make_sample_provisioned_product,
    versions_query_service_mock,
    network_qry_srv_mock,
    parameter_service_mock,
):
    # ARRANGE
    provisioned_product_query_service_mock.get_provisioned_product.return_value = None
    virtual_target_domain_qry_srv = provisioned_products_domain_query_service.ProvisionedProductsDomainQueryService(
        provisioned_products_qry_srv=provisioned_product_query_service_mock,
        version_qry_srv=versions_query_service_mock,
        networking_qry_srv=network_qry_srv_mock,
        parameter_srv=parameter_service_mock,
    )
    # ACT & ASSERT
    with pytest.raises(NotFoundError) as e:
        virtual_target_domain_qry_srv.get_provisioned_product(
            project_id=project_id_value_object.from_str("proj-12345"),
            provisioned_product_id=provisioned_product_id_value_object.from_str("vt-1"),
        )
        provisioned_product_query_service_mock.get_provisioned_product.assert_called_once_with(
            projectId="proj-12345", provisionedProductId="vt-1"
        )
        assertpy.assert_that(str(e.value)).is_equal_to("Provisioned product with id: vt-1 does not exist.")


def test_get_provisioned_products_filters_technical_parameters(
    provisioned_product_query_service_mock,
    make_sample_provisioned_product,
    versions_query_service_mock,
    network_qry_srv_mock,
    parameter_service_mock,
):
    # ARRANGE
    sample_provisioned_products = [
        make_sample_provisioned_product(f"vt-{i}", f"prod-{i}", user_id="user-1") for i in range(5)
    ]

    provisioned_product_query_service_mock.get_provisioned_products_by_user_id.return_value = (
        sample_provisioned_products
    )
    products_domain_qry_srv = provisioned_products_domain_query_service.ProvisionedProductsDomainQueryService(
        provisioned_products_qry_srv=provisioned_product_query_service_mock,
        version_qry_srv=versions_query_service_mock,
        networking_qry_srv=network_qry_srv_mock,
        parameter_srv=parameter_service_mock,
    )

    # ACT
    provisioned_products = products_domain_qry_srv.get_provisioned_products(
        project_id=project_id_value_object.from_str("proj-12345"),
        user_id=user_id_value_object.from_str("user-1"),
        provisioned_product_type=provisioned_product_type_value_object.from_str("Workbench"),
        return_technical_params=False,
    )

    # ASSERT
    assertpy.assert_that(provisioned_products).is_length(5)
    provisioned_product_query_service_mock.get_provisioned_products_by_user_id.assert_called_once()
    assertpy.assert_that(provisioned_products[0].provisioningParameters).is_length(1)
    assertpy.assert_that(provisioned_products[0].provisioningParameters[0].isTechnicalParameter).is_false()


def test_get_provisioned_product_filters_technical_parameters(
    provisioned_product_query_service_mock,
    make_sample_provisioned_product,
    versions_query_service_mock,
    network_qry_srv_mock,
    parameter_service_mock,
):
    # ARRANGE
    provisioned_product_query_service_mock.get_provisioned_product.return_value = make_sample_provisioned_product()
    provisioned_prods_domain_qry_srv = provisioned_products_domain_query_service.ProvisionedProductsDomainQueryService(
        provisioned_products_qry_srv=provisioned_product_query_service_mock,
        version_qry_srv=versions_query_service_mock,
        networking_qry_srv=network_qry_srv_mock,
        parameter_srv=parameter_service_mock,
    )
    # ACT
    pp, vers_meta = provisioned_prods_domain_qry_srv.get_provisioned_product(
        project_id=project_id_value_object.from_str("proj-12345"),
        provisioned_product_id=provisioned_product_id_value_object.from_str("vt-1"),
        return_technical_params=False,
    )
    # ASSERT
    provisioned_product_query_service_mock.get_provisioned_product.assert_called_once_with("proj-12345", "vt-1")
    assertpy.assert_that(pp.provisioningParameters).is_length(1)
    assertpy.assert_that(pp.provisioningParameters[0].isTechnicalParameter).is_false()


def test_get_provisioned_products_returns_active_provisioned_products_by_project(
    provisioned_product_query_service_mock,
    make_sample_provisioned_product,
    versions_query_service_mock,
    network_qry_srv_mock,
    parameter_service_mock,
):
    # ARRANGE
    sample_provisioned_products = [make_sample_provisioned_product(f"vt-{i}", f"prod-{i}") for i in range(5)]

    provisioned_product_query_service_mock.get_active_provisioned_products_by_project_id.return_value = (
        sample_provisioned_products
    )
    products_domain_qry_srv = provisioned_products_domain_query_service.ProvisionedProductsDomainQueryService(
        provisioned_products_qry_srv=provisioned_product_query_service_mock,
        version_qry_srv=versions_query_service_mock,
        networking_qry_srv=network_qry_srv_mock,
        parameter_srv=parameter_service_mock,
    )

    # ACT
    provisioned_products = products_domain_qry_srv.get_provisioned_products(
        project_id=project_id_value_object.from_str("proj-12345"),
        exclude_status=[product_status_value_object.from_str(product_status.ProductStatus.Terminated)],
        provisioned_product_type=provisioned_product_type_value_object.from_str("Workbench"),
    )

    # ASSERT
    assertpy.assert_that(provisioned_products).is_length(5)
    provisioned_product_query_service_mock.get_active_provisioned_products_by_project_id.assert_called_once()


def test_get_paginated_provisioned_products(
    provisioned_product_query_service_mock,
    make_sample_provisioned_product,
    versions_query_service_mock,
    network_qry_srv_mock,
    parameter_service_mock,
):
    # ARRANGE
    sample_provisioned_products = [make_sample_provisioned_product(f"vt-{i}", f"prod-{i}") for i in range(5)]

    provisioned_product_query_service_mock.get_provisioned_products_by_project_id_paginated.return_value = (
        sample_provisioned_products,
        {"PK": "proj-1", "SK": "pp-1"},
    )
    products_domain_qry_srv = provisioned_products_domain_query_service.ProvisionedProductsDomainQueryService(
        provisioned_products_qry_srv=provisioned_product_query_service_mock,
        version_qry_srv=versions_query_service_mock,
        networking_qry_srv=network_qry_srv_mock,
        parameter_srv=parameter_service_mock,
    )

    # ACT
    provisioned_products, paging_token = products_domain_qry_srv.get_paginated_provisioned_products(
        project_id=project_id_value_object.from_str("proj-12345"),
        paging_key=None,
        page_size=100,
        owner=user_id_value_object.from_str("user-1"),
        version_name=product_version_name_value_object.from_str("vers-name"),
        product_name=product_name_value_object.from_str("Product Name"),
        status=product_status_value_object.from_str(product_status.ProductStatus.Running),
        stage=provisioned_product_stage_value_object.from_str(provisioned_product.ProvisionedProductStage.QA),
        provisioned_product_type=provisioned_product_type_value_object.from_str("Workbench"),
        experimental=False,
    )

    # ASSERT
    assertpy.assert_that(provisioned_products).is_length(5)
    assertpy.assert_that(paging_token).is_equal_to({"PK": "proj-1", "SK": "pp-1"})
    provisioned_product_query_service_mock.get_provisioned_products_by_project_id_paginated.assert_called_once()
