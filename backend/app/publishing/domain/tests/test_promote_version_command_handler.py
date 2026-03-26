from datetime import datetime, timezone
from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.publishing.domain.command_handlers import promote_version_command_handler
from app.publishing.domain.commands import promote_version_command
from app.publishing.domain.events import (
    product_version_name_updated,
    product_version_promotion_started,
)
from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.model import portfolio, product, version
from app.publishing.domain.ports import portfolios_query_service, versions_query_service
from app.publishing.domain.read_models import component_version_detail
from app.publishing.domain.value_objects import (
    product_id_value_object,
    project_id_value_object,
    stage_value_object,
    user_id_value_object,
    user_role_value_object,
    version_id_value_object,
)
from app.shared.adapters.message_bus import message_bus
from app.shared.middleware.authorization import VirtualWorkbenchRoles

TEST_AWS_ACCOUNT_ID = "001234567890"
TEST_PROJECT_ID = "proj-12345"
TEST_PORTFOLIO_ID = "port-12345abc"
TEST_PRODUCT_ID = "prod-11111111"
TEST_SC_PORTFOLIO_ID = "port-12345"
TEST_TECHNOLOGY_ID = "tech-12345"
TEST_AWS_ACCOUNT_ID_2 = "123456789012"
TEST_ACCOUNT_ID = "1d0b2901-9482-4ce5-9d91-582fe0b14d7b"
TEST_REGION = "us-east-1"
TEST_VERSION_ID = "vers-11111111"
TEST_USER_ID = "T0011AA"
TEST_CREATE_DATE = "2023-06-20T00:00:00+00:00"
TEST_INTEGRATIONS = ["integration-1", "integration-2"]


@pytest.fixture()
def get_test_portfolio():
    def _get_test_portfolio(stage: str = "QA"):
        current_time = datetime.now(timezone.utc).isoformat()
        return portfolio.Portfolio(
            portfolioId=TEST_PORTFOLIO_ID,
            scPortfolioId=TEST_SC_PORTFOLIO_ID,
            projectId=TEST_PROJECT_ID,
            technologyId=TEST_TECHNOLOGY_ID,
            awsAccountId=TEST_AWS_ACCOUNT_ID_2,
            accountId=TEST_ACCOUNT_ID,
            stage=stage,
            region=TEST_REGION,
            status=portfolio.PortfolioStatus.Creating,
            createDate=current_time,
            lastUpdateDate=current_time,
        )

    return _get_test_portfolio


@pytest.fixture()
def portfolio_query_service_mock_qa(get_test_portfolio):
    portfolio_srv_mock = mock.create_autospec(spec=portfolios_query_service.PortfoliosQueryService)
    portfolio_srv_mock.get_portfolios_by_tech_and_stage.return_value = [get_test_portfolio("QA")]
    return portfolio_srv_mock


@pytest.fixture()
def portfolio_query_service_mock_prod(get_test_portfolio):
    portfolio_srv_mock = mock.create_autospec(spec=portfolios_query_service.PortfoliosQueryService)
    portfolio_srv_mock.get_portfolios_by_tech_and_stage.return_value = [get_test_portfolio("PROD")]
    return portfolio_srv_mock


