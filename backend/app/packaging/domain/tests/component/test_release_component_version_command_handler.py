from typing import List
from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.packaging.domain.command_handlers.component import (
    release_component_version_command_handler,
)
from app.packaging.domain.commands.component import release_component_version_command
from app.packaging.domain.events.component import (
    component_version_release_completed,
)
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component_version
from app.packaging.domain.model.recipe import recipe_version
from app.packaging.domain.model.shared import component_version_entry
from app.packaging.domain.model.shared.component_version_entry import (
    ComponentVersionEntry,
)
from app.packaging.domain.tests.conftest import (
    TEST_COMPONENT_ID,
    TEST_COMPONENT_NAME,
    TEST_COMPONENT_VERSION_ID,
)
from app.packaging.domain.value_objects.component import component_id_value_object
from app.packaging.domain.value_objects.component_version import (
    component_version_id_value_object,
)
from app.packaging.domain.value_objects.shared import (
    project_id_value_object,
    user_id_value_object,
    user_role_value_object,
)
from app.shared.adapters.unit_of_work_v2 import unit_of_work
from app.shared.middleware.authorization import VirtualWorkbenchRoles


@pytest.fixture()
def get_release_component_version_command_mock():
    def _get_release_component_version_command_mock(
        user_roles: List[str] = [
            VirtualWorkbenchRoles.BetaUser,
            VirtualWorkbenchRoles.PlatformUser,
            VirtualWorkbenchRoles.ProductContributor,
        ]
    ):
        return release_component_version_command.ReleaseComponentVersionCommand(
            projectId=project_id_value_object.from_str("proj-1234"),
            componentId=component_id_value_object.from_str("comp-1234abcd"),
            componentVersionId=component_version_id_value_object.from_str("vers-1234abcd"),
            userRoles=[user_role_value_object.from_str(user_role) for user_role in user_roles],
            lastUpdatedBy=user_id_value_object.from_str("T000001"),
        )

    return _get_release_component_version_command_mock


@pytest.mark.parametrize(
    "fetched_release_name,expected_version_name",
    (
        ("2.0.0-rc.1", "2.0.0"),
        ("2.1.0-rc.1", "2.1.0"),
        ("2.0.1-rc.1", "2.0.1"),
    ),
)
@freeze_time("2023-10-12")
def test_handle_should_release_version(
    component_version_query_service_mock,
    get_release_component_version_command_mock,
    get_test_component_version_with_specific_version_name_and_status,
    fetched_release_name,
    expected_version_name,
    message_bus_mock,
    recipe_version_query_service_mock,
):
    # ARRANGE
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)

    repos_dict = {component_version.ComponentVersion: component_version_repo_mock}

    component_version_entity = get_test_component_version_with_specific_version_name_and_status(
        version_name=fetched_release_name,
        status=component_version.ComponentVersionStatus.Validated,
    )
    component_version_entity.componentVersionDependencies = list()
    component_version_query_service_mock.get_component_version.return_value = component_version_entity
    release_component_version_command_mock = get_release_component_version_command_mock()
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)

    # ACT
    release_component_version_command_handler.handle(
        command=release_component_version_command_mock,
        uow=uow_mock,
        message_bus=message_bus_mock,
        component_version_qry_srv=component_version_query_service_mock,
        recipe_version_qry_srv=recipe_version_query_service_mock,
    )

    # ASSERT
    pk = component_version.ComponentVersionPrimaryKey(
        componentId=release_component_version_command_mock.componentId.value,
        componentVersionId=release_component_version_command_mock.componentVersionId.value,
    )
    component_version_repo_mock.update_attributes.assert_called_once_with(
        pk,
        lastUpdateDate="2023-10-12T00:00:00+00:00",
        lastUpdateBy=release_component_version_command_mock.lastUpdatedBy.value,
        componentVersionName=expected_version_name,
        status=component_version.ComponentVersionStatus.Released,
    )
    uow_mock.commit.assert_called()
    message_bus_mock.publish.assert_called_once_with(
        component_version_release_completed.ComponentVersionReleaseCompleted(
            componentId=release_component_version_command_mock.componentId.value,
            componentVersionId=release_component_version_command_mock.componentVersionId.value,
            componentVersionDependencies=component_version_entity.componentVersionDependencies,
        )
    )


