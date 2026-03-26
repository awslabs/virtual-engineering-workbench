import os
from unittest import mock

import assertpy
import boto3
import pytest
from freezegun import freeze_time

from app.packaging.domain.command_handlers.recipe import (
    update_recipe_version_command_handler,
)
from app.packaging.domain.events.recipe import recipe_version_update_started
from app.packaging.domain.exceptions.domain_exception import DomainException
from app.packaging.domain.model.component import component_version
from app.packaging.domain.model.recipe import recipe_version
from app.packaging.domain.model.shared import component_version_entry
from app.packaging.domain.value_objects.recipe_version import (
    recipe_version_components_versions_value_object,
)
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work


@pytest.mark.parametrize(
    "fetched_release_name,expected_version_name",
    (
        ("1.0.0-rc.1", "1.0.0-rc.2"),
        ("1.1.0-rc.1", "1.1.0-rc.2"),
        ("1.0.1-rc.1", "1.0.1-rc.2"),
    ),
)
@freeze_time("2023-12-01")
def test_handle_should_update_recipe_version(
    recipe_version_query_service_mock,
    update_recipe_version_command_mock,
    component_version_query_service_mock,
    recipe_query_service_mock,
    parameter_service_mock,
    mandatory_components_list_query_service_mock,
    mock_system_configuration_mapping,
    mock_recipe_object,
    get_test_ami_id,
    get_test_component_version_with_specific_status,
    get_test_mandatory_components_list_with_specific_mandatory_components_versions,
    get_test_recipe_version_with_specific_version_name,
    fetched_release_name,
    expected_version_name,
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    recipe_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {recipe_version.RecipeVersion: recipe_version_repo_mock}
    mandatory_components_list_query_service_mock.get_mandatory_components_list.return_value = (
        get_test_mandatory_components_list_with_specific_mandatory_components_versions()
    )
    recipe_version_entity: recipe_version.RecipeVersion = get_test_recipe_version_with_specific_version_name(
        fetched_release_name
    )
    recipe_version_query_service_mock.get_recipe_version.return_value = recipe_version_entity
    recipe_query_service_mock.get_recipe.return_value = mock_recipe_object
    parameter_service_mock.get_parameter_value.return_value = get_test_ami_id
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)
    component_version_entities = list()
    for recipe_component_version in update_recipe_version_command_mock.recipeComponentsVersions.value:
        component_version_entity = get_test_component_version_with_specific_status(
            status=component_version.ComponentVersionStatus.Released
        )
        component_version_entity.componentId = recipe_component_version.componentId
        component_version_entity.componentVersionId = recipe_component_version.componentVersionId

        component_version_entities.append(component_version_entity)

    component_version_query_service_mock.get_component_version.side_effect = component_version_entities

    # ACT
    update_recipe_version_command_handler.handle(
        command=update_recipe_version_command_mock,
        uow=uow_mock,
        message_bus=message_bus_mock,
        component_version_qry_srv=component_version_query_service_mock,
        recipe_version_query_service=recipe_version_query_service_mock,
        recipe_qry_service=recipe_query_service_mock,
        parameter_qry_srv=parameter_service_mock,
        mandatory_components_list_qry_srv=mandatory_components_list_query_service_mock,
        system_configuration_mapping=mock_system_configuration_mapping,
    )

    # ASSERT
    call_args = recipe_version_repo_mock.update_attributes.call_args
    assertpy.assert_that(call_args[0][0]).is_equal_to(
        recipe_version.RecipeVersionPrimaryKey(
            recipeId=update_recipe_version_command_mock.recipeId.value,
            recipeVersionId=update_recipe_version_command_mock.recipeVersionId.value,
        )
    )
    assertpy.assert_that(call_args[1]["lastUpdatedBy"]).is_equal_to(
        update_recipe_version_command_mock.lastUpdatedBy.value
    )
    assertpy.assert_that(call_args[1]["lastUpdateDate"]).is_equal_to("2023-12-01T00:00:00+00:00")
    assertpy.assert_that(call_args[1]["recipeVersionName"]).is_equal_to(expected_version_name)
    assertpy.assert_that(call_args[1]["parentImageUpstreamId"]).is_equal_to(get_test_ami_id)
    assertpy.assert_that(call_args[1]["recipeVersionDescription"]).is_equal_to(
        update_recipe_version_command_mock.recipeVersionDescription.value
    )
    assertpy.assert_that(call_args[1]["recipeVersionVolumeSize"]).is_equal_to("8")
    assertpy.assert_that(call_args[1]["status"]).is_equal_to(recipe_version.RecipeVersionStatus.Updating)

    components = call_args[1]["recipeComponentsVersions"]
    assertpy.assert_that(components).is_length(6)

    assertpy.assert_that(components[0]["componentId"]).is_equal_to("comp-1234abc")
    assertpy.assert_that(components[0]["order"]).is_equal_to(1)
    assertpy.assert_that(components[0]["position"]).is_equal_to(
        component_version_entry.ComponentVersionEntryPosition.Prepend
    )

    assertpy.assert_that(components[1]["componentId"]).is_equal_to("comp-1234fghi")
    assertpy.assert_that(components[1]["order"]).is_equal_to(2)
    assertpy.assert_that(components[1]["position"]).is_equal_to(
        component_version_entry.ComponentVersionEntryPosition.Prepend
    )

    assertpy.assert_that(components[2]["componentId"]).is_equal_to("comp-1234def")
    assertpy.assert_that(components[2]["order"]).is_equal_to(3)
    assertpy.assert_that(components[2]["position"]).is_equal_to(
        component_version_entry.ComponentVersionEntryPosition.Prepend
    )

    assertpy.assert_that(components[3]["componentId"]).is_equal_to("comp-1234pqr")
    assertpy.assert_that(components[3]["order"]).is_equal_to(4)
    assertpy.assert_that(components[3]["position"]).is_none()

    assertpy.assert_that(components[4]["componentId"]).is_equal_to("comp-1234mno")
    assertpy.assert_that(components[4]["order"]).is_equal_to(5)
    assertpy.assert_that(components[4]["position"]).is_none()

    assertpy.assert_that(components[5]["componentId"]).is_equal_to("comp-1234jkl")
    assertpy.assert_that(components[5]["order"]).is_equal_to(6)
    assertpy.assert_that(components[5]["position"]).is_none()

    uow_mock.commit.assert_called()
    message_bus_mock.publish.assert_called_once_with(
        recipe_version_update_started.RecipeVersionUpdateStarted(
            project_id="proj-12345",
            recipe_id="reci-1234abcd",
            recipe_version_id="vers-1234abcd",
            recipe_version_name=expected_version_name,
            parent_image_upstream_id=get_test_ami_id,
            previous_recipe_components_versions=recipe_version_entity.recipeComponentsVersions,
            recipe_components_versions=[
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234abc",
                    componentVersionName="3.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234fghi",
                    componentName="component-1234fghi",
                    componentVersionId="vers-123fghi",
                    componentVersionName="1.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=2,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234def",
                    componentName="component-1234def",
                    componentVersionId="vers-1234def",
                    componentVersionName="2.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=3,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234pqr",
                    componentName="component-1234pqr",
                    componentVersionId="vers-1234pqr",
                    componentVersionName="3.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=4,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234mno",
                    componentName="component-1234mno",
                    componentVersionId="vers-1234mno",
                    componentVersionName="2.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=5,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234jkl",
                    componentName="component-1234jkl",
                    componentVersionId="vers-1234jkl",
                    componentVersionName="1.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=6,
                ),
            ],
            recipe_version_volume_size="8",
        )
    )


