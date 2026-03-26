from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.packaging.domain.command_handlers.component import (
    update_mandatory_components_list_command_handler,
)
from app.packaging.domain.commands.component import (
    update_mandatory_components_list_command,
)
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.exceptions.domain_exception import DomainException
from app.packaging.domain.model.component import (
    component_version,
    mandatory_components_list,
)
from app.packaging.domain.model.shared import component_version_entry
from app.packaging.domain.ports import (
    mandatory_components_list_query_service,
)
from app.packaging.domain.value_objects.component import (
    component_platform_value_object,
    component_supported_architecture_value_object,
    component_supported_os_version_value_object,
)
from app.packaging.domain.value_objects.shared import user_id_value_object
from app.shared.adapters.unit_of_work_v2 import unit_of_work


@pytest.fixture()
def get_update_mandatory_components_list_command_mock():
    def _get_update_mandatory_components_list_command_mock(
        prepended_components_versions: list[component_version_entry.ComponentVersionEntry] = [],
        appended_components_versions: list[component_version_entry.ComponentVersionEntry] = [
            component_version_entry.ComponentVersionEntry(
                componentId="comp-1234abc",
                componentName="component-1234abc",
                componentVersionId="vers-1234abc",
                componentVersionName="3.0.0",
                order=3,
            ),
            component_version_entry.ComponentVersionEntry(
                componentId="comp-1234fghi",
                componentName="component-1234fghi",
                componentVersionId="vers-123fghi",
                componentVersionName="1.0.0",
                order=1,
            ),
            component_version_entry.ComponentVersionEntry(
                componentId="comp-1234def",
                componentName="component-1234def",
                componentVersionId="vers-1234def",
                componentVersionName="2.0.0",
                order=2,
            ),
        ],
    ):
        from app.packaging.domain.value_objects.component_version import (
            components_versions_list_value_object,
        )

        return update_mandatory_components_list_command.UpdateMandatoryComponentsListCommand(
            mandatoryComponentsListPlatform=component_platform_value_object.from_str("Linux"),
            mandatoryComponentsListArchitecture=component_supported_architecture_value_object.from_str("amd64"),
            mandatoryComponentsListOsVersion=component_supported_os_version_value_object.from_str("Ubuntu 24"),
            prependedComponentsVersions=components_versions_list_value_object.from_list(prepended_components_versions),
            appendedComponentsVersions=components_versions_list_value_object.from_list(appended_components_versions),
            lastUpdatedBy=user_id_value_object.from_str("T123456"),
        )

    return _get_update_mandatory_components_list_command_mock


@freeze_time("2024-01-18")
def test_handle_should_update_mandatory_component_versions_list(
    component_version_query_service_mock,
    get_test_component_version_with_specific_status,
    get_update_mandatory_components_list_command_mock,
    mandatory_components_list_query_service_mock,
):
    # ARRANGE
    mandatory_components_list_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {mandatory_components_list.MandatoryComponentsList: mandatory_components_list_repo_mock}
    mandatory_components_list_query_service_mock.get_mandatory_components_list.return_value = {}
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)
    update_mandatory_components_list_command_mock = get_update_mandatory_components_list_command_mock()
    component_version_entities = list()
    # Combine prepended and appended components
    all_components = (
        update_mandatory_components_list_command_mock.prependedComponentsVersions.value
        + update_mandatory_components_list_command_mock.appendedComponentsVersions.value
    )
    for recipe_component_version in all_components:
        component_version_entity = get_test_component_version_with_specific_status(
            status=component_version.ComponentVersionStatus.Released
        )
        component_version_entity.componentId = recipe_component_version.componentId
        component_version_entity.componentVersionId = recipe_component_version.componentVersionId

        component_version_entities.append(component_version_entity)

    component_version_query_service_mock.get_component_version.side_effect = component_version_entities

    # ACT
    update_mandatory_components_list_command_handler.handle(
        command=update_mandatory_components_list_command_mock,
        component_version_qry_srv=component_version_query_service_mock,
        mandatory_components_list_qry_srv=mandatory_components_list_query_service_mock,
        uow=uow_mock,
    )

    # ASSERT
    call_args = mandatory_components_list_repo_mock.update_attributes.call_args
    assertpy.assert_that(call_args[0][0]).is_equal_to(
        mandatory_components_list.MandatoryComponentsListPrimaryKey(
            mandatoryComponentsListPlatform=update_mandatory_components_list_command_mock.mandatoryComponentsListPlatform.value,
            mandatoryComponentsListOsVersion=update_mandatory_components_list_command_mock.mandatoryComponentsListOsVersion.value,
            mandatoryComponentsListArchitecture=update_mandatory_components_list_command_mock.mandatoryComponentsListArchitecture.value,
        )
    )
    assertpy.assert_that(call_args[1]["mandatoryComponentsVersions"]).is_length(len(all_components))
    assertpy.assert_that(call_args[1]["lastUpdateDate"]).is_equal_to("2024-01-18T00:00:00+00:00")
    assertpy.assert_that(call_args[1]["lastUpdatedBy"]).is_equal_to(
        update_mandatory_components_list_command_mock.lastUpdatedBy.value
    )
    uow_mock.commit.assert_called()


