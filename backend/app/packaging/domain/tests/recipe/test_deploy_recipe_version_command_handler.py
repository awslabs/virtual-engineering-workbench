import logging
import random
from unittest import mock

import assertpy
import pytest
import semver
import yaml
from freezegun import freeze_time

from app.packaging.domain.command_handlers.recipe import deploy_recipe_version_command_handler
from app.packaging.domain.events.recipe import recipe_version_published
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.recipe import recipe_version


@pytest.mark.parametrize(
    "recipe_version_value",
    (("2.1.0-rc.1"), ("2.1.0-rc.2"), ("2.2.0-rc.1")),
)
@freeze_time("2024-01-11")
def test_handle_should_deploy_version(
    recipe_version_service_mock,
    recipe_query_service_mock,
    deploy_recipe_version_command_mock,
    message_bus_mock,
    component_version_query_service_mock,
    component_version_service_mock,
    component_version_definition_service_mock,
    uow_mock,
    recipe_version_value,
    return_component_version,
    recipe_version_repo_mock,
):
    # ARRANGE
    command = deploy_recipe_version_command_mock(recipe_version_value)

    sorted_components = sorted(command.components.value, key=lambda x: x.order)
    component_version_query_service_mock.get_component_version.side_effect = [
        return_component_version(componentId=item.componentId, componentVersionId=item.componentVersionId)
        for item in sorted_components
    ]
    repos_dict = {recipe_version.RecipeVersion: recipe_version_repo_mock}
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)
    recipe_version_service_mock.create.return_value = f"arn:aws:imagebuilder:us-east-1:123456789012:image-recipe/{command.recipeId.value}/{str(semver.Version.parse(command.recipeVersionName.value).finalize_version())}"
    component_version_service_mock.create.return_value = f"arn:aws:imagebuilder:us-east-1:123456789012:component/{command.recipeId.value}/{str(semver.Version.parse(command.recipeVersionName.value).finalize_version())}"
    # ACT
    deploy_recipe_version_command_handler.handle(
        command=command,
        uow=uow_mock,
        message_bus=message_bus_mock,
        recipe_version_service=recipe_version_service_mock,
        recipe_query_service=recipe_query_service_mock,
        component_version_query_service=component_version_query_service_mock,
        component_version_service=component_version_service_mock,
        recipe_component_definition_service=component_version_definition_service_mock,
        logger=mock.create_autospec(spec=logging.Logger),
    )

    # ASSERT
    message_bus_mock.publish.assert_called_once_with(
        recipe_version_published.RecipeVersionPublished(
            projectId=command.projectId.value,
            recipe_id=command.recipeId.value,
            recipe_version_id=command.recipeVersionId.value,
        )
    )
    recipe_version_service_mock.get_build_arn.assert_called_once_with(
        name=command.recipeId.value,
        version=str(semver.Version.parse(command.recipeVersionName.value).finalize_version()),
    )
    recipe_version_repo_mock.update_attributes.assert_called_once_with(
        recipe_version.RecipeVersionPrimaryKey(
            recipeId=command.recipeId.value, recipeVersionId=command.recipeVersionId.value
        ),
        status=recipe_version.RecipeVersionStatus.Created,
        recipeVersionComponentArn=f"arn:aws:imagebuilder:us-east-1:123456789012:component/{command.recipeId.value}/{str(semver.Version.parse(command.recipeVersionName.value).finalize_version())}",
        recipeVersionArn=f"arn:aws:imagebuilder:us-east-1:123456789012:image-recipe/{command.recipeId.value}/{str(semver.Version.parse(command.recipeVersionName.value).finalize_version())}",
    )
    uow_mock.commit.assert_called_once()


@pytest.mark.parametrize(
    "recipe_version_value",
    (("2.1.0-rc.1"), ("2.1.0-rc.2"), ("2.2.0-rc.1")),
)
@freeze_time("2024-01-11")
def test_handle_should_create_nested_component(
    recipe_version_service_mock,
    deploy_recipe_version_command_mock,
    component_version_query_service_mock,
    component_version_service_mock,
    component_version_definition_service_mock,
    uow_mock,
    recipe_version_value,
    return_component_version,
    recipe_version_repo_mock,
    mock_recipe_object,
    mock_recipe_version_object,
):
    # ARRANGE
    command = deploy_recipe_version_command_mock(recipe_version_value)

    sorted_components = sorted(command.components.value, key=lambda x: x.order)
    component_version_query_service_mock.get_component_version.side_effect = [
        return_component_version(componentId=item.componentId, componentVersionId=item.componentVersionId)
        for item in sorted_components
    ]
    repos_dict = {recipe_version.RecipeVersion: recipe_version_repo_mock}
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)

    # ACT
    recipe_component_arns = deploy_recipe_version_command_handler.__create_recipe_component_list(
        component_version_query_service=component_version_query_service_mock,
        components=command.components,
        component_version_service=component_version_service_mock,
        recipe_component_definition_service=component_version_definition_service_mock,
        recipe_entity=mock_recipe_object,
        recipe_component_version_name=command.recipeVersionName.value,
        recipe_version_build_arn=None,
    )
    recipe_version_build_arn = recipe_version_service_mock.create(
        name=command.recipeId.value,
        version=str(semver.Version.parse(command.recipeVersionName.value).finalize_version()),
        component_arns=recipe_component_arns,
        parent_image=mock_recipe_version_object.parentImageUpstreamId,
        volume_size=mock_recipe_version_object.recipeVersionVolumeSize,
        description=mock_recipe_object.recipeDescription,
    )

    # ASSERT
    assertpy.assert_that(recipe_version_build_arn).is_not_none()


