from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.publishing.domain.command_handlers import archive_product_command_handler
from app.publishing.domain.commands import archive_product_command
from app.publishing.domain.events import product_archiving_started
from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.model import product
from app.publishing.domain.value_objects import product_id_value_object, project_id_value_object, user_id_value_object
from app.shared.adapters.message_bus import message_bus


@pytest.fixture()
def message_bus_mock():
    mess_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    return mess_bus_mock


@pytest.fixture()
def archive_product_command_mock():
    archive_product_command_mock = archive_product_command.ArchiveProductCommand(
        projectId=project_id_value_object.from_str("proj-12345"),
        productId=product_id_value_object.from_str("prod-12345abc"),
        archivedBy=user_id_value_object.from_str("T0037SG"),
    )
    return archive_product_command_mock


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


@freeze_time("2023-07-24")
def test_archive_product_archives_product(
    archive_product_command_mock, mock_unit_of_work, message_bus_mock, mock_products_repo, get_product
):
    # ARRANGE
    mock_products_repo.get.return_value = get_product()
    # ACT
    archive_product_command_handler.handle(
        cmd=archive_product_command_mock,
        uow=mock_unit_of_work,
        message_bus=message_bus_mock,
    )
    # ASSERT
    mock_products_repo.update_attributes.assert_called_with(
        pk=product.ProductPrimaryKey(
            projectId=archive_product_command_mock.projectId.value,
            productId=archive_product_command_mock.productId.value,
        ),
        status=product.ProductStatus.Archiving,
        lastUpdateDate="2023-07-24T00:00:00+00:00",
        lastUpdatedBy=archive_product_command_mock.archivedBy.value,
    )
    mock_unit_of_work.commit.assert_called()
    message_bus_mock.publish.assert_any_call(
        product_archiving_started.ProductArchivingStarted(projectId="proj-12345", product_id="prod-12345abc")
    )


def test_archive_product_handler_raise_error_if_product_has_invalid_status(
    archive_product_command_mock, mock_unit_of_work, message_bus_mock, mock_products_repo
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
        archive_product_command_handler.handle(
            cmd=archive_product_command_mock,
            uow=mock_unit_of_work,
            message_bus=message_bus_mock,
        )
        assertpy.assert_that(str(error.value)).is_equal_to("Only products with status 'Created' can be archived")