def test_handle_should_raise_an_exception_if_mandatory_components_versions_don_t_exist(
    component_version_query_service_mock,
    get_update_mandatory_components_list_command_mock,
    mandatory_components_list_query_service_mock,
):
    # ARRANGE
    mandatory_components_list_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {mandatory_components_list.MandatoryComponentsList: mandatory_components_list_repo_mock}
    mandatory_components_list_query_service_mock.get_mandatory_components_list.return_value = {}
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)
    update_mandatory_components_list_command_mock = get_update_mandatory_components_list_command_mock()
    # Combine prepended and appended components
    all_components = (
        update_mandatory_components_list_command_mock.prependedComponentsVersions.value
        + update_mandatory_components_list_command_mock.appendedComponentsVersions.value
    )
    component_version_query_service_mock.get_component_version.side_effect = [None for _ in range(len(all_components))]
    first_recipe_component_version = all_components[0]

    # ACT
    with pytest.raises(DomainException) as exc_info:
        update_mandatory_components_list_command_handler.handle(
            command=update_mandatory_components_list_command_mock,
            component_version_qry_srv=component_version_query_service_mock,
            mandatory_components_list_qry_srv=mandatory_components_list_query_service_mock,
            uow=uow_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exc_info.value)).is_equal_to(
        f"Version {first_recipe_component_version.componentVersionId} of component "
        f"{first_recipe_component_version.componentId} does not exist."
    )


@pytest.mark.parametrize(
    "status",
    (
        component_version.ComponentVersionStatus.Created,
        component_version.ComponentVersionStatus.Creating,
        component_version.ComponentVersionStatus.Failed,
        component_version.ComponentVersionStatus.Retired,
        component_version.ComponentVersionStatus.Testing,
        component_version.ComponentVersionStatus.Updating,
        component_version.ComponentVersionStatus.Validated,
    ),
)
def test_handle_should_raise_an_exception_if_mandatory_components_versions_are_not_released(
    component_version_query_service_mock,
    get_test_component_version_with_specific_status,
    get_update_mandatory_components_list_command_mock,
    mandatory_components_list_query_service_mock,
    status,
):
    # ARRANGE
    mandatory_components_list_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {mandatory_components_list.MandatoryComponentsList: mandatory_components_list_repo_mock}
    mandatory_components_list_query_service_mock.get_mandatory_components_list.return_value = {}
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)
    update_mandatory_components_list_command_mock = get_update_mandatory_components_list_command_mock()
    component_version_entities = list()
    # Combine prepended and appended components
    all_components = (
        update_mandatory_components_list_command_mock.prependedComponentsVersions.value
        + update_mandatory_components_list_command_mock.appendedComponentsVersions.value
    )
    for recipe_component_version in all_components:
        component_version_entity = get_test_component_version_with_specific_status(status=status)
        component_version_entity.componentId = recipe_component_version.componentId
        component_version_entity.componentVersionId = recipe_component_version.componentVersionId

        component_version_entities.append(component_version_entity)

    component_version_query_service_mock.get_component_version.side_effect = component_version_entities
    first_recipe_component_version = all_components[0]

    # ACT
    with pytest.raises(DomainException) as exc_info:
        update_mandatory_components_list_command_handler.handle(
            command=update_mandatory_components_list_command_mock,
            component_version_qry_srv=component_version_query_service_mock,
            mandatory_components_list_qry_srv=mandatory_components_list_query_service_mock,
            uow=uow_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exc_info.value)).is_equal_to(
        f"Version {first_recipe_component_version.componentVersionId} of component "
        f"{first_recipe_component_version.componentId} has not been released."
    )


