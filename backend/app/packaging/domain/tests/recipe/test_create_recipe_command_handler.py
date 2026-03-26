from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.packaging.domain.command_handlers.recipe.create_recipe_command_handler import (
    handle,
)
from app.packaging.domain.commands.recipe.create_recipe_command import (
    CreateRecipeCommand,
)
from app.packaging.domain.exceptions.domain_exception import DomainException
from app.packaging.domain.model.recipe import recipe
from app.packaging.domain.value_objects.recipe import (
    recipe_description_value_object,
    recipe_id_value_object,
    recipe_name_value_object,
    recipe_system_configuration_value_object,
)
from app.packaging.domain.value_objects.shared import (
    project_id_value_object,
    user_id_value_object,
)


@freeze_time("2023-10-13T00:00:00+00:00")
def create_recipe_command_recipe_platform_fail_mock() -> CreateRecipeCommand:
    return CreateRecipeCommand(
        projectId=project_id_value_object.from_str("proj-12345"),
        recipeId=recipe_id_value_object.from_str("reci-12345abc"),
        recipeName=recipe_name_value_object.from_str("proserve-autosar-recipe"),
        recipeDescription=recipe_description_value_object.from_str("This is a recipe for validation"),
        recipeSystemConfiguration=recipe_system_configuration_value_object.from_attrs(
            platform="LINUX",
            architecture="amd64",
            os_version="Ubuntu 24",
        ),
        createdBy=user_id_value_object.from_str("T998765"),
        createDate="2023-10-13T00:00:00+00:00",
    )


@freeze_time("2023-10-13T00:00:00+00:00")
def create_recipe_command_architecture_fail_mock() -> CreateRecipeCommand:
    return CreateRecipeCommand(
        projectId=project_id_value_object.from_str("proj-12345"),
        recipeId=recipe_id_value_object.from_str("reci-12345abc"),
        recipeName=recipe_name_value_object.from_str("proserve-autosar-recipe"),
        recipeDescription=recipe_description_value_object.from_str("This is a recipe for validation"),
        recipeSystemConfiguration=recipe_system_configuration_value_object.from_attrs(
            platform="Linux",
            architecture="RISC-V",
            os_version="Ubuntu 24",
        ),
        createdBy=user_id_value_object.from_str("T998765"),
        createDate="2023-10-13T00:00:00+00:00",
    )


@freeze_time("2023-10-13T00:00:00+00:00")
def create_recipe_command_recipe_os_version_fail_mock() -> CreateRecipeCommand:
    return CreateRecipeCommand(
        projectId=project_id_value_object.from_str("proj-12345"),
        recipeId=recipe_id_value_object.from_str("reci-12345abc"),
        recipeName=recipe_name_value_object.from_str("proserve-autosar-recipe"),
        recipeDescription=recipe_description_value_object.from_str("This is a recipe for validation"),
        recipeSystemConfiguration=recipe_system_configuration_value_object.from_attrs(
            platform="Linux",
            architecture="amd64",
            os_version="Ubuntu 26",
        ),
        createdBy=user_id_value_object.from_str("T998765"),
        createDate="2023-10-13T00:00:00+00:00",
    )


@freeze_time("2023-10-13T00:00:00+00:00")
def create_recipe_command_recipe_incompatible_platform_architecture_fail_mock() -> CreateRecipeCommand:
    return CreateRecipeCommand(
        projectId=project_id_value_object.from_str("proj-12345"),
        recipeId=recipe_id_value_object.from_str("reci-12345abc"),
        recipeName=recipe_name_value_object.from_str("proserve-autosar-recipe"),
        recipeDescription=recipe_description_value_object.from_str("This is a recipe for validation"),
        recipeSystemConfiguration=recipe_system_configuration_value_object.from_attrs(
            platform="Windows",
            architecture="arm64",
            os_version="Microsoft Windows Server 2025",
        ),
        createdBy=user_id_value_object.from_str("T998765"),
        createDate="2023-10-13T00:00:00+00:00",
    )