@pytest.mark.parametrize(
    "mandatory_components_versions,recipe_component_versions,expected_recipe_component_versions",
    (
        (
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234abc",
                    componentVersionName="1.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
            ],
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-123def",
                    componentName="component-1234def",
                    componentVersionId="vers-1234def",
                    componentVersionName="2.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                ),
            ],
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234abc",
                    componentVersionName="1.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-123def",
                    componentName="component-1234def",
                    componentVersionId="vers-1234def",
                    componentVersionName="2.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=2,
                ),
            ],
        ),
        (
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234ghi",
                    componentVersionName="3.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
            ],
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234abc",
                    componentVersionName="1.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-123def",
                    componentName="component-1234def",
                    componentVersionId="vers-1234def",
                    componentVersionName="2.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                ),
            ],
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234ghi",
                    componentVersionName="3.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-123def",
                    componentName="component-1234def",
                    componentVersionId="vers-1234def",
                    componentVersionName="2.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=2,
                ),
            ],
        ),
        (
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234abc",
                    componentVersionName="1.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-123def",
                    componentName="component-1234def",
                    componentVersionId="vers-1234def",
                    componentVersionName="2.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=2,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
            ],
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-123ghi",
                    componentName="component-1234ghi",
                    componentVersionId="vers-1234ghi",
                    componentVersionName="3.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                ),
            ],
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-123ghi",
                    componentName="component-1234ghi",
                    componentVersionId="vers-1234ghi",
                    componentVersionName="3.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=3,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234abc",
                    componentVersionName="1.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-123def",
                    componentName="component-1234def",
                    componentVersionId="vers-1234def",
                    componentVersionName="2.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=2,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
            ],
        ),
        (
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234abc",
                    componentVersionName="1.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-123def",
                    componentName="component-1234def",
                    componentVersionId="vers-1234def",
                    componentVersionName="2.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=2,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
            ],
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-123ghi",
                    componentName="component-1234ghi",
                    componentVersionId="vers-1234ghi",
                    componentVersionName="3.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-123jkl",
                    componentName="component-1234jkl",
                    componentVersionId="vers-1234jkl",
                    componentVersionName="4.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=2,
                ),
            ],
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234abc",
                    componentVersionName="1.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-123def",
                    componentName="component-1234def",
                    componentVersionId="vers-1234def",
                    componentVersionName="2.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=2,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-123ghi",
                    componentName="component-1234ghi",
                    componentVersionId="vers-1234ghi",
                    componentVersionName="3.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=3,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-123jkl",
                    componentName="component-1234jkl",
                    componentVersionId="vers-1234jkl",
                    componentVersionName="4.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=4,
                ),
            ],
        ),
        (
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234mno",
                    componentVersionName="5.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-123def",
                    componentName="component-1234def",
                    componentVersionId="vers-1234pqr",
                    componentVersionName="6.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=2,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
            ],
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-123ghi",
                    componentName="component-1234ghi",
                    componentVersionId="vers-1234ghi",
                    componentVersionName="3.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-123jkl",
                    componentName="component-1234jkl",
                    componentVersionId="vers-1234jkl",
                    componentVersionName="4.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=2,
                ),
            ],
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234mno",
                    componentVersionName="5.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=1,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-123def",
                    componentName="component-1234def",
                    componentVersionId="vers-1234pqr",
                    componentVersionName="6.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=2,
                    position=component_version_entry.ComponentVersionEntryPosition.Prepend,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-123ghi",
                    componentName="component-1234ghi",
                    componentVersionId="vers-1234ghi",
                    componentVersionName="3.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=3,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-123jkl",
                    componentName="component-1234jkl",
                    componentVersionId="vers-1234jkl",
                    componentVersionName="4.0.0",
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                    order=4,
                ),
            ],
        ),
    ),
)
@freeze_time("2023-12-01")
def test_handle_should_update_recipe_version_with_correct_component_versions(
    recipe_version_query_service_mock,
    update_recipe_version_command_mock,
    component_version_query_service_mock,
    recipe_query_service_mock,
    parameter_service_mock,
    mandatory_components_list_query_service_mock,
    mock_system_configuration_mapping,
    mock_recipe_object,
    get_test_ami_id,
    get_test_component_version_with_specific_status,
    get_test_mandatory_components_list_with_specific_mandatory_components_versions,
    get_test_recipe_version_with_specific_version_name,
    mandatory_components_versions,
    recipe_component_versions,
    expected_recipe_component_versions,
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    recipe_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {recipe_version.RecipeVersion: recipe_version_repo_mock}
    mandatory_components_list_query_service_mock.get_mandatory_components_list.return_value = (
        get_test_mandatory_components_list_with_specific_mandatory_components_versions(
            mandatory_components_versions=mandatory_components_versions
        )
    )
    recipe_version_entity: recipe_version.RecipeVersion = get_test_recipe_version_with_specific_version_name(
        "1.0.0-rc.1"
    )
    recipe_version_query_service_mock.get_recipe_version.return_value = recipe_version_entity
    recipe_query_service_mock.get_recipe.return_value = mock_recipe_object
    parameter_service_mock.get_parameter_value.return_value = get_test_ami_id
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)
    update_recipe_version_command_mock.recipeComponentsVersions = (
        recipe_version_components_versions_value_object.from_list(recipe_component_versions)
    )
    component_version_entities = list()
    for recipe_component_version in recipe_component_versions:
        component_version_entity = get_test_component_version_with_specific_status(
            status=component_version.ComponentVersionStatus.Released
        )
        component_version_entity.componentId = recipe_component_version.componentId
        component_version_entity.componentVersionId = recipe_component_version.componentVersionId

        component_version_entities.append(component_version_entity)

    component_version_query_service_mock.get_component_version.side_effect = component_version_entities

    # ACT
    update_recipe_version_command_handler.handle(
        command=update_recipe_version_command_mock,
        uow=uow_mock,
        message_bus=message_bus_mock,
        component_version_qry_srv=component_version_query_service_mock,
        recipe_version_query_service=recipe_version_query_service_mock,
        recipe_qry_service=recipe_query_service_mock,
        parameter_qry_srv=parameter_service_mock,
        mandatory_components_list_qry_srv=mandatory_components_list_query_service_mock,
        system_configuration_mapping=mock_system_configuration_mapping,
    )

    # ASSERT
    call_args = recipe_version_repo_mock.update_attributes.call_args
    assertpy.assert_that(call_args[0][0]).is_equal_to(
        recipe_version.RecipeVersionPrimaryKey(
            recipeId=update_recipe_version_command_mock.recipeId.value,
            recipeVersionId=update_recipe_version_command_mock.recipeVersionId.value,
        )
    )
    assertpy.assert_that(call_args[1]["lastUpdatedBy"]).is_equal_to(
        update_recipe_version_command_mock.lastUpdatedBy.value
    )
    assertpy.assert_that(call_args[1]["lastUpdateDate"]).is_equal_to("2023-12-01T00:00:00+00:00")
    assertpy.assert_that(call_args[1]["recipeVersionName"]).is_equal_to("1.0.0-rc.2")
    assertpy.assert_that(call_args[1]["parentImageUpstreamId"]).is_equal_to(get_test_ami_id)
    assertpy.assert_that(call_args[1]["recipeVersionDescription"]).is_equal_to(
        update_recipe_version_command_mock.recipeVersionDescription.value
    )
    assertpy.assert_that(call_args[1]["recipeVersionVolumeSize"]).is_equal_to("8")
    assertpy.assert_that(call_args[1]["status"]).is_equal_to(recipe_version.RecipeVersionStatus.Updating)

    components = call_args[1]["recipeComponentsVersions"]
    assertpy.assert_that(components).is_length(len(expected_recipe_component_versions))

    mandatory_ids = {c.componentId for c in mandatory_components_versions}
    user_ids = {c.componentId for c in recipe_component_versions if c.componentId not in mandatory_ids}

    for i, comp in enumerate(components):
        if i < len(mandatory_components_versions):
            assertpy.assert_that(comp["componentId"]).is_in(*mandatory_ids)
            assertpy.assert_that(comp["position"]).is_equal_to(
                component_version_entry.ComponentVersionEntryPosition.Prepend
            )
        else:
            assertpy.assert_that(comp["componentId"]).is_in(*user_ids)
            assertpy.assert_that(comp["position"]).is_none()
        assertpy.assert_that(comp["order"]).is_equal_to(i + 1)

    uow_mock.commit.assert_called()

    publish_call_args = message_bus_mock.publish.call_args[0][0]
    assertpy.assert_that(publish_call_args.project_id).is_equal_to("proj-12345")
    assertpy.assert_that(publish_call_args.recipe_id).is_equal_to("reci-1234abcd")
    assertpy.assert_that(publish_call_args.recipe_version_id).is_equal_to("vers-1234abcd")
    assertpy.assert_that(publish_call_args.recipe_version_name).is_equal_to("1.0.0-rc.2")
    assertpy.assert_that(publish_call_args.parent_image_upstream_id).is_equal_to(get_test_ami_id)
    assertpy.assert_that(publish_call_args.recipe_version_volume_size).is_equal_to("8")