@pytest.mark.parametrize(
    "prepended_components,appended_components,expected_exception_message",
    (
        (
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234abc",
                    componentVersionName="1.0.0",
                    order=1,
                ),
            ],
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234def",
                    componentVersionName="2.0.0",
                    order=1,
                ),
            ],
            "Components cannot be both prepended and appended: ['comp-1234abc'].",
        ),
        (
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234abc",
                    componentVersionName="1.0.0",
                    order=1,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234def",
                    componentName="component-1234def",
                    componentVersionId="vers-1234ghi",
                    componentVersionName="3.0.0",
                    order=2,
                ),
            ],
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234def",
                    componentVersionName="2.0.0",
                    order=1,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234def",
                    componentName="component-1234def",
                    componentVersionId="vers-1234jkl",
                    componentVersionName="4.0.0",
                    order=2,
                ),
            ],
            "Components cannot be both prepended and appended: ['comp-1234abc', 'comp-1234def'].",
        ),
    ),
)
def test_handle_should_raise_an_exception_with_duplicate_components(
    component_version_query_service_mock,
    expected_exception_message,
    get_update_mandatory_components_list_command_mock,
    mandatory_components_list_query_service_mock,
    prepended_components,
    appended_components,
):
    mandatory_components_list_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {mandatory_components_list.MandatoryComponentsList: mandatory_components_list_repo_mock}
    mandatory_components_list_query_service_mock.get_mandatory_components_list.return_value = {}
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)
    update_mandatory_components_list_command_mock = get_update_mandatory_components_list_command_mock(
        prepended_components_versions=prepended_components,
        appended_components_versions=appended_components,
    )

    # ACT
    with pytest.raises(DomainException) as e:
        update_mandatory_components_list_command_handler.handle(
            command=update_mandatory_components_list_command_mock,
            component_version_qry_srv=component_version_query_service_mock,
            mandatory_components_list_qry_srv=mandatory_components_list_query_service_mock,
            uow=uow_mock,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(expected_exception_message)


def test_handle_should_raise_if_no_mandatory_components_list_found(
    component_version_query_service_mock,
    get_test_component_version_with_specific_status,
    get_update_mandatory_components_list_command_mock,
    mandatory_components_list_query_service_mock,
):
    # ARRANGE
    mandatory_components_list_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {mandatory_components_list.MandatoryComponentsList: mandatory_components_list_repo_mock}
    mandatory_components_list_query_service_mock.get_mandatory_components_list.return_value = None
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)
    update_mandatory_components_list_command_mock = get_update_mandatory_components_list_command_mock()
    component_version_entities = list()
    # Combine prepended and appended components
    all_components = (
        update_mandatory_components_list_command_mock.prependedComponentsVersions.value
        + update_mandatory_components_list_command_mock.appendedComponentsVersions.value
    )
    for recipe_component_version in all_components:
        component_version_entity = get_test_component_version_with_specific_status(
            status=component_version.ComponentVersionStatus.Released
        )
        component_version_entity.componentId = recipe_component_version.componentId
        component_version_entity.componentVersionId = recipe_component_version.componentVersionId

        component_version_entities.append(component_version_entity)

    component_version_query_service_mock.get_component_version.side_effect = component_version_entities

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        update_mandatory_components_list_command_handler.handle(
            command=update_mandatory_components_list_command_mock,
            component_version_qry_srv=component_version_query_service_mock,
            mandatory_components_list_qry_srv=mandatory_components_list_query_service_mock,
            uow=uow_mock,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        f"Mandatory components list for {update_mandatory_components_list_command_mock.mandatoryComponentsListPlatform.value} "
        f"{update_mandatory_components_list_command_mock.mandatoryComponentsListOsVersion.value} "
        f"({update_mandatory_components_list_command_mock.mandatoryComponentsListArchitecture.value}) can not be found."
    )