def test_handle_should_raise_exception_when_component_version_is_none(
    component_version_query_service_mock,
    get_release_component_version_command_mock,
    message_bus_mock,
    recipe_version_query_service_mock,
):
    # ARRANGE
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)

    repos_dict = {component_version.ComponentVersion: component_version_repo_mock}

    component_version_query_service_mock.get_component_version.return_value = None
    release_component_version_command_mock = get_release_component_version_command_mock()
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda x: repos_dict.get(x)

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        release_component_version_command_handler.handle(
            command=release_component_version_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_qry_srv=component_version_query_service_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        f"Version {release_component_version_command_mock.componentVersionId.value} of component {release_component_version_command_mock.componentId.value} does not exist."
    )


@pytest.mark.parametrize(
    "fetched_release_name",
    (
        ("2.0.0"),
        ("2.1.0"),
        ("2.0.1"),
    ),
)
def test_handle_should_raise_exception_when_version_is_not_rc(
    component_version_query_service_mock,
    get_release_component_version_command_mock,
    get_test_component_version_with_specific_version_name_and_status,
    fetched_release_name,
    message_bus_mock,
    recipe_version_query_service_mock,
    uow_mock,
):
    # ARRANGE
    component_version_query_service_mock.get_component_version.return_value = (
        get_test_component_version_with_specific_version_name_and_status(
            version_name=fetched_release_name,
            status=component_version.ComponentVersionStatus.Validated,
        )
    )
    release_component_version_command_mock = get_release_component_version_command_mock()

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        release_component_version_command_handler.handle(
            command=release_component_version_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_qry_srv=component_version_query_service_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        f"Can not release an already released component version ({fetched_release_name}) - only release candidates are allowed."
    )


@pytest.mark.parametrize(
    "component_version_status",
    (
        (component_version.ComponentVersionStatus.Creating),
        (component_version.ComponentVersionStatus.Created),
        (component_version.ComponentVersionStatus.Released),
        (component_version.ComponentVersionStatus.Testing),
        (component_version.ComponentVersionStatus.Updating),
        (component_version.ComponentVersionStatus.Failed),
    ),
)
def test_handle_should_raise_exception_when_version_status_is_not_allowed(
    component_version_query_service_mock,
    get_release_component_version_command_mock,
    get_test_component_version_with_specific_version_name_and_status,
    component_version_status,
    message_bus_mock,
    recipe_version_query_service_mock,
):
    # ARRANGE
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)

    repos_dict = {component_version.ComponentVersion: component_version_repo_mock}

    _component_version = get_test_component_version_with_specific_version_name_and_status(
        version_name="1.0.0-rc.1",
        status=component_version_status,
    )
    component_version_query_service_mock.get_component_version.return_value = _component_version
    release_component_version_command_mock = get_release_component_version_command_mock()
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda x: repos_dict.get(x)

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        release_component_version_command_handler.handle(
            command=release_component_version_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_qry_srv=component_version_query_service_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        f"Version 1.0.0-rc.1 of component {release_component_version_command_mock.componentId.value} can't be released while in {component_version_status} status: only {component_version.ComponentVersionStatus.Validated} is accepted."
    )