def test_handle_should_raise_an_exception_when_recipe_version_not_found(
    recipe_version_query_service_mock,
    update_recipe_version_command_mock,
    component_version_query_service_mock,
    recipe_query_service_mock,
    parameter_service_mock,
    mandatory_components_list_query_service_mock,
    mock_system_configuration_mapping,
    get_test_ami_id,
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    recipe_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {recipe_version.RecipeVersion: recipe_version_repo_mock}
    mandatory_components_list_query_service_mock.get_mandatory_components_list.return_value = None
    recipe_version_query_service_mock.get_recipe_version.return_value = None
    recipe_query_service_mock.get_recipe.return_value = None
    parameter_service_mock.get_parameter_value.return_value = get_test_ami_id
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)

    # ACT
    with pytest.raises(DomainException) as e:
        update_recipe_version_command_handler.handle(
            command=update_recipe_version_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_qry_srv=component_version_query_service_mock,
            recipe_version_query_service=recipe_version_query_service_mock,
            recipe_qry_service=recipe_query_service_mock,
            parameter_qry_srv=parameter_service_mock,
            mandatory_components_list_qry_srv=mandatory_components_list_query_service_mock,
            system_configuration_mapping=mock_system_configuration_mapping,
        )

    # ASSERT
    assert (
        str(e.value)
        == f"No recipe version {update_recipe_version_command_mock.recipeVersionId.value} found for {update_recipe_version_command_mock.recipeId.value}"
    )


