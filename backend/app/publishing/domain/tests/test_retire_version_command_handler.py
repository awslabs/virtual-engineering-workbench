from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.publishing.domain.command_handlers import retire_version_command_handler
from app.publishing.domain.commands import retire_version_command
from app.publishing.domain.events import product_version_retirement_started
from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.model import product, version
from app.publishing.domain.ports import versions_query_service
from app.publishing.domain.value_objects import (
    product_id_value_object,
    project_id_value_object,
    user_id_value_object,
    user_role_value_object,
    version_id_value_object,
)
from app.shared.adapters.message_bus import message_bus
from app.shared.middleware.authorization import VirtualWorkbenchRoles


@pytest.fixture()
def get_test_versions():
    def _get_test_versions(version_id: str = "version-123"):
        return [
            version.Version(
                projectId="proj-12345",
                productId="prod-12345abc",
                versionId=version_id,
                scPortfolioId="port-12345",
                versionDescription="Product version description",
                versionName="1.0.0-rc.2",
                versionType=version.VersionType.ReleaseCandidate.text,
                technologyId="tech-12345",
                awsAccountId=f"{i}",
                stage="DEV",
                region="us-east-1",
                originalAmiId="ami-023c04780e65e723c",
                status=version.VersionStatus.Created,
                isRecommendedVersion=True,
                createDate="2023-06-20T00:00:00+00:00",
                lastUpdateDate="2023-06-20T00:00:00+00:00",
                createdBy="T0037SG",
                lastUpdatedBy="T0037SG",
            )
            for i in range(1, 4)
        ]

    return _get_test_versions


@pytest.fixture()
def message_bus_mock():
    mess_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    return mess_bus_mock


@pytest.fixture()
def retire_version_command_mock():
    retire_version_command_mock = retire_version_command.RetireVersionCommand(
        projectId=project_id_value_object.from_str("proj-12345"),
        productId=product_id_value_object.from_str("prod-12345abc"),
        versionId=version_id_value_object.from_str("vers-12345abc"),
        retiredBy=user_id_value_object.from_str("T0037SG"),
        userRoles=[user_role_value_object.from_str(VirtualWorkbenchRoles.Admin)],
        retireReason="Some reason",
    )
    return retire_version_command_mock


@pytest.fixture
def get_version():
    def _get_version():

        return version.Version(
            projectId="proj-12345",
            productId="prod-12345abc",
            technologyId="tech-12345",
            versionId="vers-12345abc",
            versionName="1.0.0-rc.2",
            versionType=version.VersionType.ReleaseCandidate.text,
            awsAccountId="123456789012",
            stage=version.VersionStage.DEV,
            region="us-east-1",
            originalAmiId="ami-12345",
            copiedAmiId="ami-12345",
            status=version.VersionStatus.Created,
            scPortfolioId="port-12345",
            isRecommendedVersion=True,
            createDate="2023-07-13T00:00:00+00:00",
            lastUpdateDate="2023-07-13T00:00:00+00:00",
            createdBy="T000001",
            lastUpdatedBy="T000001",
        )

    return _get_version


@pytest.fixture
def get_product():
    def _get_product():
        return product.Product(
            projectId="proj-12345",
            productId="prod-12345abc",
            technologyId="tech-12345",
            technologyName="Test technology",
            status=product.ProductStatus.Created,
            productName="My product",
            productType=product.ProductType.Workbench,
            recommendedVersionId="vers-12345abc",
            createDate="2023-07-13T00:00:00+00:00",
            lastUpdateDate="2023-07-13T00:00:00+00:00",
            createdBy="T000001",
            lastUpdatedBy="T000001",
        )

    return _get_product


@pytest.fixture()
def version_query_service_mock(get_test_versions):
    version_qry_srv = mock.create_autospec(spec=versions_query_service.VersionsQueryService)
    version_qry_srv.get_product_version_distributions.return_value = get_test_versions()
    return version_qry_srv


@freeze_time("2023-07-24")
def test_retire_version_retires_version(
    retire_version_command_mock,
    mock_unit_of_work,
    message_bus_mock,
    version_query_service_mock,
    mock_version_repo,
    mock_products_repo,
    get_version,
    get_product,
):
    # ARRANGE
    mock_version_repo.get.return_value = get_version()
    mock_products_repo.get.return_value = get_product()
    # ACT
    retire_version_command_handler.handle(
        command=retire_version_command_mock,
        uow=mock_unit_of_work,
        message_bus=message_bus_mock,
        versions_qry_srv=version_query_service_mock,
    )
    # ASSERT
    mock_products_repo.update_attributes.assert_called_with(
        pk=product.ProductPrimaryKey(
            projectId=retire_version_command_mock.projectId.value,
            productId=retire_version_command_mock.productId.value,
        ),
        recommendedVersionId=None,
        lastUpdateDate="2023-07-24T00:00:00+00:00",
        lastUpdatedBy=retire_version_command_mock.retiredBy.value,
    )
    mock_version_repo.update_attributes.assert_any_call(
        version.VersionPrimaryKey(
            productId=retire_version_command_mock.productId.value,
            versionId=retire_version_command_mock.versionId.value,
            awsAccountId="1",
        ),
        lastUpdateDate="2023-07-24T00:00:00+00:00",
        lastUpdatedBy=retire_version_command_mock.retiredBy.value,
        status=version.VersionStatus.Retiring,
        retireReason=retire_version_command_mock.retireReason,
        isRecommendedVersion=False,
    )
    version_query_service_mock.get_product_version_distributions.assert_called_once_with(
        "prod-12345abc", "vers-12345abc"
    )
    assertpy.assert_that(mock_unit_of_work.commit.call_count).is_equal_to(3)
    message_bus_mock.publish.assert_any_call(
        product_version_retirement_started.ProductVersionRetirementStarted(
            product_id="prod-12345abc", version_id="version-123", aws_account_id="1"
        )
    )