@pytest.mark.parametrize(
    "component_version_dependencies",
    (
        [
            component_version_entry.ComponentVersionEntry(
                componentId="comp-00000000",
                componentName="test-component-00000000",
                componentVersionId="vers-00000000",
                componentVersionName="1.0.0-rc.1",
                order=1,
            )
        ],
        [
            component_version_entry.ComponentVersionEntry(
                componentId="comp-00000000",
                componentName="test-component-00000000",
                componentVersionId="vers-00000000",
                componentVersionName="1.0.0-rc.1",
                order=1,
            ),
            component_version_entry.ComponentVersionEntry(
                componentId="comp-00000001",
                componentName="test-component-00000001",
                componentVersionId="vers-00000001",
                componentVersionName="1.0.0",
                order=2,
            ),
        ],
        [
            component_version_entry.ComponentVersionEntry(
                componentId="comp-00000001",
                componentName="test-component-00000001",
                componentVersionId="vers-00000001",
                componentVersionName="1.0.0",
                order=2,
            ),
            component_version_entry.ComponentVersionEntry(
                componentId="comp-00000000",
                componentName="test-component-00000000",
                componentVersionId="vers-00000000",
                componentVersionName="1.0.0-rc.1",
                order=1,
            ),
        ],
    ),
)
def test_validate_dependencies_should_raise_exception_when_dependencies_are_not_released(
    get_test_component_version_with_specific_version_name_and_status,
    component_version_dependencies,
):
    # ARRANGE
    component_version_entity: component_version.ComponentVersion = (
        get_test_component_version_with_specific_version_name_and_status(
            version_name="1.0.0-rc.1",
            status=component_version.ComponentVersionStatus.Validated,
        )
    )
    component_version_entity.componentVersionDependencies = component_version_dependencies

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        release_component_version_command_handler.__validate_dependencies(component_version_entity)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        f"Can not release the component version {component_version_entity.componentVersionName} "
        "because not all its dependencies have been released yet."
    )


@freeze_time("2023-10-12")
def test_handle_release_should_succeed_when_updating_downstream_dependencies(
    get_release_component_version_command_mock,
    component_version_query_service_mock,
    get_mock_components_versions_list_with_dependencies,
    message_bus_mock,
    recipe_version_query_service_mock,
):
    # ARRANGE
    expected_version_name = "1.0.0"
    components_version_list = get_mock_components_versions_list_with_dependencies()
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {component_version.ComponentVersion: component_version_repo_mock}
    component_version_query_service_mock.get_component_version.side_effect = components_version_list
    components_version_list[0].componentVersionDependencies = list()
    release_component_version_command_mock = get_release_component_version_command_mock()
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)

    # ACT
    release_component_version_command_handler.handle(
        command=release_component_version_command_mock,
        uow=uow_mock,
        message_bus=message_bus_mock,
        component_version_qry_srv=component_version_query_service_mock,
        recipe_version_qry_srv=recipe_version_query_service_mock,
    )

    # ASSERT
    uow_mock.commit.assert_called()
    component_version_repo_mock.update_attributes.assert_called_once_with(
        component_version.ComponentVersionPrimaryKey(
            componentId=release_component_version_command_mock.componentId.value,
            componentVersionId=release_component_version_command_mock.componentVersionId.value,
        ),
        lastUpdateDate="2023-10-12T00:00:00+00:00",
        lastUpdateBy=release_component_version_command_mock.lastUpdatedBy.value,
        componentVersionName=expected_version_name,
        status=component_version.ComponentVersionStatus.Released,
    )
    uow_mock.commit.assert_called()
    assertpy.assert_that(component_version_repo_mock.update_entity.call_count).is_equal_to(3)
    component_version_repo_mock.update_entity.assert_has_calls(
        [
            mock.call(
                component_version.ComponentVersionPrimaryKey(
                    componentId=f"comp-{i}",
                    componentVersionId=f"vers-{i}",
                ),
                component_version.ComponentVersion(
                    componentId=f"comp-{i}",
                    componentName=f"component-{i}",
                    componentVersionId=f"vers-{i}",
                    componentVersionName="1.0.0-rc.1",
                    componentVersionDescription="Test component version",
                    componentBuildVersionArn=f"arn:aws:imagebuilder:us-east-1:123456789012:component/comp-{i}/1.0.0-rc.1/1",
                    componentVersionS3Uri=f"s3://test-component-bucket/comp-{i}/1.0.0-rc.1/component.yaml",
                    componentPlatform="Linux",
                    componentSupportedArchitectures=["amd64", "arm64"],
                    componentSupportedOsVersions=["Ubuntu 24"],
                    componentVersionDependencies=[
                        ComponentVersionEntry(
                            componentId=TEST_COMPONENT_ID,
                            componentName=TEST_COMPONENT_NAME,
                            componentVersionId=TEST_COMPONENT_VERSION_ID,
                            componentVersionName=expected_version_name,
                            order=1,
                        )
                    ],
                    softwareVendor="Vector",
                    softwareVersion="1.0.0",
                    status="VALIDATED",
                    createDate="2024-01-11",
                    createdBy="2024-01-11",
                    lastUpdateDate="2024-01-11",
                    lastUpdatedBy="T0000001",
                ),
            )
            for i in range(3)
        ],
        any_order=False,
    )
    message_bus_mock.publish.assert_called_once_with(
        component_version_release_completed.ComponentVersionReleaseCompleted(
            componentId=release_component_version_command_mock.componentId.value,
            componentVersionId=release_component_version_command_mock.componentVersionId.value,
            componentVersionDependencies=components_version_list[0].componentVersionDependencies,
        )
    )


