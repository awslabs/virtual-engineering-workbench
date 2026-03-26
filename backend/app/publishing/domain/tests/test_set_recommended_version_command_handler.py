from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.publishing.domain.command_handlers import set_recommended_version_command_handler
from app.publishing.domain.commands import set_recommended_version_command
from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.model import product, version
from app.publishing.domain.ports import products_query_service, versions_query_service
from app.publishing.domain.value_objects import (
    product_id_value_object,
    project_id_value_object,
    user_id_value_object,
    version_id_value_object,
)
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work


@pytest.fixture()
def command_mock(new_version_id) -> set_recommended_version_command.SetRecommendedVersionCommand:
    return set_recommended_version_command.SetRecommendedVersionCommand(
        projectId=project_id_value_object.from_str("proj-0000"),
        productId=product_id_value_object.from_str("prod-1111"),
        versionId=version_id_value_object.from_str(new_version_id),
        userId=user_id_value_object.from_str("T0000AA"),
    )


@pytest.fixture
def message_bus_mock():
    return mock.create_autospec(spec=message_bus.MessageBus)


@pytest.fixture
def products_qs_mock(mocked_product):
    mock_inst = mock.create_autospec(spec=products_query_service.ProductsQueryService)
    mock_inst.get_product.return_value = mocked_product
    return mock_inst


@pytest.fixture
def versions_qs_mock(mock_product_version):
    mock_inst = mock.create_autospec(spec=versions_query_service.VersionsQueryService)

    def _get_versions_mock(**kwargs):
        if "version_id" in kwargs:
            return [
                mock_product_version(versionId=kwargs.get("version_id"), is_recommented_version=False),
                mock_product_version(
                    versionId=kwargs.get("version_id"), is_recommented_version=False, aws_account_id="123456789000"
                ),
                mock_product_version(
                    versionId=kwargs.get("version_id"),
                    is_recommented_version=False,
                    aws_account_id="000000000000",
                    stage=version.VersionStage.DEV,
                ),
                mock_product_version(
                    versionId=kwargs.get("version_id"),
                    is_recommented_version=False,
                    aws_account_id="111111111111",
                    stage=version.VersionStage.QA,
                ),
            ]

        return [mock_product_version(), mock_product_version(aws_account_id="123456789000")]

    mock_inst.get_product_version_distributions.side_effect = _get_versions_mock
    return mock_inst


@pytest.fixture
def old_version_id():
    return "vers-3333"


@pytest.fixture
def new_version_id():
    return "vers-2222"


@pytest.fixture
def mocked_product():
    return product.Product(
        projectId="proj-0000",
        productId="prod-1111",
        technologyId="tech=2222",
        technologyName="Technology for Test",
        status=product.ProductStatus.Created,
        productName="Test Product",
        productType=product.ProductType.Workbench,
        createDate="2023-09-01",
        lastUpdateDate="2023-09-01",
        createdBy="T0000AA",
        lastUpdatedBy="T0000AA",
    )


@pytest.fixture
def mock_product_version(old_version_id):
    def _mock_product_version(
        is_recommented_version: bool = True,
        aws_account_id: str = "012345678900",
        versionId: str = old_version_id,
        stage: version.VersionStage = version.VersionStage.PROD,
        status: version.VersionStatus = version.VersionStatus.Created,
    ):
        return version.Version(
            projectId="proj-0000",
            productId="prod-1111",
            technologyId="tech=2222",
            versionId=versionId,
            versionName="1.0.1",
            versionType=version.VersionType.ReleaseCandidate.text,
            awsAccountId=aws_account_id,
            stage=stage,
            region="us-east-1",
            originalAmiId="ami-0000",
            status=status,
            scPortfolioId="portf-4444",
            isRecommendedVersion=is_recommented_version,
            createDate="2023-09-01",
            lastUpdateDate="2023-09-01",
            createdBy="T0000AA",
            lastUpdatedBy="T0000AA",
        )

    return _mock_product_version