@pytest.fixture()
def get_test_version():
    def _get_test_version(
        is_recommended_version: bool = True,
        aws_account_id: str = TEST_AWS_ACCOUNT_ID_2,
        account_id: str = TEST_ACCOUNT_ID,
        version_id: str = TEST_VERSION_ID,
        version_status: str = version.VersionStatus.Created,
        version_name: str = "1.0.0-rc.12",
        version_type: str = version.VersionType.ReleaseCandidate.text,
        product_type: product.ProductType = product.ProductType.Workbench,
        stage: str = "DEV",
        project_id: str = TEST_PROJECT_ID,
        product_id: str = TEST_PRODUCT_ID,
        technology_id: str = TEST_TECHNOLOGY_ID,
        sc_portfolio_id: str = TEST_SC_PORTFOLIO_ID,
        os_version: str = "Ubuntu 24",
        create_date: str = TEST_CREATE_DATE,
        last_update_date: str = TEST_CREATE_DATE,
        created_by: str = TEST_USER_ID,
        last_updated_by: str = TEST_USER_ID,
        region: str = TEST_REGION,
        version_description: str = "Workbench version description",
        integrations: list[str] = TEST_INTEGRATIONS,
        has_integrations: bool = True,
    ):
        additional_attributes = {
            "originalAmiId": "ami-023c04780e65e723c",
            "componentVersionDetails": [
                component_version_detail.ComponentVersionDetail(
                    componentName="VS Code",
                    componentVersionType=component_version_detail.ComponentVersionEntryType.Main,
                    softwareVendor="Microsoft",
                    softwareVersion="1.87.0",
                )
            ],
            "integrations": integrations,
            "hasIntegrations": has_integrations,
        }
        return version.Version(
            versionId=version_id,
            projectId=project_id,
            productId=product_id,
            scPortfolioId=sc_portfolio_id,
            versionDescription=version_description,
            versionName=version_name,
            versionType=version_type,
            draftTemplateLocation=f"{product_id}/{version_id}/draft_workbench.yml",
            technologyId=technology_id,
            awsAccountId=aws_account_id,
            accountId=account_id,
            stage=stage,
            region=region,
            status=version_status,
            isRecommendedVersion=is_recommended_version,
            osVersion=os_version,
            createDate=create_date,
            lastUpdateDate=last_update_date,
            createdBy=created_by,
            lastUpdatedBy=last_updated_by,
            **additional_attributes,
        )

    return _get_test_version


@pytest.fixture()
def version_query_service_mock(get_test_version):
    version_qry_srv = mock.create_autospec(spec=versions_query_service.VersionsQueryService)
    return version_qry_srv


@pytest.fixture()
def get_test_product():
    def _get_test_product(
        project_id: str = TEST_PROJECT_ID,
        product_id: str = TEST_PRODUCT_ID,
        technology_id: str = TEST_TECHNOLOGY_ID,
        status: product.ProductStatus = product.ProductStatus.Created,
        product_type: product.ProductType = product.ProductType.Workbench,
    ):
        return product.Product(
            projectId=project_id,
            productId=product_id,
            technologyId=technology_id,
            technologyName="Test technology",
            status=status,
            productName="My Product",
            productType=product_type,
            productDescription="My Description",
            recommendedVersionId=None,
            createDate=TEST_CREATE_DATE,
            lastUpdateDate=TEST_CREATE_DATE,
            createdBy=TEST_USER_ID,
            lastUpdatedBy=TEST_USER_ID,
        )

    return _get_test_product


@freeze_time("2023-06-20")
@pytest.mark.parametrize(
    "product_type",
    (product.ProductType.Workbench, product.ProductType.VirtualTarget),
)
def test_handle_should_promote_version_to_qa(
    portfolio_query_service_mock_qa,
    version_query_service_mock,
    product_type,
    get_test_version,
    get_test_product,
    mock_unit_of_work,
    mock_version_repo,
    mock_products_repo,
    mock_amis_query_service,
):
    # ARRANGE
    version_query_service_mock.get_product_version_distributions.return_value = [
        get_test_version(product_type=product_type),
        get_test_version(aws_account_id=TEST_AWS_ACCOUNT_ID, product_type=product_type),
    ]
    mock_products_repo.get.return_value = get_test_product(product_type=product_type)
    expected_entity = get_test_version(
        product_type=product_type,
        aws_account_id=TEST_AWS_ACCOUNT_ID_2,
        stage="QA",
        version_status=version.VersionStatus.Creating,
    )
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)

    promote_product_version_command_mock = promote_version_command.PromoteVersionCommand(
        projectId=project_id_value_object.from_str(TEST_PROJECT_ID),
        productId=product_id_value_object.from_str(TEST_PRODUCT_ID),
        versionId=version_id_value_object.from_str(TEST_VERSION_ID),
        createdBy=user_id_value_object.from_str(TEST_USER_ID),
        userRoles=[user_role_value_object.from_str(VirtualWorkbenchRoles.Admin)],
        stage=stage_value_object.from_str("QA"),
    )

    # ACT
    promote_version_command_handler.handle(
        command=promote_product_version_command_mock,
        uow=mock_unit_of_work,
        message_bus=message_bus_mock,
        portf_qry_srv=portfolio_query_service_mock_qa,
        versions_qry_srv=version_query_service_mock,
        amis_qry_srv=mock_amis_query_service,
    )

    # ASSERT
    version_query_service_mock.get_product_version_distributions.assert_any_call(TEST_PRODUCT_ID, TEST_VERSION_ID)
    portfolio_query_service_mock_qa.get_portfolios_by_tech_and_stage.assert_any_call(TEST_TECHNOLOGY_ID, "QA")
    mock_version_repo.add.assert_called_once_with(expected_entity)
    mock_unit_of_work.commit.assert_called()
    message_bus_mock.publish.assert_called_once_with(
        product_version_promotion_started.ProductVersionPromotionStarted(
            product_id=TEST_PRODUCT_ID,
            version_id=TEST_VERSION_ID,
            aws_account_id=TEST_AWS_ACCOUNT_ID_2,
            product_type=product_type,
        )
    )