@freeze_time("2023-10-12")
def test_handle_release_should_succeed_when_updating_downstream_dependencies_function_only(
    component_version_query_service_mock,
    get_mock_components_versions_list_with_dependencies,
):
    # ARRANGE
    expected_version_name = "1.0.0"
    components_version_list = get_mock_components_versions_list_with_dependencies()
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {component_version.ComponentVersion: component_version_repo_mock}
    component_version_query_service_mock.get_component_version.side_effect = components_version_list[1:]
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)

    # ACT
    release_component_version_command_handler.__update_downstream_dependencies(
        update_component_version_name=expected_version_name,
        component_version_entity=components_version_list[0],
        uow=uow_mock,
        component_version_qry_srv=component_version_query_service_mock,
    )

    # ASSERT
    assertpy.assert_that(component_version_repo_mock.update_entity.call_count).is_equal_to(3)
    component_version_repo_mock.update_entity.assert_has_calls(
        [
            mock.call(
                component_version.ComponentVersionPrimaryKey(
                    componentId=f"comp-{i}",
                    componentVersionId=f"vers-{i}",
                ),
                component_version.ComponentVersion(
                    componentId=f"comp-{i}",
                    componentName=f"component-{i}",
                    componentVersionId=f"vers-{i}",
                    componentVersionName="1.0.0-rc.1",
                    componentVersionDescription="Test component version",
                    componentBuildVersionArn=f"arn:aws:imagebuilder:us-east-1:123456789012:component/comp-{i}/1.0.0-rc.1/1",
                    componentVersionS3Uri=f"s3://test-component-bucket/comp-{i}/1.0.0-rc.1/component.yaml",
                    componentPlatform="Linux",
                    componentSupportedArchitectures=["amd64", "arm64"],
                    componentSupportedOsVersions=["Ubuntu 24"],
                    componentVersionDependencies=[
                        ComponentVersionEntry(
                            componentId=TEST_COMPONENT_ID,
                            componentName=TEST_COMPONENT_NAME,
                            componentVersionId=TEST_COMPONENT_VERSION_ID,
                            componentVersionName=expected_version_name,
                            order=1,
                        )
                    ],
                    softwareVendor="Vector",
                    softwareVersion="1.0.0",
                    status="VALIDATED",
                    createDate="2024-01-11",
                    createdBy="2024-01-11",
                    lastUpdateDate="2024-01-11",
                    lastUpdatedBy="T0000001",
                ),
            )
            for i in range(3)
        ],
        any_order=False,
    )