@freeze_time("2023-09-28")
def test_handle_should_update_product_entity(
    command_mock: set_recommended_version_command.SetRecommendedVersionCommand,
    mock_unit_of_work: unit_of_work.UnitOfWork,
    message_bus_mock,
    versions_qs_mock: versions_query_service.VersionsQueryService,
    mock_products_repo,
    products_qs_mock: products_query_service.ProductsQueryService,
    new_version_id,
):
    # ARRANGE

    # ACT
    set_recommended_version_command_handler.handle(
        cmd=command_mock,
        products_query_service=products_qs_mock,
        versions_qry_srv=versions_qs_mock,
        uow=mock_unit_of_work,
        msg_bus=message_bus_mock,
    )

    # ASSERT
    mock_products_repo.update_attributes.assert_called_once_with(
        product.ProductPrimaryKey(
            projectId="proj-0000",
            productId="prod-1111",
        ),
        recommendedVersionId=new_version_id,
        lastUpdateDate="2023-09-28T00:00:00+00:00",
        lastUpdatedBy="T0000AA",
    )
    mock_unit_of_work.commit.assert_called_once()


@freeze_time("2023-09-28")
def test_handle_should_cleanup_old_recommended_version_entities(
    command_mock: set_recommended_version_command.SetRecommendedVersionCommand,
    mock_unit_of_work: unit_of_work.UnitOfWork,
    message_bus_mock,
    versions_qs_mock: versions_query_service.VersionsQueryService,
    mock_version_repo,
    products_qs_mock: products_query_service.ProductsQueryService,
    old_version_id,
):
    # ARRANGE

    # ACT
    set_recommended_version_command_handler.handle(
        cmd=command_mock,
        products_query_service=products_qs_mock,
        versions_qry_srv=versions_qs_mock,
        uow=mock_unit_of_work,
        msg_bus=message_bus_mock,
    )

    # ASSERT
    mock_version_repo.update_attributes.assert_any_call(
        version.VersionPrimaryKey(
            productId="prod-1111",
            versionId=old_version_id,
            awsAccountId="012345678900",
        ),
        isRecommendedVersion=False,
        lastUpdateDate="2023-09-28T00:00:00+00:00",
        lastUpdatedBy="T0000AA",
    )
    mock_version_repo.update_attributes.assert_any_call(
        version.VersionPrimaryKey(
            productId="prod-1111",
            versionId=old_version_id,
            awsAccountId="123456789000",
        ),
        isRecommendedVersion=False,
        lastUpdateDate="2023-09-28T00:00:00+00:00",
        lastUpdatedBy="T0000AA",
    )

    mock_unit_of_work.commit.assert_called_once()


@freeze_time("2023-09-28")
def test_handle_should_update_version_to_recommended(
    command_mock: set_recommended_version_command.SetRecommendedVersionCommand,
    mock_unit_of_work: unit_of_work.UnitOfWork,
    message_bus_mock,
    versions_qs_mock: versions_query_service.VersionsQueryService,
    mock_version_repo,
    products_qs_mock: products_query_service.ProductsQueryService,
    new_version_id,
):
    # ARRANGE

    # ACT
    set_recommended_version_command_handler.handle(
        cmd=command_mock,
        products_query_service=products_qs_mock,
        versions_qry_srv=versions_qs_mock,
        uow=mock_unit_of_work,
        msg_bus=message_bus_mock,
    )

    # ASSERT
    mock_version_repo.update_attributes.assert_any_call(
        version.VersionPrimaryKey(
            productId="prod-1111",
            versionId=new_version_id,
            awsAccountId="012345678900",
        ),
        isRecommendedVersion=True,
        lastUpdateDate="2023-09-28T00:00:00+00:00",
        lastUpdatedBy="T0000AA",
    )
    mock_version_repo.update_attributes.assert_any_call(
        version.VersionPrimaryKey(
            productId="prod-1111",
            versionId=new_version_id,
            awsAccountId="123456789000",
        ),
        isRecommendedVersion=True,
        lastUpdateDate="2023-09-28T00:00:00+00:00",
        lastUpdatedBy="T0000AA",
    )
    mock_version_repo.update_attributes.assert_any_call(
        version.VersionPrimaryKey(
            productId="prod-1111",
            versionId=new_version_id,
            awsAccountId="000000000000",
        ),
        isRecommendedVersion=True,
        lastUpdateDate="2023-09-28T00:00:00+00:00",
        lastUpdatedBy="T0000AA",
    )
    mock_version_repo.update_attributes.assert_any_call(
        version.VersionPrimaryKey(
            productId="prod-1111",
            versionId=new_version_id,
            awsAccountId="111111111111",
        ),
        isRecommendedVersion=True,
        lastUpdateDate="2023-09-28T00:00:00+00:00",
        lastUpdatedBy="T0000AA",
    )

    mock_unit_of_work.commit.assert_called_once()