@freeze_time("2023-10-13T00:00:00+00:00")
def create_recipe_command_recipe_incompatible_platform_os_version_fail_mock() -> CreateRecipeCommand:
    return CreateRecipeCommand(
        projectId=project_id_value_object.from_str("proj-12345"),
        recipeId=recipe_id_value_object.from_str("reci-12345abc"),
        recipeName=recipe_name_value_object.from_str("proserve-autosar-recipe"),
        recipeDescription=recipe_description_value_object.from_str("This is a recipe for validation"),
        recipeSystemConfiguration=recipe_system_configuration_value_object.from_attrs(
            platform="Windows",
            architecture="amd64",
            os_version="Ubuntu 24",
        ),
        createdBy=user_id_value_object.from_str("T998765"),
        createDate="2023-10-13T00:00:00+00:00",
    )


def test_create_command_recipe_should_raise_exception_with_invalid_platform():
    # ARRANGE & ACT
    with pytest.raises(DomainException) as exec_info:
        create_recipe_command_recipe_platform_fail_mock()

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(
        f"Recipe platform should be in {recipe.RecipePlatform.list()}."
    )


def test_create_command_recipe_should_raise_exception_with_invalid_architecture():
    # ARRANGE & ACT
    with pytest.raises(DomainException) as exec_info:
        create_recipe_command_architecture_fail_mock()

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(
        f"Recipe architecture should be in {recipe.RecipeArchitecture.list()}."
    )


def test_create_command_recipe_should_raise_exception_with_invalid_os_version():
    # ARRANGE & ACT
    with pytest.raises(DomainException) as exec_info:
        create_recipe_command_recipe_os_version_fail_mock()

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(
        f"Recipe OS version should be in {recipe.RecipeOsVersion.list()}."
    )


@freeze_time("2023-10-13T00:00:00+00:00")
def test_create_recipe_should_raise_exception_with_incompatible_platform_architectures():
    # ARRANGE & ACT
    with pytest.raises(DomainException) as exec_info:
        create_recipe_command_recipe_incompatible_platform_architecture_fail_mock()
    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(
        "Recipe platform Windows does not support arm64 architecture."
    )


@freeze_time("2023-10-13T00:00:00+00:00")
def test_create_recipe_should_raise_exception_with_incompatible_platform_os_versions():
    # ARRANGE & ACT
    with pytest.raises(DomainException) as exec_info:
        create_recipe_command_recipe_incompatible_platform_os_version_fail_mock()

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(
        "Recipe platform Windows does not support Linux OS versions."
    )


@pytest.fixture()
@freeze_time("2023-10-13T00:00:00+00:00")
def create_recipe_command_mock() -> CreateRecipeCommand:
    return CreateRecipeCommand(
        projectId=project_id_value_object.from_str("proj-12345"),
        recipeId=recipe_id_value_object.from_str("reci-12345"),
        recipeName=recipe_name_value_object.from_str("proserve-autosar-recipe"),
        recipeDescription=recipe_description_value_object.from_str("This is a recipe for validation"),
        recipeSystemConfiguration=recipe_system_configuration_value_object.from_attrs(
            platform="Linux",
            architecture="amd64",
            os_version="Ubuntu 24",
        ),
        createdBy=user_id_value_object.from_str("T998765"),
        createDate="2023-10-13T00:00:00+00:00",
    )


@pytest.fixture()
def mock_recipe_object() -> recipe.Recipe:
    return recipe.Recipe(
        projectId="proj-12345",
        recipeId="reci-11111111",
        recipeName="proserve-autosar-recipe",
        recipeDescription="This is a recipe for validation",
        recipePlatform="Linux",
        recipeArchitecture="amd64",
        recipeOsVersion="Ubuntu 24",
        status=recipe.RecipeStatus.Created,
        createdBy="T998765",
        createDate="2023-10-13T00:00:00+00:00",
        lastUpdatedBy="T998765",
        lastUpdateDate="2023-10-13T00:00:00+00:00",
    )


@mock.patch("app.packaging.domain.model.recipe.recipe.random.choice", lambda chars: "1")
@freeze_time("2023-10-13T00:00:00+00:00")
def test_create_recipe_should_create_new_recipe(
    create_recipe_command_mock, mock_recipe_object, generic_repo_mock, uow_mock
):
    # ARRANGE & ACT
    handle(create_recipe_command_mock, uow=uow_mock)

    # ASSERT
    generic_repo_mock.add.assert_called_with(mock_recipe_object)
    uow_mock.commit.assert_called()
