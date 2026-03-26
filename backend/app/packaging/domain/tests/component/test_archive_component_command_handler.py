from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.packaging.domain.command_handlers.component import archive_component_command_handler
from app.packaging.domain.commands.component import archive_component_command
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component, component_version
from app.packaging.domain.tests.conftest import TEST_COMPONENT_ID, TEST_PROJECT_ID, TEST_USER_ID
from app.packaging.domain.value_objects.component import component_id_value_object
from app.packaging.domain.value_objects.shared import project_id_value_object, user_id_value_object
from app.shared.adapters.unit_of_work_v2 import unit_of_work


@pytest.fixture()
def get_archive_component_command_mock():
    def _get_archive_component_command_mock():
        return archive_component_command.ArchiveComponentCommand(
            projectId=project_id_value_object.from_str(TEST_PROJECT_ID),
            componentId=component_id_value_object.from_str(TEST_COMPONENT_ID),
            lastUpdatedBy=user_id_value_object.from_str(TEST_USER_ID),
        )

    return _get_archive_component_command_mock


def test_handle_should_raise_an_exception_when_component_is_not_found(
    component_query_service_mock, component_version_query_service_mock, get_archive_component_command_mock, uow_mock
):
    # ARRANGE
    archive_component_command_mock = get_archive_component_command_mock()
    component_query_service_mock.get_component.return_value = None

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        archive_component_command_handler.handle(
            command=archive_component_command_mock,
            component_qry_srv=component_query_service_mock,
            component_version_qry_srv=component_version_query_service_mock,
            uow=uow_mock,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        f"Component {archive_component_command_mock.componentId.value} can not be found."
    )


@pytest.mark.parametrize(
    "components_versions_statuses",
    (
        [
            component_version.ComponentVersionStatus.Created,
        ],
        [
            component_version.ComponentVersionStatus.Created,
            component_version.ComponentVersionStatus.Retired,
        ],
        [
            component_version.ComponentVersionStatus.Creating,
        ],
        [
            component_version.ComponentVersionStatus.Failed,
        ],
        [
            component_version.ComponentVersionStatus.Released,
        ],
        [
            component_version.ComponentVersionStatus.Retired,
            component_version.ComponentVersionStatus.Created,
        ],
        [
            component_version.ComponentVersionStatus.Testing,
        ],
        [
            component_version.ComponentVersionStatus.Updating,
        ],
        [
            component_version.ComponentVersionStatus.Validated,
        ],
    ),
)
@freeze_time("2023-10-12")
def test_handle_should_raise_an_exception_when_a_component_version_status_is_invalid(
    component_query_service_mock,
    component_version_query_service_mock,
    components_versions_statuses,
    get_archive_component_command_mock,
    get_test_component,
    get_test_component_version_with_specific_status,
    uow_mock,
):
    # ARRANGE
    archive_component_command_mock = get_archive_component_command_mock()
    component_query_service_mock.get_component.return_value = get_test_component
    components_versions_entities = [
        get_test_component_version_with_specific_status(status=status) for status in components_versions_statuses
    ]
    component_version_query_service_mock.get_component_versions.return_value = components_versions_entities
    component_version_invalid_status_entity = [
        component_version_entity
        for component_version_entity in components_versions_entities
        if component_version_entity.status is not component_version.ComponentVersionStatus.Retired
    ][0]

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        archive_component_command_handler.handle(
            command=archive_component_command_mock,
            component_qry_srv=component_query_service_mock,
            component_version_qry_srv=component_version_query_service_mock,
            uow=uow_mock,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        f"Component {archive_component_command_mock.componentId.value} cannot be retired because component version "
        f"{component_version_invalid_status_entity.componentVersionId} is in {component_version_invalid_status_entity.status} status."
    )


@pytest.mark.parametrize(
    "components_versions_statuses",
    (
        [],
        [
            component_version.ComponentVersionStatus.Retired,
        ],
        [
            component_version.ComponentVersionStatus.Retired,
            component_version.ComponentVersionStatus.Retired,
        ],
    ),
)
@freeze_time("2023-10-12")
def test_handle_should_archive_component(
    component_query_service_mock,
    component_version_query_service_mock,
    components_versions_statuses,
    get_archive_component_command_mock,
    get_test_component,
    get_test_component_version_with_specific_status,
):
    # ARRANGE
    archive_component_command_mock = get_archive_component_command_mock()
    component_query_service_mock.get_component.return_value = get_test_component
    component_repository_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    component_version_query_service_mock.get_component_versions.return_value = [
        get_test_component_version_with_specific_status(status=status) for status in components_versions_statuses
    ]
    repositories_dictionary = {component.Component: component_repository_mock}
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)

    uow_mock.get_repository.side_effect = lambda pk, x: repositories_dictionary.get(x)

    # ACT
    archive_component_command_handler.handle(
        command=archive_component_command_mock,
        component_qry_srv=component_query_service_mock,
        component_version_qry_srv=component_version_query_service_mock,
        uow=uow_mock,
    )

    # ASSERT
    component_repository_mock.update_attributes.assert_called_once_with(
        component.ComponentPrimaryKey(
            componentId=archive_component_command_mock.componentId.value,
        ),
        lastUpdateBy=archive_component_command_mock.lastUpdatedBy.value,
        lastUpdateDate="2023-10-12T00:00:00+00:00",
        status=component.ComponentStatus.Archived,
    )
    uow_mock.commit.assert_called()
