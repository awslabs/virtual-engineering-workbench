from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.publishing.domain.command_handlers import create_product_command_handler
from app.publishing.domain.commands import create_product_command
from app.publishing.domain.events import product_created
from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.model import product
from app.publishing.domain.value_objects import (
    product_description_value_object,
    product_id_value_object,
    product_name_value_object,
    product_type_value_object,
    project_id_value_object,
    tech_id_value_object,
    tech_name_value_object,
    user_id_value_object,
)
from app.shared.adapters.message_bus import message_bus


@mock.patch("app.publishing.domain.value_objects.product_id_value_object.random.choice", lambda chars: "1")
@freeze_time("2023-06-20")
@pytest.mark.parametrize(
    "product_type_cmd_value, product_type",
    [("Workbench", product.ProductType.Workbench), ("Virtual_Target", product.ProductType.VirtualTarget)],
)
def test_handle_should_store_entity_and_publish_event(
    mock_products_repo, product_type_cmd_value, product_type, mock_unit_of_work
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)

    command = create_product_command.CreateProductCommand(
        projectId=project_id_value_object.from_str("proj-123"),
        productId=product_id_value_object.from_str("prod-11111111"),
        productName=product_name_value_object.from_str("My Product"),
        productType=product_type_value_object.from_str(product_type_cmd_value),
        productDescription=product_description_value_object.from_str("My Description"),
        technologyId=tech_id_value_object.from_str("tech-123"),
        technologyName=tech_name_value_object.from_str("Test technology"),
        userId=user_id_value_object.from_str("T0011AA"),
    )
    # ACT
    create_product_command_handler.handle(command=command, unit_of_work=mock_unit_of_work, message_bus=message_bus_mock)

    # ASSERT
    mock_products_repo.add.assert_called_once_with(
        product.Product(
            projectId="proj-123",
            productId="prod-11111111",
            technologyId="tech-123",
            technologyName="Test technology",
            status="CREATED",
            productName="My Product",
            productType=product_type,
            productDescription="My Description",
            recommendedVersionId=None,
            createDate="2023-06-20T00:00:00+00:00",
            lastUpdateDate="2023-06-20T00:00:00+00:00",
            createdBy="T0011AA",
            lastUpdatedBy="T0011AA",
        )
    )
    mock_unit_of_work.commit.assert_called_once()

    message_bus_mock.publish.assert_called_once_with(
        product_created.ProductCreated(
            event_name="ProductCreated",
            project_id="proj-123",
            product_name="My Product",
            product_description="My Description",
            technology_id="tech-123",
            user_id="T0011AA",
            product_id="prod-11111111",
            product_type=product_type,
        )
    )


@freeze_time("2023-06-20")
def test_handle_should_raise_exception_when_product_name_exceeds_50_characters():
    # ARRANGE & ACT & ASSERT
    with pytest.raises(domain_exception.DomainException) as e:
        create_product_command.CreateProductCommand(
            projectId=project_id_value_object.from_str("proj-123"),
            productId=product_id_value_object.from_str("prod-11111111"),
            productName=product_name_value_object.from_str(
                "A very long product name that will exceed the specified limit set in the command handler"
            ),
            productType=product_type_value_object.from_str("Workbench"),
            productDescription=product_description_value_object.from_str("My Description"),
            technologyId=tech_id_value_object.from_str("tech-123"),
            technologyName=tech_name_value_object.from_str("Test technology"),
            userId=user_id_value_object.from_str("T0011AA"),
        )
    assertpy.assert_that(str(e.value)).is_equal_to(
        "Product name should be between 1 and 50 characters in alphanumeric, space( ), underscore(_) and hyphen(-)"
    )


@freeze_time("2023-06-20")
def test_handle_should_raise_exception_when_product_description_exceeds_100_characters():
    # ARRANGE & ACT & ASSERT
    with pytest.raises(domain_exception.DomainException) as e:
        create_product_command.CreateProductCommand(
            projectId=project_id_value_object.from_str("proj-123"),
            productId=product_id_value_object.from_str("prod-11111111"),
            productName=product_name_value_object.from_str("My product"),
            productType=product_type_value_object.from_str("Workbench"),
            productDescription=product_description_value_object.from_str(
                "A very long product description that will exceed the specified limit set in the command handler and thus should cause an exception to be thrown"
            ),
            technologyId=tech_id_value_object.from_str("tech-123"),
            technologyName=tech_name_value_object.from_str("Test technology"),
            userId=user_id_value_object.from_str("T0011AA"),
        )
    assertpy.assert_that(str(e.value)).is_equal_to(
        "Product description should be between 0 and 100 characters in alphanumeric, space( ), underscore(_) and hyphen(-)"
    )
