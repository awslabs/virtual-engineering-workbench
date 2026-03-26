import logging
from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.packaging.domain.command_handlers.component import update_component_version_associations_command_handler
from app.packaging.domain.commands.component import update_component_version_associations_command
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component_version
from app.packaging.domain.model.shared.component_version_entry import ComponentVersionEntry
from app.packaging.domain.value_objects.component import component_id_value_object
from app.packaging.domain.value_objects.component_version import (
    component_version_id_value_object,
    components_versions_list_value_object,
)
from app.shared.adapters.unit_of_work_v2 import unit_of_work


@pytest.fixture()
def update_component_version_associations_command_mock():
    def _update_component_version_associations_command_mock(
        previous_components_version_dependencies: list[ComponentVersionEntry] | None = None,
    ):
        return update_component_version_associations_command.UpdateComponentVersionAssociationsCommand(
            componentId=component_id_value_object.from_str("comp-1234abcd"),
            componentVersionId=component_version_id_value_object.from_str("vers-1234abcd"),
            componentsVersionDependencies=components_versions_list_value_object.from_list(
                [
                    ComponentVersionEntry(
                        componentId="comp-5678abcd",
                        componentName="component-5678abcd",
                        componentVersionId="vers-5678abcd",
                        componentVersionName="1.0.0",
                    ),
                ]
            ),
            previousComponentsVersionDependencies=previous_components_version_dependencies,
        )

    return _update_component_version_associations_command_mock


def test_get_component_version_should_return_component_version(
    component_version_query_service_mock,
    get_test_component_version,
    get_test_component_id,
    get_test_component_version_id,
):
    # ARRANGE
    component_version_query_service_mock.get_component_version.return_value = get_test_component_version

    # ACT
    component_version_entity = update_component_version_associations_command_handler.__get_component_version(
        component_version_qry_srv=component_version_query_service_mock,
        component_id=get_test_component_id,
        component_version_id=get_test_component_version_id,
        logger=mock.create_autospec(spec=logging.Logger),
    )

    # ASSERT
    assertpy.assert_that(component_version_entity).is_equal_to(get_test_component_version)


def test_get_component_version_should_raise_if_component_version_not_found(
    component_version_query_service_mock,
    get_test_component_id,
    get_test_component_version_id,
):
    # ARRANGE
    component_version_query_service_mock.get_component_version.return_value = None

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        update_component_version_associations_command_handler.__get_component_version(
            component_version_qry_srv=component_version_query_service_mock,
            component_id=get_test_component_id,
            component_version_id=get_test_component_version_id,
            logger=mock.create_autospec(spec=logging.Logger),
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        f"Version {get_test_component_version_id} for {get_test_component_id} can not be found."
    )


@pytest.mark.parametrize(
    "status",
    (
        (component_version.ComponentVersionStatus.Created.value),
        (component_version.ComponentVersionStatus.Released.value),
        (component_version.ComponentVersionStatus.Retired.value),
        (component_version.ComponentVersionStatus.Validated.value),
    ),
)
def test_validate_component_version_status_should_succeed_if_valid_status(
    get_test_component_version,
    status,
):
    # ARRANGE
    component_version_entity = get_test_component_version
    component_version_entity.status = status

    # ACT
    validation_result = update_component_version_associations_command_handler.__validate_component_version_status(
        component_version_entity=component_version_entity,
        logger=mock.create_autospec(spec=logging.Logger),
    )

    # ASSERT
    assertpy.assert_that(validation_result).is_equal_to(True)


@pytest.mark.parametrize(
    "status",
    (
        (component_version.ComponentVersionStatus.Creating.value),
        (component_version.ComponentVersionStatus.Failed.value),
        (component_version.ComponentVersionStatus.Testing.value),
        (component_version.ComponentVersionStatus.Updating.value),
    ),
)
def test_validate_component_version_status_should_raise_if_invalid_status(
    get_test_component_version,
    status,
):
    # ARRANGE
    component_version_entity = get_test_component_version
    component_version_entity.status = status

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        update_component_version_associations_command_handler.__validate_component_version_status(
            component_version_entity=component_version_entity,
            logger=mock.create_autospec(spec=logging.Logger),
        )

    # ASSERT
    exception_message = (
        f"Version {component_version_entity.componentVersionName} of "
        f"component {component_version_entity.componentId} "
        f"can't be (dis-)associated while in {component_version_entity.status} status: "
        f"only {component_version.ComponentVersionStatus.Created}, "
        f"{component_version.ComponentVersionStatus.Released}, "
        f"{component_version.ComponentVersionStatus.Retired}, and "
        f"{component_version.ComponentVersionStatus.Validated} states are accepted."
    )
    assertpy.assert_that(str(e.value)).is_equal_to(exception_message)


@freeze_time("2024-02-07")
def test_handle_should_update_associations(
    update_component_version_associations_command_mock,
    component_version_query_service_mock,
    get_test_component_version_with_specific_component_id_version_name_and_status,
):
    # ARRANGE
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {component_version.ComponentVersion: component_version_repo_mock}
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda _, x: repos_dict.get(x)
    current_component_version_entity = get_test_component_version_with_specific_component_id_version_name_and_status(
        component_id="comp-1234abcd",
        component_version_id="vers-1234abcd",
        version_name="1.0.0",
        status=component_version.ComponentVersionStatus.Created,
    )
    target_component_version_entity = get_test_component_version_with_specific_component_id_version_name_and_status(
        component_id="comp-5678abcd",
        component_version_id="vers-5678abcd",
        version_name="1.0.0",
        status=component_version.ComponentVersionStatus.Created,
    )
    component_version_query_service_mock.get_component_version.side_effect = [
        current_component_version_entity,
        target_component_version_entity,
    ]

    # ACT
    update_component_version_associations_command_handler.handle(
        command=update_component_version_associations_command_mock(),
        component_version_qry_srv=component_version_query_service_mock,
        logger=mock.create_autospec(spec=logging.Logger),
        uow=uow_mock,
    )

    # ASSERT
    component_version_repo_mock.update_entity.assert_called_once_with(
        component_version.ComponentVersionPrimaryKey(
            componentId=target_component_version_entity.componentId,
            componentVersionId=target_component_version_entity.componentVersionId,
        ),
        target_component_version_entity,
    )
    uow_mock.commit.assert_called()