def test_handle_when_version_is_not_in_prod_should_raise(
    command_mock: set_recommended_version_command.SetRecommendedVersionCommand,
    mock_unit_of_work: unit_of_work.UnitOfWork,
    message_bus_mock,
    versions_qs_mock: versions_query_service.VersionsQueryService,
    products_qs_mock: products_query_service.ProductsQueryService,
    new_version_id,
    mock_product_version,
):
    # ARRANGE
    versions_qs_mock.get_product_version_distributions.side_effect = [
        [  # new recommended version
            mock_product_version(
                versionId=new_version_id, is_recommented_version=False, stage=version.VersionStage.DEV
            ),
            mock_product_version(
                versionId=new_version_id,
                is_recommented_version=False,
                aws_account_id="123456789000",
                stage=version.VersionStage.QA,
            ),
        ],
        [],  # old recommended version
    ]

    # ACT
    with pytest.raises(expected_exception=domain_exception.DomainException) as e:
        set_recommended_version_command_handler.handle(
            cmd=command_mock,
            products_query_service=products_qs_mock,
            versions_qry_srv=versions_qs_mock,
            uow=mock_unit_of_work,
            msg_bus=message_bus_mock,
        )

    # ASSERT
    mock_unit_of_work.commit.assert_not_called()
    assertpy.assert_that(str(e)).contains(f"Product version {new_version_id} is not published to PROD stage.")


@pytest.mark.parametrize(
    "status",
    [
        (version.VersionStatus.Failed),
        (version.VersionStatus.Creating),
        (version.VersionStatus.Retiring),
        (version.VersionStatus.Retired),
        (version.VersionStatus.Restoring),
        (version.VersionStatus.Updating),
    ],
)
def test_handle_if_any_prod_version_distribution_is_not_created_should_raise(
    command_mock: set_recommended_version_command.SetRecommendedVersionCommand,
    mock_unit_of_work: unit_of_work.UnitOfWork,
    message_bus_mock,
    versions_qs_mock: versions_query_service.VersionsQueryService,
    products_qs_mock: products_query_service.ProductsQueryService,
    new_version_id,
    mock_product_version,
    status: version.VersionStatus,
):
    # ARRANGE
    versions_qs_mock.get_product_version_distributions.side_effect = [
        [  # new recommended version
            mock_product_version(versionId=new_version_id, is_recommented_version=False, status=status),
            mock_product_version(versionId=new_version_id, is_recommented_version=False, aws_account_id="123456789000"),
        ],
        [],  # old recommended version
    ]

    # ACT
    with pytest.raises(expected_exception=domain_exception.DomainException) as e:
        set_recommended_version_command_handler.handle(
            cmd=command_mock,
            products_query_service=products_qs_mock,
            versions_qry_srv=versions_qs_mock,
            uow=mock_unit_of_work,
            msg_bus=message_bus_mock,
        )

    # ASSERT
    mock_unit_of_work.commit.assert_not_called()
    assertpy.assert_that(str(e)).contains(
        f"Product version {new_version_id} is not fully published to the PROD environment: {status} status exists"
    )


def test_handle_when_success_should_publish_domain_event(
    command_mock: set_recommended_version_command.SetRecommendedVersionCommand,
    mock_unit_of_work: unit_of_work.UnitOfWork,
    message_bus_mock,
    versions_qs_mock: versions_query_service.VersionsQueryService,
    mock_products_repo,
    products_qs_mock: products_query_service.ProductsQueryService,
    new_version_id,
):
    # ARRANGE

    # ACT
    set_recommended_version_command_handler.handle(
        cmd=command_mock,
        products_query_service=products_qs_mock,
        versions_qry_srv=versions_qs_mock,
        uow=mock_unit_of_work,
        msg_bus=message_bus_mock,
    )

    # ASSERT
    message_bus_mock.publish.assert_called_once()