def test_handle_should_raise_an_exception_when_recipe_version_is_not_valid(
    recipe_version_query_service_mock,
    update_recipe_version_command_mock,
    component_version_query_service_mock,
    recipe_query_service_mock,
    parameter_service_mock,
    mandatory_components_list_query_service_mock,
    mock_system_configuration_mapping,
    mock_recipe_object,
    get_test_ami_id,
    get_test_mandatory_components_list_with_specific_mandatory_components_versions,
    get_test_recipe_version_with_specific_version_name,
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    recipe_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {recipe_version.RecipeVersion: recipe_version_repo_mock}
    mandatory_components_list_query_service_mock.get_mandatory_components_list.return_value = (
        get_test_mandatory_components_list_with_specific_mandatory_components_versions()
    )
    recipe_version_name = "AAA"
    recipe_version_query_service_mock.get_recipe_version.return_value = (
        get_test_recipe_version_with_specific_version_name(recipe_version_name)
    )
    recipe_query_service_mock.get_recipe.return_value = mock_recipe_object
    parameter_service_mock.get_parameter_value.return_value = get_test_ami_id
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)

    # ACT
    with pytest.raises(DomainException) as e:
        update_recipe_version_command_handler.handle(
            command=update_recipe_version_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_qry_srv=component_version_query_service_mock,
            recipe_version_query_service=recipe_version_query_service_mock,
            recipe_qry_service=recipe_query_service_mock,
            parameter_qry_srv=parameter_service_mock,
            mandatory_components_list_qry_srv=mandatory_components_list_query_service_mock,
            system_configuration_mapping=mock_system_configuration_mapping,
        )

    # ASSERT
    assert str(e.value) == f"Not a semantic version {recipe_version_name}"