def test_retires_version_handler_does_not_retire_version_in_prod_if_role_is_invalid(
    retire_version_command_mock, mock_unit_of_work, message_bus_mock, version_query_service_mock, get_test_versions
):
    # ARRANGE
    retire_version_command_mock.userRoles = [user_role_value_object.from_str(VirtualWorkbenchRoles.ProductContributor)]
    fetched_versions_mock = get_test_versions()
    fetched_versions_mock[0].stage = version.VersionStage.PROD
    version_query_service_mock.get_product_version_distributions.return_value = fetched_versions_mock
    # ACT & ASSERT
    with pytest.raises(domain_exception.DomainException) as error:
        retire_version_command_handler.handle(
            command=retire_version_command_mock,
            uow=mock_unit_of_work,
            message_bus=message_bus_mock,
            versions_qry_srv=version_query_service_mock,
        )
        assertpy.assert_that(str(error.value)).is_equal_to(
            "Only power users and above can retire a version in PROD stage."
        )


def test_retires_version_handler_raise_error_if_product_has_invalid_status(
    retire_version_command_mock, mock_unit_of_work, message_bus_mock, version_query_service_mock, mock_products_repo
):
    # ARRANGE
    mock_products_repo.get.return_value = product.Product(
        projectId="proj-12345",
        productId="prod-12345abc",
        technologyId="tech-12345",
        technologyName="Test technology",
        status=product.ProductStatus.Creating,
        productName="My product",
        productType=product.ProductType.Workbench,
        createDate="2023-07-13T00:00:00+00:00",
        lastUpdateDate="2023-07-13T00:00:00+00:00",
        createdBy="T000001",
        lastUpdatedBy="T000001",
    )
    # ACT & ASSERT
    with pytest.raises(domain_exception.DomainException) as error:
        retire_version_command_handler.handle(
            command=retire_version_command_mock,
            uow=mock_unit_of_work,
            message_bus=message_bus_mock,
            versions_qry_srv=version_query_service_mock,
        )
        assertpy.assert_that(str(error.value)).is_equal_to("Product can only be retired with status 'Created'")


def test_retires_version_handler_raise_error_if_no_versions_distributions(
    retire_version_command_mock,
    mock_unit_of_work,
    message_bus_mock,
    version_query_service_mock,
):
    # ARRANGE
    version_query_service_mock.get_product_version_distributions.return_value = []
    # ACT & ASSERT
    with pytest.raises(domain_exception.DomainException) as error:
        retire_version_command_handler.handle(
            command=retire_version_command_mock,
            uow=mock_unit_of_work,
            message_bus=message_bus_mock,
            versions_qry_srv=version_query_service_mock,
        )
        assertpy.assert_that(str(error.value)).is_equal_to("Product version not found")


def test_retires_version_handler_raise_error_if_not_all_versions_has_created_status(
    retire_version_command_mock, mock_unit_of_work, message_bus_mock, version_query_service_mock, get_test_versions
):
    # ARRANGE
    fetched_versions_mock = get_test_versions()
    fetched_versions_mock[0].status = version.VersionStatus.Creating
    version_query_service_mock.get_product_version_distributions.return_value = fetched_versions_mock
    # ACT & ASSERT
    with pytest.raises(domain_exception.DomainException) as error:
        retire_version_command_handler.handle(
            command=retire_version_command_mock,
            uow=mock_unit_of_work,
            message_bus=message_bus_mock,
            versions_qry_srv=version_query_service_mock,
        )
        assertpy.assert_that(str(error.value)).is_equal_to(
            "Product version can only be retired if the status of all distributed versions is 'Created'"
        )


def test_retire_version_command_handler_do_not_retire_version_if_there_is_only_one_product_version(
    retire_version_command_mock, mock_unit_of_work, message_bus_mock, version_query_service_mock, get_test_versions
):
    # ARRANGE
    fetched_versions_mock = get_test_versions()[:1]
    fetched_versions_mock[0].status = version.VersionStatus.Creating
    version_query_service_mock.get_product_version_distributions.return_value = fetched_versions_mock
    # ACT & ASSERT
    with pytest.raises(domain_exception.DomainException) as error:
        retire_version_command_handler.handle(
            command=retire_version_command_mock,
            uow=mock_unit_of_work,
            message_bus=message_bus_mock,
            versions_qry_srv=version_query_service_mock,
        )
        assertpy.assert_that(str(error.value)).is_equal_to(
            "Product version can not be retired because it is the only product version"
        )


def test_retire_version_command_handler_do_not_retire_version_if_the_product_version_is_latest(
    retire_version_command_mock, mock_unit_of_work, message_bus_mock, version_query_service_mock, get_test_versions
):
    # ARRANGE
    fetched_versions_mock = get_test_versions()
    version_query_service_mock.get_product_version_distributions.return_value = fetched_versions_mock
    version_query_service_mock.get_latest_version_name_and_id.return_value = "1.0.0-rc.2", "vers-1234"
    # ACT & ASSERT
    with pytest.raises(domain_exception.DomainException) as error:
        retire_version_command_handler.handle(
            command=retire_version_command_mock,
            uow=mock_unit_of_work,
            message_bus=message_bus_mock,
            versions_qry_srv=version_query_service_mock,
        )
        assertpy.assert_that(str(error.value)).is_equal_to("Latest version can not be retired")
