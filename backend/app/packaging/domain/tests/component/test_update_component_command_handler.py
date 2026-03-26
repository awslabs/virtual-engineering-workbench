import assertpy
import pytest
from freezegun import freeze_time

from app.packaging.domain.command_handlers.component.update_component_command_handler import (
    handle,
)
from app.packaging.domain.commands.component.update_component_command import (
    UpdateComponentCommand,
)
from app.packaging.domain.model.component import component
from app.packaging.domain.value_objects.component import (
    component_description_value_object,
    component_id_value_object,
)
from app.packaging.domain.value_objects.shared import user_id_value_object


@pytest.fixture()
@freeze_time("2023-10-13T00:00:00+00:00")
def update_component_command_mock() -> UpdateComponentCommand:
    return UpdateComponentCommand(
        componentId=component_id_value_object.from_str("comp-11111111"),
        componentDescription=component_description_value_object.from_str("Updated component description"),
        lastUpdatedBy=user_id_value_object.from_str("T998765"),
    )


@pytest.fixture()
def mock_existing_component_object() -> component.Component:
    return component.Component(
        componentId="comp-11111111",
        componentName="Test component",
        componentDescription="Original component description",
        componentPlatform="Linux",
        componentSupportedArchitectures=["amd64"],
        componentSupportedOsVersions=["Ubuntu 24"],
        status=component.ComponentStatus.Created,
        createdBy="T998765",
        createDate="2023-10-12T00:00:00+00:00",
        lastUpdatedBy="T998765",
        lastUpdateDate="2023-10-12T00:00:00+00:00",
    )


@pytest.fixture()
def mock_updated_component_object() -> component.Component:
    return component.Component(
        componentId="comp-11111111",
        componentName="Test component",
        componentDescription="Updated component description",
        componentPlatform="Linux",
        componentSupportedArchitectures=["amd64"],
        componentSupportedOsVersions=["Ubuntu 24"],
        status=component.ComponentStatus.Created,
        createdBy="T998765",
        createDate="2023-10-12T00:00:00+00:00",
        lastUpdatedBy="T998765",
        lastUpdateDate="2023-10-13T00:00:00+00:00",
    )


@freeze_time("2023-10-13T00:00:00+00:00")
def test_update_component_should_update_existing_component(
    update_component_command_mock,
    mock_existing_component_object,
    mock_updated_component_object,
    generic_repo_mock,
    uow_mock,
):
    # ARRANGE
    generic_repo_mock.get.return_value = mock_existing_component_object

    # ACT
    handle(update_component_command_mock, uow=uow_mock)

    # ASSERT
    expected_primary_key = component.ComponentPrimaryKey(componentId=mock_existing_component_object.componentId)
    generic_repo_mock.get.assert_called_once_with(expected_primary_key)

    generic_repo_mock.update_entity.assert_called_once()
    call_args = generic_repo_mock.update_entity.call_args

    assertpy.assert_that(call_args[0][0]).is_equal_to(expected_primary_key)

    updated_entity = call_args[0][1]
    assertpy.assert_that(updated_entity).is_equal_to(mock_updated_component_object)

    uow_mock.commit.assert_called_once()


@freeze_time("2023-10-13T00:00:00+00:00")
def test_update_component_should_raise_error_when_component_not_found(
    update_component_command_mock,
    generic_repo_mock,
    uow_mock,
):
    # ARRANGE
    generic_repo_mock.get.return_value = None

    # ACT & ASSERT
    with pytest.raises(ValueError, match="Component comp-11111111 not found"):
        handle(update_component_command_mock, uow=uow_mock)

    generic_repo_mock.get.assert_called_once()
    generic_repo_mock.update_entity.assert_not_called()
    uow_mock.commit.assert_not_called()