@pytest.mark.parametrize("fetched_version_name", ("1.0.0", "1.0.1", "1.2.3"))
def test_handle_should_raise_an_exception_when_recipe_version_is_not_rc(
    recipe_version_query_service_mock,
    update_recipe_version_command_mock,
    component_version_query_service_mock,
    recipe_query_service_mock,
    parameter_service_mock,
    mandatory_components_list_query_service_mock,
    mock_system_configuration_mapping,
    mock_recipe_object,
    fetched_version_name,
    get_test_ami_id,
    get_test_mandatory_components_list_with_specific_mandatory_components_versions,
    get_test_recipe_version_with_specific_version_name,
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    recipe_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {recipe_version.RecipeVersion: recipe_version_repo_mock}
    mandatory_components_list_query_service_mock.get_mandatory_components_list.return_value = (
        get_test_mandatory_components_list_with_specific_mandatory_components_versions()
    )
    recipe_version_query_service_mock.get_recipe_version.return_value = (
        get_test_recipe_version_with_specific_version_name(fetched_version_name)
    )
    recipe_query_service_mock.get_recipe.return_value = mock_recipe_object
    parameter_service_mock.get_parameter_value.return_value = get_test_ami_id
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)

    # ACT
    with pytest.raises(DomainException) as e:
        update_recipe_version_command_handler.handle(
            command=update_recipe_version_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_qry_srv=component_version_query_service_mock,
            recipe_version_query_service=recipe_version_query_service_mock,
            recipe_qry_service=recipe_query_service_mock,
            parameter_qry_srv=parameter_service_mock,
            mandatory_components_list_qry_srv=mandatory_components_list_query_service_mock,
            system_configuration_mapping=mock_system_configuration_mapping,
        )

    # ASSERT
    assert str(e.value) == f"Can not update an already Generally Available recipe version. {fetched_version_name}"


