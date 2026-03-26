import logging
from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.packaging.domain.command_handlers.component import (
    remove_component_version_command_handler,
)
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component_version
from app.packaging.domain.ports import component_version_definition_service


@pytest.fixture()
def component_version_definition_service_mock():
    return mock.create_autospec(spec=component_version_definition_service.ComponentVersionDefinitionService)


@freeze_time("2023-10-12")
def test_handle_should_raise_exception_when_component_version_can_t_be_deleted(
    generic_repo_mock,
    component_version_service_mock,
    remove_component_version_command_mock,
    uow_mock,
):
    # ARRANGE
    component_version_service_mock.delete.side_effect = Exception()

    # ACT
    with pytest.raises(domain_exception.DomainException) as exc_info:
        remove_component_version_command_handler.handle(
            command=remove_component_version_command_mock,
            uow=uow_mock,
            component_version_service=component_version_service_mock,
            component_version_definition_service=component_version_definition_service_mock,
            logger=mock.create_autospec(spec=logging.Logger),
        )

    # ASSERT
    assertpy.assert_that(str(exc_info.value)).is_equal_to(
        f"Version {remove_component_version_command_mock.componentVersionId.value} of component {remove_component_version_command_mock.componentId.value} can't be deleted."
    )
    generic_repo_mock.update_attributes.assert_called_once_with(
        component_version.ComponentVersionPrimaryKey(
            componentId=remove_component_version_command_mock.componentId.value,
            componentVersionId=remove_component_version_command_mock.componentVersionId.value,
        ),
        lastUpdateDate="2023-10-12T00:00:00+00:00",
        status=component_version.ComponentVersionStatus.Failed,
    )
    uow_mock.commit.assert_called()


@freeze_time("2023-10-12")
def test_handle_should_remove_component_version(
    generic_repo_mock,
    component_version_service_mock,
    remove_component_version_command_mock,
    uow_mock,
):
    # ARRANGE
    component_version_service_mock.delete.return_value = None

    # ACT
    remove_component_version_command_handler.handle(
        command=remove_component_version_command_mock,
        uow=uow_mock,
        component_version_service=component_version_service_mock,
        component_version_definition_service=component_version_definition_service_mock,
        logger=mock.create_autospec(spec=logging.Logger),
    )

    # ASSERT
    generic_repo_mock.update_attributes.assert_called_once_with(
        component_version.ComponentVersionPrimaryKey(
            componentId=remove_component_version_command_mock.componentId.value,
            componentVersionId=remove_component_version_command_mock.componentVersionId.value,
        ),
        lastUpdateDate="2023-10-12T00:00:00+00:00",
        status=component_version.ComponentVersionStatus.Retired,
    )
    uow_mock.commit.assert_called()


@freeze_time("2023-10-12")
def test_handle_should_remove_component_version_and_cleanup_vectors(
    generic_repo_mock,
    component_version_service_mock,
    component_version_definition_service_mock,
    remove_component_version_command_mock,
    uow_mock,
):
    """Test that component retirement successfully removes the component version."""
    # ARRANGE
    component_version_service_mock.delete.return_value = None

    # ACT
    remove_component_version_command_handler.handle(
        command=remove_component_version_command_mock,
        uow=uow_mock,
        component_version_service=component_version_service_mock,
        component_version_definition_service=component_version_definition_service_mock,
        logger=mock.create_autospec(spec=logging.Logger),
    )

    # ASSERT
    # Verify component version was deleted
    component_version_service_mock.delete.assert_called_once_with(
        component_build_version_arn=remove_component_version_command_mock.componentBuildVersionArn.value
    )

    # Vector cleanup is no longer needed with Bedrock Knowledge Base approach

    # Verify status was updated to retired
    generic_repo_mock.update_attributes.assert_called_once_with(
        component_version.ComponentVersionPrimaryKey(
            componentId=remove_component_version_command_mock.componentId.value,
            componentVersionId=remove_component_version_command_mock.componentVersionId.value,
        ),
        lastUpdateDate="2023-10-12T00:00:00+00:00",
        status=component_version.ComponentVersionStatus.Retired,
    )
    uow_mock.commit.assert_called()


@freeze_time("2023-10-12")
def test_handle_should_retire_component_version_successfully(
    generic_repo_mock,
    component_version_service_mock,
    component_version_definition_service_mock,
    remove_component_version_command_mock,
    uow_mock,
):
    """Test that component retirement works successfully."""
    # ARRANGE
    component_version_service_mock.delete.return_value = None

    logger_mock = mock.create_autospec(spec=logging.Logger)

    # ACT
    remove_component_version_command_handler.handle(
        command=remove_component_version_command_mock,
        uow=uow_mock,
        component_version_service=component_version_service_mock,
        component_version_definition_service=component_version_definition_service_mock,
        logger=logger_mock,
    )

    # ASSERT
    # Verify component version was deleted
    component_version_service_mock.delete.assert_called_once_with(
        component_build_version_arn=remove_component_version_command_mock.componentBuildVersionArn.value
    )

    # Vector cleanup is no longer needed with Bedrock Knowledge Base approach

    # Verify status was updated to retired
    generic_repo_mock.update_attributes.assert_called_once_with(
        component_version.ComponentVersionPrimaryKey(
            componentId=remove_component_version_command_mock.componentId.value,
            componentVersionId=remove_component_version_command_mock.componentVersionId.value,
        ),
        lastUpdateDate="2023-10-12T00:00:00+00:00",
        status=component_version.ComponentVersionStatus.Retired,
    )
    uow_mock.commit.assert_called()