@freeze_time("2024-02-07")
def test_handle_should_remove_old_associations_for_same_component_version(
    update_component_version_associations_command_mock,
    component_version_query_service_mock,
    get_test_component_version_with_specific_component_id_version_name_and_status,
):
    # ARRANGE
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {component_version.ComponentVersion: component_version_repo_mock}
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda _, x: repos_dict.get(x)
    current_component_version_entity = get_test_component_version_with_specific_component_id_version_name_and_status(
        component_id="comp-1234abcd",
        component_version_id="vers-1234abcd",
        version_name="1.0.0-rc.2",
        status=component_version.ComponentVersionStatus.Created,
    )
    target_component_version_entity = get_test_component_version_with_specific_component_id_version_name_and_status(
        component_id="comp-5678abcd",
        component_version_id="vers-5678abcd",
        version_name="1.0.0",
        status=component_version.ComponentVersionStatus.Created,
    )
    # The target component version already has an old version of the current component as association
    target_component_version_entity.associatedComponentsVersions = [
        ComponentVersionEntry(
            componentId=current_component_version_entity.componentId,
            componentName=current_component_version_entity.componentName,
            componentVersionId=current_component_version_entity.componentVersionId,
            componentVersionName="1.0.0-rc.1",
        ),
    ]
    component_version_query_service_mock.get_component_version.side_effect = [
        current_component_version_entity,
        target_component_version_entity,
    ]

    # ACT
    update_component_version_associations_command_handler.handle(
        command=update_component_version_associations_command_mock(),
        component_version_qry_srv=component_version_query_service_mock,
        logger=mock.create_autospec(spec=logging.Logger),
        uow=uow_mock,
    )

    # ASSERT
    component_version_repo_mock.update_entity.assert_called_once_with(
        component_version.ComponentVersionPrimaryKey(
            componentId=target_component_version_entity.componentId,
            componentVersionId=target_component_version_entity.componentVersionId,
        ),
        target_component_version_entity,
    )
    uow_mock.commit.assert_called()


@freeze_time("2024-02-07")
def test_handle_should_remove_old_associations_for_previous_component_version(
    update_component_version_associations_command_mock,
    component_version_query_service_mock,
    get_test_component_version_with_specific_component_id_version_name_and_status,
):
    # ARRANGE
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {component_version.ComponentVersion: component_version_repo_mock}
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda _, x: repos_dict.get(x)
    current_component_version_entity = get_test_component_version_with_specific_component_id_version_name_and_status(
        component_id="comp-1234abcd",
        component_version_id="vers-1234abcd",
        version_name="1.0.0-rc.2",
        status=component_version.ComponentVersionStatus.Created,
    )
    target_component_version_entity = get_test_component_version_with_specific_component_id_version_name_and_status(
        component_id="comp-5678abcd",
        component_version_id="vers-5678abcd",
        version_name="1.0.0",
        status=component_version.ComponentVersionStatus.Created,
    )
    target_previous_component_version_entity = (
        get_test_component_version_with_specific_component_id_version_name_and_status(
            component_id="comp-9012abcd",
            component_version_id="vers-9012abcd",
            version_name="1.0.0",
            status=component_version.ComponentVersionStatus.Created,
        )
    )
    # The target component version already has an old version of the current component as association
    target_component_version_entity.associatedComponentsVersions = [
        ComponentVersionEntry(
            componentId=current_component_version_entity.componentId,
            componentName=current_component_version_entity.componentName,
            componentVersionId=current_component_version_entity.componentVersionId,
            componentVersionName="1.0.0-rc.1",
        ),
    ]
    component_version_query_service_mock.get_component_version.side_effect = [
        current_component_version_entity,
        target_previous_component_version_entity,
        target_component_version_entity,
    ]

    # ACT
    update_component_version_associations_command_handler.handle(
        command=update_component_version_associations_command_mock(
            previous_components_version_dependencies=components_versions_list_value_object.from_list(
                [
                    ComponentVersionEntry(
                        componentId="comp-9012abcd",
                        componentName="component-9012abcd",
                        componentVersionId="vers-9012abcd",
                        componentVersionName="1.0.0",
                    ),
                ]
            )
        ),
        component_version_qry_srv=component_version_query_service_mock,
        logger=mock.create_autospec(spec=logging.Logger),
        uow=uow_mock,
    )

    # ASSERT
    component_version_repo_mock.update_entity.assert_any_call(
        component_version.ComponentVersionPrimaryKey(
            componentId=target_component_version_entity.componentId,
            componentVersionId=target_component_version_entity.componentVersionId,
        ),
        target_component_version_entity,
    )
    component_version_repo_mock.update_entity.assert_any_call(
        component_version.ComponentVersionPrimaryKey(
            componentId=target_previous_component_version_entity.componentId,
            componentVersionId=target_previous_component_version_entity.componentVersionId,
        ),
        target_previous_component_version_entity,
    )
    uow_mock.commit.assert_called()