def test_handle_should_raise_an_exception_when_recipe_not_found(
    get_test_recipe_version_with_specific_version_name,
    component_version_query_service_mock,
    recipe_version_query_service_mock,
    update_recipe_version_command_mock,
    recipe_query_service_mock,
    parameter_service_mock,
    mandatory_components_list_query_service_mock,
    mock_system_configuration_mapping,
    get_test_ami_id,
    get_test_mandatory_components_list_with_specific_mandatory_components_versions,
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    recipe_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {recipe_version.RecipeVersion: recipe_version_repo_mock}
    mandatory_components_list_query_service_mock.get_mandatory_components_list.return_value = (
        get_test_mandatory_components_list_with_specific_mandatory_components_versions()
    )
    recipe_version_query_service_mock.get_recipe_version.return_value = (
        get_test_recipe_version_with_specific_version_name("1.0.0-rc.1")
    )
    recipe_query_service_mock.get_recipe.side_effect = Exception("Recipe not found.")
    parameter_service_mock.get_parameter_value.return_value = get_test_ami_id
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)

    # ACT
    with pytest.raises(DomainException) as e:
        update_recipe_version_command_handler.handle(
            command=update_recipe_version_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_qry_srv=component_version_query_service_mock,
            recipe_version_query_service=recipe_version_query_service_mock,
            recipe_qry_service=recipe_query_service_mock,
            parameter_qry_srv=parameter_service_mock,
            mandatory_components_list_qry_srv=mandatory_components_list_query_service_mock,
            system_configuration_mapping=mock_system_configuration_mapping,
        )

    # ASSERT
    assert str(e.value) == f"Recipe {update_recipe_version_command_mock.recipeId.value} not found."


def test_handle_should_raise_an_exception_if_recipe_component_versions_don_t_exist(
    update_recipe_version_command_mock,
    get_test_ami_id,
    get_test_mandatory_components_list_with_specific_mandatory_components_versions,
    get_test_recipe_version_with_specific_version_name,
    component_version_query_service_mock,
    mandatory_components_list_query_service_mock,
    mock_recipe_object,
    mock_system_configuration_mapping,
    parameter_service_mock,
    recipe_version_query_service_mock,
    recipe_query_service_mock,
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    recipe_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {recipe_version.RecipeVersion: recipe_version_repo_mock}
    mandatory_components_list_query_service_mock.get_mandatory_components_list.return_value = (
        get_test_mandatory_components_list_with_specific_mandatory_components_versions()
    )
    recipe_version_query_service_mock.get_recipe_version.return_value = (
        get_test_recipe_version_with_specific_version_name("1.0.0-rc.1")
    )
    recipe_query_service_mock.get_recipe.return_value = mock_recipe_object
    parameter_service_mock.get_parameter_value.return_value = get_test_ami_id
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)
    component_version_query_service_mock.get_component_version.side_effect = [
        None for _ in range(len(update_recipe_version_command_mock.recipeComponentsVersions.value))
    ]
    first_recipe_component_version = sorted(
        update_recipe_version_command_mock.recipeComponentsVersions.value,
        key=lambda recipe_component_version: recipe_component_version.order,
    )[0]

    # ACT
    with pytest.raises(DomainException) as e:
        update_recipe_version_command_handler.handle(
            command=update_recipe_version_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_qry_srv=component_version_query_service_mock,
            recipe_version_query_service=recipe_version_query_service_mock,
            recipe_qry_service=recipe_query_service_mock,
            parameter_qry_srv=parameter_service_mock,
            mandatory_components_list_qry_srv=mandatory_components_list_query_service_mock,
            system_configuration_mapping=mock_system_configuration_mapping,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
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
    ),
)
def test_handle_should_raise_an_exception_if_recipe_component_versions_are_not_validated_or_released(
    update_recipe_version_command_mock,
    get_test_ami_id,
    get_test_component_version_with_specific_version_name_and_status,
    get_test_mandatory_components_list_with_specific_mandatory_components_versions,
    get_test_recipe_version_with_specific_version_name,
    component_version_query_service_mock,
    mandatory_components_list_query_service_mock,
    mock_recipe_object,
    mock_system_configuration_mapping,
    parameter_service_mock,
    recipe_version_query_service_mock,
    recipe_query_service_mock,
    status,
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    recipe_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {recipe_version.RecipeVersion: recipe_version_repo_mock}
    mandatory_components_list_query_service_mock.get_mandatory_components_list.return_value = (
        get_test_mandatory_components_list_with_specific_mandatory_components_versions()
    )
    recipe_version_query_service_mock.get_recipe_version.return_value = (
        get_test_recipe_version_with_specific_version_name("1.0.0-rc.1")
    )
    recipe_query_service_mock.get_recipe.return_value = mock_recipe_object
    parameter_service_mock.get_parameter_value.return_value = get_test_ami_id
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)
    component_version_entities = list()
    recipe_versions = sorted(
        update_recipe_version_command_mock.recipeComponentsVersions.value,
        key=lambda recipe_component_version: recipe_component_version.order,
    )
    for recipe_component_version in recipe_versions:
        component_version_entity = get_test_component_version_with_specific_version_name_and_status(
            version_name=recipe_component_version.componentVersionName,
            status=status,
        )
        component_version_entity.componentId = recipe_component_version.componentId
        component_version_entity.componentVersionId = recipe_component_version.componentVersionId

        component_version_entities.append(component_version_entity)

    component_version_query_service_mock.get_component_version.side_effect = component_version_entities
    first_recipe_component_version = recipe_versions[0]

    # ACT
    with pytest.raises(DomainException) as e:
        update_recipe_version_command_handler.handle(
            command=update_recipe_version_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_qry_srv=component_version_query_service_mock,
            recipe_version_query_service=recipe_version_query_service_mock,
            recipe_qry_service=recipe_query_service_mock,
            parameter_qry_srv=parameter_service_mock,
            mandatory_components_list_qry_srv=mandatory_components_list_query_service_mock,
            system_configuration_mapping=mock_system_configuration_mapping,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        f"Version {first_recipe_component_version.componentVersionName} of component "
        f"{first_recipe_component_version.componentId} can't be included in this recipe version "
        f"while in {status} status: only {component_version.ComponentVersionStatus.Released} "
        f"and {component_version.ComponentVersionStatus.Validated} states are accepted."
    )