@freeze_time("2024-01-18")
def test_handle_should_update_list_with_prepended_and_appended_components(
    component_version_query_service_mock,
    get_test_component_version_with_specific_status,
    get_test_mandatory_components_list_with_positioned_components,
):
    # ARRANGE
    from app.packaging.domain.commands.component import (
        update_mandatory_components_list_command,
    )
    from app.packaging.domain.value_objects.component_version import (
        components_versions_list_value_object,
    )

    prepended_components = [
        component_version_entry.ComponentVersionEntry(
            componentId="comp-prepend-new",
            componentName="PrependComponentNew",
            componentVersionId="vers-prepend-new",
            componentVersionName="2.0.0",
            order=1,
        ),
    ]

    appended_components = [
        component_version_entry.ComponentVersionEntry(
            componentId="comp-append-new",
            componentName="AppendComponentNew",
            componentVersionId="vers-append-new",
            componentVersionName="3.0.0",
            order=1,
        ),
    ]

    command_mock = update_mandatory_components_list_command.UpdateMandatoryComponentsListCommand(
        mandatoryComponentsListPlatform=component_platform_value_object.from_str("Linux"),
        mandatoryComponentsListArchitecture=component_supported_architecture_value_object.from_str("amd64"),
        mandatoryComponentsListOsVersion=component_supported_os_version_value_object.from_str("Ubuntu 24"),
        prependedComponentsVersions=components_versions_list_value_object.from_list(prepended_components),
        appendedComponentsVersions=components_versions_list_value_object.from_list(appended_components),
        lastUpdatedBy=user_id_value_object.from_str("T123456"),
    )

    mandatory_components_list_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {mandatory_components_list.MandatoryComponentsList: mandatory_components_list_repo_mock}

    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)

    mandatory_components_list_query_service_mock = mock.create_autospec(
        spec=mandatory_components_list_query_service.MandatoryComponentsListQueryService
    )
    mandatory_components_list_query_service_mock.get_mandatory_components_list.return_value = (
        get_test_mandatory_components_list_with_positioned_components()
    )

    component_version_entities = []
    for comp in prepended_components + appended_components:
        entity = get_test_component_version_with_specific_status(
            status=component_version.ComponentVersionStatus.Released
        )
        entity.componentId = comp.componentId
        entity.componentVersionId = comp.componentVersionId
        component_version_entities.append(entity)

    component_version_query_service_mock.get_component_version.side_effect = component_version_entities

    # ACT
    update_mandatory_components_list_command_handler.handle(
        command=command_mock,
        component_version_qry_srv=component_version_query_service_mock,
        mandatory_components_list_qry_srv=mandatory_components_list_query_service_mock,
        uow=uow_mock,
    )

    # ASSERT
    call_args = mandatory_components_list_repo_mock.update_attributes.call_args
    positioned_components = call_args[1]["mandatoryComponentsVersions"]
    assertpy.assert_that(positioned_components).is_length(2)
    assertpy.assert_that(positioned_components[0]["position"]).is_equal_to("PREPEND")
    assertpy.assert_that(positioned_components[0]["order"]).is_equal_to(1)
    assertpy.assert_that(positioned_components[1]["position"]).is_equal_to("APPEND")
    assertpy.assert_that(positioned_components[1]["order"]).is_equal_to(1)
    uow_mock.commit.assert_called()