@freeze_time("2023-06-20")
@pytest.mark.parametrize(
    "product_type",
    (product.ProductType.Workbench, product.ProductType.VirtualTarget),
)
def test_handle_should_promote_version_to_prod(
    portfolio_query_service_mock_prod,
    version_query_service_mock,
    mock_products_repo,
    get_test_version,
    get_test_product,
    product_type,
    mock_unit_of_work,
    mock_version_repo,
    mock_amis_query_service,
):
    # ARRANGE
    version_query_service_mock.get_product_version_distributions.return_value = [
        get_test_version(product_type=product_type),
        get_test_version(product_type=product_type, aws_account_id=TEST_AWS_ACCOUNT_ID, stage="QA"),
    ]
    mock_products_repo.get.return_value = get_test_product(product_type=product_type)
    expected_entity = get_test_version(
        product_type=product_type,
        aws_account_id=TEST_AWS_ACCOUNT_ID_2,
        stage="PROD",
        version_status=version.VersionStatus.Creating,
        version_name="1.0.0",
        version_type="RELEASED",
    )
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)

    promote_product_version_command_mock = promote_version_command.PromoteVersionCommand(
        projectId=project_id_value_object.from_str(TEST_PROJECT_ID),
        productId=product_id_value_object.from_str(TEST_PRODUCT_ID),
        versionId=version_id_value_object.from_str(TEST_VERSION_ID),
        createdBy=user_id_value_object.from_str(TEST_USER_ID),
        userRoles=[user_role_value_object.from_str(VirtualWorkbenchRoles.Admin)],
        stage=stage_value_object.from_str("PROD"),
    )

    # ACT
    promote_version_command_handler.handle(
        command=promote_product_version_command_mock,
        uow=mock_unit_of_work,
        message_bus=message_bus_mock,
        portf_qry_srv=portfolio_query_service_mock_prod,
        versions_qry_srv=version_query_service_mock,
        amis_qry_srv=mock_amis_query_service,
    )

    # ASSERT
    version_query_service_mock.get_product_version_distributions.assert_any_call(TEST_PRODUCT_ID, TEST_VERSION_ID)
    portfolio_query_service_mock_prod.get_portfolios_by_tech_and_stage.assert_any_call(TEST_TECHNOLOGY_ID, "PROD")
    current_time = datetime.now(timezone.utc).isoformat()
    mock_version_repo.update_attributes.assert_called_with(
        pk=version.VersionPrimaryKey(
            productId=TEST_PRODUCT_ID,
            versionId="vers-11111111",
            awsAccountId="001234567890",
        ),
        versionName="1.0.0",
        versionType=version.VersionType.Released.text,
        lastUpdateDate=current_time,
        lastUpdatedBy=TEST_USER_ID,
        status=version.VersionStatus.Updating,
    )
    message_bus_mock.publish.assert_any_call(
        product_version_name_updated.ProductVersionNameUpdated(
            project_id=TEST_PROJECT_ID,
            product_id=TEST_PRODUCT_ID,
            version_id=TEST_VERSION_ID,
            version_name="1.0.0",
            aws_account_id=TEST_AWS_ACCOUNT_ID_2,
            integrations=TEST_INTEGRATIONS,
            has_integrations=True,
        )
    )
    mock_version_repo.add.assert_called_once_with(expected_entity)
    mock_unit_of_work.commit.assert_called()
    message_bus_mock.publish.assert_any_call(
        product_version_promotion_started.ProductVersionPromotionStarted(
            product_id=TEST_PRODUCT_ID,
            version_id=TEST_VERSION_ID,
            aws_account_id=TEST_AWS_ACCOUNT_ID_2,
            product_type=product_type,
        )
    )