def test_handle_should_raise_exception_if_parameter_doesnt_exist_when_updating_version(
    get_test_recipe_version_with_specific_version_name,
    update_recipe_version_command_mock,
    component_version_query_service_mock,
    recipe_version_query_service_mock,
    recipe_query_service_mock,
    mock_system_configuration_mapping,
    mock_recipe_object,
    parameter_service_mock,
    mandatory_components_list_query_service_mock,
    get_test_mandatory_components_list_with_specific_mandatory_components_versions,
):
    # ARRANGE
    os.environ["AWS_REGION"] = "us-east-1"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    recipe_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {recipe_version.RecipeVersion: recipe_version_repo_mock}
    mandatory_components_list_query_service_mock.get_mandatory_components_list.return_value = (
        get_test_mandatory_components_list_with_specific_mandatory_components_versions()
    )
    recipe_version_query_service_mock.get_recipe_version.return_value = (
        get_test_recipe_version_with_specific_version_name("1.0.0-rc.1")
    )
    recipe_query_service_mock.get_recipe.return_value = mock_recipe_object
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)
    parameter_service_mock.get_parameter_value.side_effect = boto3.client(
        "ssm", region_name="us-east-1"
    ).exceptions.ParameterNotFound(
        operation_name="GetParameter",
        error_response={"Code": "ParameterNotFound", "Message": ""},
    )

    # ACT
    with pytest.raises(DomainException) as exec_info:
        update_recipe_version_command_handler.handle(
            command=update_recipe_version_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_qry_srv=component_version_query_service_mock,
            recipe_version_query_service=recipe_version_query_service_mock,
            recipe_qry_service=recipe_query_service_mock,
            parameter_qry_srv=parameter_service_mock,
            mandatory_components_list_qry_srv=mandatory_components_list_query_service_mock,
            system_configuration_mapping=mock_system_configuration_mapping,
        )
    assertpy.assert_that(str(exec_info.value)).is_equal_to("Parameter ami_ssm_param_name not found.")