@freeze_time("2023-10-12")
def test_handle_should_fail_when_no_component_is_returned_updating_downstream_dependencies(
    component_version_query_service_mock,
    get_mock_components_versions_list_with_dependencies,
):
    # ARRANGE
    components_version_list = get_mock_components_versions_list_with_dependencies()
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {component_version.ComponentVersion: component_version_repo_mock}
    component_version_query_service_mock.get_component_version.return_value = None
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)
    expected_version_name = "1.0.0-rc.2"

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        release_component_version_command_handler.__update_downstream_dependencies(
            update_component_version_name=expected_version_name,
            component_version_entity=components_version_list[0],
            uow=uow_mock,
            component_version_qry_srv=component_version_query_service_mock,
        )
    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to("Version vers-0 of component comp-0 does not exist.")


@pytest.mark.parametrize(
    "fetched_release_name,expected_version_name",
    (
        ("2.0.0-rc.1", "2.0.0"),
        ("2.1.0-rc.1", "2.1.0"),
        ("2.0.1-rc.1", "2.0.1"),
    ),
)
@freeze_time("2023-10-12")
def test_handle_should_release_version_and_update_recipe(
    component_version_query_service_mock,
    get_release_component_version_command_mock,
    get_test_component_version_with_specific_version_name_and_status_with_recipe,
    fetched_release_name,
    expected_version_name,
    message_bus_mock,
    recipe_version_query_service_mock,
    get_recipe_version_with_rc_component,
    uow_mock,
    generic_repo_mock,
):
    # ARRANGE
    component_version_entity = get_test_component_version_with_specific_version_name_and_status_with_recipe(
        version_name=fetched_release_name,
        status=component_version.ComponentVersionStatus.Validated,
    )
    component_version_entity.componentVersionDependencies = list()
    component_version_query_service_mock.get_component_version.return_value = component_version_entity
    release_component_version_command_mock = get_release_component_version_command_mock()
    recipe_version_query_service_mock.get_recipe_version.return_value = get_recipe_version_with_rc_component(
        component_id=component_version_entity.componentId,
        component_version_id=component_version_entity.componentVersionId,
        component_version_name=fetched_release_name,
    )

    # ACT
    release_component_version_command_handler.handle(
        command=release_component_version_command_mock,
        uow=uow_mock,
        message_bus=message_bus_mock,
        component_version_qry_srv=component_version_query_service_mock,
        recipe_version_qry_srv=recipe_version_query_service_mock,
    )

    # ASSERT
    uow_mock.commit.assert_called()
    # lets check the component update
    generic_repo_mock.update_attributes.assert_called_once_with(
        component_version.ComponentVersionPrimaryKey(
            componentId=component_version_entity.componentId,
            componentVersionId=component_version_entity.componentVersionId,
        ),
        lastUpdateDate="2023-10-12T00:00:00+00:00",
        lastUpdateBy=release_component_version_command_mock.lastUpdatedBy.value,
        componentVersionName=expected_version_name,
        status=component_version.ComponentVersionStatus.Released,
    )

    # lets check the recipe update
    final_recipe = get_recipe_version_with_rc_component(
        component_id=component_version_entity.componentId,
        component_version_id=component_version_entity.componentVersionId,
        component_version_name=expected_version_name,
    )
    generic_repo_mock.update_entity.assert_called_once_with(
        recipe_version.RecipeVersionPrimaryKey(
            recipeId=final_recipe.recipeId,
            recipeVersionId=final_recipe.recipeVersionId,
        ),
        final_recipe,
    )
    message_bus_mock.publish.assert_called_once_with(
        component_version_release_completed.ComponentVersionReleaseCompleted(
            componentId=release_component_version_command_mock.componentId.value,
            componentVersionId=release_component_version_command_mock.componentVersionId.value,
            componentVersionDependencies=component_version_entity.componentVersionDependencies,
        )
    )