@freeze_time("2023-06-20")
def test_handle_with_retired_versions_should_raise(
    mock_unit_of_work,
    portfolio_query_service_mock_qa,
    version_query_service_mock,
    mock_products_repo,
    get_test_version,
    get_test_product,
    mock_amis_query_service,
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    version_query_service_mock.get_product_version_distributions.return_value = [
        get_test_version(),
        get_test_version(aws_account_id=TEST_AWS_ACCOUNT_ID),
        get_test_version(version_status=version.VersionStatus.Retired),
    ]
    mock_products_repo.get.return_value = get_test_product()
    promote_product_version_command_mock = promote_version_command.PromoteVersionCommand(
        projectId=project_id_value_object.from_str(TEST_PROJECT_ID),
        productId=product_id_value_object.from_str(TEST_PRODUCT_ID),
        versionId=version_id_value_object.from_str(TEST_VERSION_ID),
        createdBy=user_id_value_object.from_str(TEST_USER_ID),
        userRoles=[user_role_value_object.from_str(VirtualWorkbenchRoles.Admin)],
        stage=stage_value_object.from_str("QA"),
    )

    # Act and Assert
    with pytest.raises(domain_exception.DomainException):
        promote_version_command_handler.handle(
            command=promote_product_version_command_mock,
            uow=mock_unit_of_work,
            message_bus=message_bus_mock,
            portf_qry_srv=portfolio_query_service_mock_qa,
            versions_qry_srv=version_query_service_mock,
            amis_qry_srv=mock_amis_query_service,
        )


@freeze_time("2023-06-20")
def test_handle_with_role_without_permission_for_prod_should_raise(
    mock_unit_of_work,
    portfolio_query_service_mock_prod,
    version_query_service_mock,
    mock_products_repo,
    get_test_version,
    get_test_product,
    mock_amis_query_service,
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    version_query_service_mock.get_product_version_distributions.return_value = [
        get_test_version(),
        get_test_version(aws_account_id=TEST_AWS_ACCOUNT_ID),
        get_test_version(version_status=version.VersionStatus.Retired),
    ]
    mock_products_repo.get.return_value = get_test_product()
    promote_product_version_command_mock = promote_version_command.PromoteVersionCommand(
        projectId=project_id_value_object.from_str(TEST_PROJECT_ID),
        productId=product_id_value_object.from_str(TEST_PRODUCT_ID),
        versionId=version_id_value_object.from_str(TEST_VERSION_ID),
        createdBy=user_id_value_object.from_str(TEST_USER_ID),
        userRoles=[user_role_value_object.from_str(VirtualWorkbenchRoles.BetaUser)],
        stage=stage_value_object.from_str("PROD"),
    )

    # Act and Assert
    with pytest.raises(domain_exception.DomainException):
        promote_version_command_handler.handle(
            command=promote_product_version_command_mock,
            uow=mock_unit_of_work,
            message_bus=message_bus_mock,
            portf_qry_srv=portfolio_query_service_mock_prod,
            versions_qry_srv=version_query_service_mock,
            amis_qry_srv=mock_amis_query_service,
        )


@freeze_time("2023-06-20")
def test_handle_promote_restored_version_to_prod_raises_error(
    mock_unit_of_work,
    portfolio_query_service_mock_prod,
    version_query_service_mock,
    mock_products_repo,
    get_test_version,
    get_test_product,
    mock_amis_query_service,
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    version_query_service_mock.get_product_version_distributions.return_value = [
        get_test_version(),
        get_test_version(aws_account_id=TEST_AWS_ACCOUNT_ID),
    ]
    mock_products_repo.get.return_value = get_test_product()

    promote_product_version_command_mock = promote_version_command.PromoteVersionCommand(
        projectId=project_id_value_object.from_str(TEST_PROJECT_ID),
        productId=product_id_value_object.from_str(TEST_PRODUCT_ID),
        versionId=version_id_value_object.from_str(TEST_VERSION_ID),
        createdBy=user_id_value_object.from_str(TEST_USER_ID),
        userRoles=[user_role_value_object.from_str(VirtualWorkbenchRoles.PowerUser)],
        stage=stage_value_object.from_str("PROD"),
    )

    version_query_service_mock.get_product_version_distributions.return_value = [
        get_test_version(version_status=version.VersionStatus.Created),
        get_test_version(
            account_id=TEST_AWS_ACCOUNT_ID,
            version_name="1.0.0-restored.1",
            version_type=version.VersionType.Restored.text,
            version_status=version.VersionStatus.Created,
        ),
    ]

    # Act and Assert
    with pytest.raises(domain_exception.DomainException) as error:
        promote_version_command_handler.handle(
            command=promote_product_version_command_mock,
            uow=mock_unit_of_work,
            message_bus=message_bus_mock,
            portf_qry_srv=portfolio_query_service_mock_prod,
            versions_qry_srv=version_query_service_mock,
            amis_qry_srv=mock_amis_query_service,
        )
    assertpy.assert_that(str(error.value)).is_equal_to("Only release candidate versions can be promoted to PROD")


@freeze_time("2023-06-20")
@pytest.mark.parametrize(
    "product_type,error_message",
    (
        (
            product.ProductType.Workbench,
            "Original AMI was retired. Update product version with available AMI",
        ),
        (
            product.ProductType.VirtualTarget,
            "Original AMI was retired. Update product version with available AMI",
        ),
    ),
)
def test_handle_promote_restored_version_to_prod_raises_error_if_ami_retired(
    product_type,
    error_message,
    mock_unit_of_work,
    portfolio_query_service_mock_prod,
    version_query_service_mock,
    mock_products_repo,
    get_test_version,
    get_test_product,
    mock_amis_query_service,
):
    # ARRANGE
    mock_amis_query_service.get_ami.return_value = None
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    version_query_service_mock.get_product_version_distributions.return_value = [
        get_test_version(product_type=product_type),
        get_test_version(product_type=product_type, aws_account_id=TEST_AWS_ACCOUNT_ID),
    ]
    mock_products_repo.get.return_value = get_test_product(product_type=product_type)

    promote_product_version_command_mock = promote_version_command.PromoteVersionCommand(
        projectId=project_id_value_object.from_str(TEST_PROJECT_ID),
        productId=product_id_value_object.from_str(TEST_PRODUCT_ID),
        versionId=version_id_value_object.from_str(TEST_VERSION_ID),
        createdBy=user_id_value_object.from_str(TEST_USER_ID),
        userRoles=[user_role_value_object.from_str(VirtualWorkbenchRoles.PowerUser)],
        stage=stage_value_object.from_str("PROD"),
    )

    version_query_service_mock.get_product_version_distributions.return_value = [
        get_test_version(product_type=product_type, version_status=version.VersionStatus.Created)
    ]

    # Act and Assert
    with pytest.raises(domain_exception.DomainException) as error:
        promote_version_command_handler.handle(
            command=promote_product_version_command_mock,
            uow=mock_unit_of_work,
            message_bus=message_bus_mock,
            portf_qry_srv=portfolio_query_service_mock_prod,
            versions_qry_srv=version_query_service_mock,
            amis_qry_srv=mock_amis_query_service,
        )
    assertpy.assert_that(str(error.value)).is_equal_to(error_message)
    mock_unit_of_work.commit.assert_not_called()