@pytest.mark.parametrize(
    "recipe_component_versions",
    (
        (
            component_version_entry.ComponentVersionEntry(
                componentId="comp-1234jkl",
                componentName="component-1234jkl",
                componentVersionId="vers-1234jkl",
                componentVersionName="1.0.0",
                componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                order=1,
            ),
            component_version_entry.ComponentVersionEntry(
                componentId="comp-1234jkl",
                componentName="component-1234jkl",
                componentVersionId="vers-1234mno",
                componentVersionName="2.0.0",
                componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                order=2,
            ),
        ),
        (
            component_version_entry.ComponentVersionEntry(
                componentId="comp-1234jkl",
                componentName="component-1234jkl",
                componentVersionId="vers-1234jkl",
                componentVersionName="1.0.0",
                componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                order=1,
            ),
            component_version_entry.ComponentVersionEntry(
                componentId="comp-1234jkl",
                componentName="component-1234jkl",
                componentVersionId="vers-1234mno",
                componentVersionName="2.0.0",
                componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                order=2,
            ),
            component_version_entry.ComponentVersionEntry(
                componentId="comp-1234jkl",
                componentName="component-1234jkl",
                componentVersionId="vers-1234pqr",
                componentVersionName="3.0.0",
                componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                order=3,
            ),
        ),
        (
            component_version_entry.ComponentVersionEntry(
                componentId="comp-1234jkl",
                componentName="component-1234jkl",
                componentVersionId="vers-1234jkl",
                componentVersionName="1.0.0",
                componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                order=1,
            ),
            component_version_entry.ComponentVersionEntry(
                componentId="comp-1234jkl",
                componentName="component-1234jkl",
                componentVersionId="vers-1234mno",
                componentVersionName="2.0.0",
                componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                order=2,
            ),
            component_version_entry.ComponentVersionEntry(
                componentId="comp-1234pqr",
                componentName="component-1234pqr",
                componentVersionId="vers-1234pqr",
                componentVersionName="3.0.0",
                componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                order=3,
            ),
            component_version_entry.ComponentVersionEntry(
                componentId="comp-1234pqr",
                componentName="component-1234pqr",
                componentVersionId="vers-1234stu",
                componentVersionName="4.0.0",
                componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
                order=4,
            ),
        ),
    ),
)
def test_handle_should_raise_exception_with_duplicate_components(
    recipe_component_versions,
    update_recipe_version_command_mock,
    get_test_ami_id,
    get_test_component_version_with_specific_status,
    get_test_mandatory_components_list_with_specific_mandatory_components_versions,
    get_test_recipe_version_with_specific_version_name,
    component_version_query_service_mock,
    mandatory_components_list_query_service_mock,
    mock_recipe_object,
    mock_system_configuration_mapping,
    parameter_service_mock,
    recipe_version_query_service_mock,
    recipe_query_service_mock,
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    recipe_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {recipe_version.RecipeVersion: recipe_version_repo_mock}
    mandatory_components_list_query_service_mock.get_mandatory_components_list.return_value = (
        get_test_mandatory_components_list_with_specific_mandatory_components_versions()
    )
    recipe_query_service_mock.get_recipe.return_value = mock_recipe_object
    recipe_version_query_service_mock.get_recipe_version.return_value = (
        get_test_recipe_version_with_specific_version_name("1.0.0-rc.1")
    )
    parameter_service_mock.get_parameter_value.return_value = get_test_ami_id
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)
    recipe_component_versions = recipe_version_components_versions_value_object.from_list(recipe_component_versions)
    component_ids = [component_version.componentId for component_version in recipe_component_versions.value]
    duplicate_component_ids = list(
        set([component_id for component_id in component_ids if component_ids.count(component_id) > 1])
    )
    update_recipe_version_command_mock.recipeComponentsVersions = recipe_component_versions
    component_version_entities = list()
    for recipe_component_version in update_recipe_version_command_mock.recipeComponentsVersions.value:
        component_version_entity = get_test_component_version_with_specific_status(
            status=component_version.ComponentVersionStatus.Released
        )
        component_version_entity.componentId = recipe_component_version.componentId
        component_version_entity.componentVersionId = recipe_component_version.componentVersionId

        component_version_entities.append(component_version_entity)

    component_version_query_service_mock.get_component_version.side_effect = component_version_entities

    # ACT
    with pytest.raises(DomainException) as e:
        update_recipe_version_command_handler.handle(
            command=update_recipe_version_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_qry_srv=component_version_query_service_mock,
            recipe_version_query_service=recipe_version_query_service_mock,
            recipe_qry_service=recipe_query_service_mock,
            parameter_qry_srv=parameter_service_mock,
            mandatory_components_list_qry_srv=mandatory_components_list_query_service_mock,
            system_configuration_mapping=mock_system_configuration_mapping,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        f"Recipe version contains duplicate components: {sorted(duplicate_component_ids)}."
    )