@pytest.mark.parametrize(
    "recipe_version_value, component_ids",
    (
        ("2.1.0-rc.1", ["comp-1234abc", "comp-2345cde", None]),
        ("1.1.0-rc.1", ["comp-234fgd", "comp-2345cde", None]),
    ),
)
@freeze_time("2024-01-11")
def test_handle_should_not_deploy_when_one_of_the_component_is_not_available(
    recipe_version_service_mock,
    recipe_query_service_mock,
    deploy_recipe_version_command_mock,
    message_bus_mock,
    component_version_query_service_mock,
    component_version_service_mock,
    component_version_definition_service_mock,
    return_component_version,
    recipe_version_value,
    component_ids,
    uow_mock,
):
    # ARRANGE
    command = deploy_recipe_version_command_mock(recipe_version_value)
    sorted_components = sorted(command.components.value, key=lambda x: x.order)
    component_version_query_service_mock.get_component_version.side_effect = [
        return_component_version(componentId=component_ids[index], componentVersionId=item.componentVersionId)
        for index, item in enumerate(sorted_components)
    ]

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        deploy_recipe_version_command_handler.handle(
            command=command,
            uow=uow_mock,
            message_bus=message_bus_mock,
            recipe_version_service=recipe_version_service_mock,
            recipe_query_service=recipe_query_service_mock,
            component_version_query_service=component_version_query_service_mock,
            component_version_service=component_version_service_mock,
            recipe_component_definition_service=component_version_definition_service_mock,
            logger=mock.create_autospec(spec=logging.Logger),
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to("Failed to create recipe component list.")


@pytest.mark.parametrize(
    "recipe_version_value",
    (("2.1.0"), ("1.0.1"), ("1.0.0")),
)
@freeze_time("2024-01-11")
def test_handle_should_not_deploy_when_recipe_is_already_generally_available(
    recipe_version_service_mock,
    recipe_query_service_mock,
    deploy_recipe_version_command_mock,
    message_bus_mock,
    component_version_query_service_mock,
    component_version_service_mock,
    mock_recipe_object,
    recipe_version_value,
    component_version_definition_service_mock,
    return_component_version,
    uow_mock,
):
    # ARRANGE
    command = deploy_recipe_version_command_mock(recipe_version_value)
    sorted_components = sorted(command.components.value, key=lambda x: x.order)
    component_version_query_service_mock.get_component_version.side_effect = [
        return_component_version(componentId=item.componentId, componentVersionId=item.componentVersionId)
        for item in sorted_components
    ]

    recipe_query_service_mock.get_recipe.return_value = mock_recipe_object
    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        deploy_recipe_version_command_handler.handle(
            command=command,
            uow=uow_mock,
            message_bus=message_bus_mock,
            recipe_version_service=recipe_version_service_mock,
            recipe_query_service=recipe_query_service_mock,
            component_version_query_service=component_version_query_service_mock,
            component_version_service=component_version_service_mock,
            recipe_component_definition_service=component_version_definition_service_mock,
            logger=mock.create_autospec(spec=logging.Logger),
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        f"Recipe version {command.recipeVersionName.value} of {mock_recipe_object.recipeId} already exists."
    )
    assertpy.assert_that(recipe_version_service_mock.create.call_count).is_equal_to(0)


@pytest.mark.parametrize(
    "recipe_version_value",
    (
        ("2.1.0-rc.2"),
        ("1.1.0-rc.2"),
    ),
)
@freeze_time("2024-01-11")
def test_generated_template_is_valid(
    deploy_recipe_version_command_mock,
    recipe_version_value,
    return_component_version,
):
    # ARRANGE
    command = deploy_recipe_version_command_mock(recipe_version_value)
    sorted_components = sorted(command.components.value, key=lambda x: x.order)
    component_data = [
        return_component_version(
            componentId=item.componentId, componentVersionId=item.componentVersionId
        ).componentBuildVersionArn
        for item in sorted_components
    ]

    expected_yaml_template = """
    schemaVersion: 1.0
    phases:
      - name: build
        steps:
          - name: ExecuteNestedDocument
            action: ExecuteDocument
            loop:
              name: recipeLoop
              forEach:
                - arn:aws:imagebuilder:us-east-1:123456789012:component/comp2-1234abc/1.0.2/1
                - arn:aws:imagebuilder:us-east-1:123456789012:component/comp-8675abc/1.0.2/1
                - arn:aws:imagebuilder:us-east-1:123456789012:component/comp3-9867dfg/1.0.2/1
            inputs:
              document: "{{ recipeLoop.value }}"
              phases: build
      - name: validate
        steps:
          - name: ExecuteNestedDocument
            action: ExecuteDocument
            loop:
              name: recipeLoop
              forEach:
                - arn:aws:imagebuilder:us-east-1:123456789012:component/comp2-1234abc/1.0.2/1
                - arn:aws:imagebuilder:us-east-1:123456789012:component/comp-8675abc/1.0.2/1
                - arn:aws:imagebuilder:us-east-1:123456789012:component/comp3-9867dfg/1.0.2/1
            inputs:
              document: "{{ recipeLoop.value }}"
              phases: validate
      - name: test
        steps:
          - name: ExecuteNestedDocument
            action: ExecuteDocument
            loop:
              name: recipeLoop
              forEach:
                - arn:aws:imagebuilder:us-east-1:123456789012:component/comp2-1234abc/1.0.2/1
                - arn:aws:imagebuilder:us-east-1:123456789012:component/comp-8675abc/1.0.2/1
                - arn:aws:imagebuilder:us-east-1:123456789012:component/comp3-9867dfg/1.0.2/1
            inputs:
              document: "{{ recipeLoop.value }}"
              phases: test
    """

    # ACT
    rendered_data = yaml.safe_load(
        deploy_recipe_version_command_handler.__generate_nested_component_definition(component_data)
    )
    # ASSERT
    assert rendered_data == yaml.safe_load(expected_yaml_template)


@pytest.mark.parametrize(
    "recipe_version_value",
    (("2.1.0-rc.1"), ("2.1.0-rc.2"), ("2.2.0-rc.1")),
)
@freeze_time("2024-01-11")
def test_should_fail_when_recipe_does_not_exist(
    recipe_version_service_mock,
    recipe_query_service_mock,
    deploy_recipe_version_command_mock,
    message_bus_mock,
    component_version_query_service_mock,
    component_version_service_mock,
    component_version_definition_service_mock,
    uow_mock,
    recipe_version_value,
    return_component_version,
    recipe_version_repo_mock,
):
    # ARRANGE
    command = deploy_recipe_version_command_mock(recipe_version_value)
    recipe_query_service_mock.get_recipe.return_value = None
    sorted_components = sorted(command.components.value, key=lambda x: x.order)
    component_version_query_service_mock.get_component_version.side_effect = [
        return_component_version(componentId=item.componentId, componentVersionId=item.componentVersionId)
        for item in sorted_components
    ]
    repos_dict = {recipe_version.RecipeVersion: recipe_version_repo_mock}
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        deploy_recipe_version_command_handler.handle(
            command=command,
            uow=uow_mock,
            message_bus=message_bus_mock,
            recipe_version_service=recipe_version_service_mock,
            recipe_query_service=recipe_query_service_mock,
            component_version_query_service=component_version_query_service_mock,
            component_version_service=component_version_service_mock,
            recipe_component_definition_service=component_version_definition_service_mock,
            logger=mock.create_autospec(spec=logging.Logger),
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(f"Recipe {command.recipeId.value} can not be found.")


@pytest.mark.parametrize(
    "recipe_version_value",
    (
        ("2.1.0-rc.2"),
        ("1.1.0-rc.2"),
    ),
)
@freeze_time("2024-01-11")
def test_should_fail_when_yaml_definition_for_nested_component_failed_to_generate(
    deploy_recipe_version_command_mock,
    recipe_version_value,
    return_component_version,
):
    # ARRANGE
    command = deploy_recipe_version_command_mock(recipe_version_value)
    sorted_components = sorted(command.components.value, key=lambda x: x.order)
    component_data = [
        return_component_version(
            componentId=item.componentId, componentVersionId=item.componentVersionId
        ).componentBuildVersionArn
        for item in sorted_components
    ]
    # intentionally making an element at random as none to simulate something went wrong
    index_to_make_none = random.randint(0, len(component_data) - 1)
    component_data[index_to_make_none] = None

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        yaml.safe_load(deploy_recipe_version_command_handler.__generate_nested_component_definition(component_data))

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to("Component ARN can not be None.")


@pytest.mark.parametrize(
    "recipe_version_value",
    (("2.1.0-rc2"), ("0.0.0-rc.2"), ("-1.0.1"), ("0.0.0-rc.1"), ("1.1.1-rc.alpha")),
)
@freeze_time("2024-01-11")
def test_should_fail_when_recipe_version_name_is_invalid(
    deploy_recipe_version_command_mock,
    recipe_version_value,
):
    # ARRANGE
    with pytest.raises(domain_exception.DomainException) as e:
        deploy_recipe_version_command_mock(recipe_version_value)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(f"Invalid recipe version name: {recipe_version_value}.")
