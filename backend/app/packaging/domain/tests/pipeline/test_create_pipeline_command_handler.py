from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.packaging.domain.command_handlers.pipeline import create_pipeline_command_handler
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.recipe import recipe_version
from app.packaging.domain.tests.conftest import TEST_BUILD_INSTANCE_TYPES, TEST_DATE, TEST_PRODUCT_ID


@freeze_time(TEST_DATE)
@mock.patch("app.packaging.domain.model.pipeline.pipeline.random.choice", lambda _: "1")
def test_create_pipeline_command_handler_should_create_pipeline_with_product_id(
    generic_repo_mock,
    get_create_pipeline_command,
    get_pipeline_creation_started_event,
    get_pipeline_entity,
    get_test_recipe_version_with_specific_version_name_and_status,
    message_bus_mock,
    recipe_version_query_service_mock,
    recipe_query_service_mock,
    mock_recipe_object,
    pipeline_service_mock,
    uow_mock,
):
    # ARRANGE
    create_pipeline_command = get_create_pipeline_command(product_id=TEST_PRODUCT_ID)
    pipeline_creation_started_event = get_pipeline_creation_started_event(pipeline_id="pipe-11111111")
    pipeline_entity = get_pipeline_entity(pipeline_id="pipe-11111111", product_id=TEST_PRODUCT_ID)
    recipe_version_query_service_mock.get_recipe_version.return_value = (
        get_test_recipe_version_with_specific_version_name_and_status(
            status=recipe_version.RecipeVersionStatus.Released, version_name="1.0.0"
        )
    )
    recipe_query_service_mock.get_recipe.return_value = mock_recipe_object
    pipeline_service_mock.get_pipeline_allowed_build_instance_types.return_value = TEST_BUILD_INSTANCE_TYPES

    # ACT
    create_pipeline_command_handler.handle(
        command=create_pipeline_command,
        message_bus=message_bus_mock,
        recipe_version_qry_srv=recipe_version_query_service_mock,
        recipe_qry_srv=recipe_query_service_mock,
        pipeline_srv=pipeline_service_mock,
        uow=uow_mock,
    )

    # ASSERT
    generic_repo_mock.add.assert_called_with(pipeline_entity)
    message_bus_mock.publish.assert_called_with(pipeline_creation_started_event)
    uow_mock.commit.assert_called()


@freeze_time(TEST_DATE)
@mock.patch("app.packaging.domain.model.pipeline.pipeline.random.choice", lambda _: "1")
def test_create_pipeline_command_handler_should_create_pipeline(
    generic_repo_mock,
    get_create_pipeline_command,
    get_pipeline_creation_started_event,
    get_pipeline_entity,
    get_test_recipe_version_with_specific_version_name_and_status,
    message_bus_mock,
    recipe_version_query_service_mock,
    recipe_query_service_mock,
    mock_recipe_object,
    pipeline_service_mock,
    uow_mock,
):
    # ARRANGE
    create_pipeline_command = get_create_pipeline_command()
    pipeline_creation_started_event = get_pipeline_creation_started_event(pipeline_id="pipe-11111111")
    pipeline_entity = get_pipeline_entity(pipeline_id="pipe-11111111")
    recipe_version_query_service_mock.get_recipe_version.return_value = (
        get_test_recipe_version_with_specific_version_name_and_status(
            status=recipe_version.RecipeVersionStatus.Released, version_name="1.0.0"
        )
    )
    recipe_query_service_mock.get_recipe.return_value = mock_recipe_object
    pipeline_service_mock.get_pipeline_allowed_build_instance_types.return_value = TEST_BUILD_INSTANCE_TYPES

    # ACT
    create_pipeline_command_handler.handle(
        command=create_pipeline_command,
        message_bus=message_bus_mock,
        recipe_version_qry_srv=recipe_version_query_service_mock,
        recipe_qry_srv=recipe_query_service_mock,
        pipeline_srv=pipeline_service_mock,
        uow=uow_mock,
    )

    # ASSERT
    generic_repo_mock.add.assert_called_with(pipeline_entity)
    message_bus_mock.publish.assert_called_with(pipeline_creation_started_event)
    uow_mock.commit.assert_called()


def test_create_pipeline_command_should_raise_an_exception_if_recipe_version_is_not_found(
    get_create_pipeline_command,
    message_bus_mock,
    recipe_version_query_service_mock,
    uow_mock,
    recipe_query_service_mock,
    mock_recipe_object,
    pipeline_service_mock,
):
    # ARRANGE
    create_pipeline_command = get_create_pipeline_command()
    recipe_version_query_service_mock.get_recipe_version.return_value = None
    recipe_query_service_mock.get_recipe.return_value = mock_recipe_object
    pipeline_service_mock.get_pipeline_allowed_build_instance_types.return_value = TEST_BUILD_INSTANCE_TYPES

    # ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        create_pipeline_command_handler.handle(
            command=create_pipeline_command,
            message_bus=message_bus_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
            recipe_qry_srv=recipe_query_service_mock,
            pipeline_srv=pipeline_service_mock,
            uow=uow_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(
        f"No recipe version {create_pipeline_command.recipeVersionId.value} found for {create_pipeline_command.recipeId.value}."
    )


def test_create_pipeline_command_should_raise_an_exception_if_recipe_is_not_found(
    get_create_pipeline_command,
    message_bus_mock,
    recipe_version_query_service_mock,
    uow_mock,
    recipe_query_service_mock,
    mock_recipe_object,
    pipeline_service_mock,
    get_pipeline_creation_started_event,
    get_pipeline_entity,
    get_test_recipe_version_with_specific_version_name_and_status,
):
    # ARRANGE
    create_pipeline_command = get_create_pipeline_command()
    recipe_version_query_service_mock.get_recipe_version.return_value = (
        get_test_recipe_version_with_specific_version_name_and_status(
            status=recipe_version.RecipeVersionStatus.Released, version_name="1.0.0"
        )
    )
    recipe_query_service_mock.get_recipe.return_value = None
    pipeline_service_mock.get_pipeline_allowed_build_instance_types.return_value = TEST_BUILD_INSTANCE_TYPES

    # ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        create_pipeline_command_handler.handle(
            command=create_pipeline_command,
            message_bus=message_bus_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
            recipe_qry_srv=recipe_query_service_mock,
            pipeline_srv=pipeline_service_mock,
            uow=uow_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(f"No recipe {create_pipeline_command.recipeId.value} found.")


def test_create_pipeline_command_should_raise_an_exception_if_allowed_build_types_is_not_found(
    get_create_pipeline_command,
    message_bus_mock,
    recipe_version_query_service_mock,
    uow_mock,
    recipe_query_service_mock,
    mock_recipe_object,
    pipeline_service_mock,
    get_pipeline_creation_started_event,
    get_pipeline_entity,
    get_test_recipe_version_with_specific_version_name_and_status,
):
    # ARRANGE
    create_pipeline_command = get_create_pipeline_command()
    recipe_version_query_service_mock.get_recipe_version.return_value = (
        get_test_recipe_version_with_specific_version_name_and_status(
            status=recipe_version.RecipeVersionStatus.Released, version_name="1.0.0"
        )
    )
    recipe_query_service_mock.get_recipe.return_value = mock_recipe_object
    pipeline_service_mock.get_pipeline_allowed_build_instance_types.return_value = ["c8a.9xlarge"]

    # ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        create_pipeline_command_handler.handle(
            command=create_pipeline_command,
            message_bus=message_bus_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
            recipe_qry_srv=recipe_query_service_mock,
            pipeline_srv=pipeline_service_mock,
            uow=uow_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(
        f"Build instance type {TEST_BUILD_INSTANCE_TYPES[0]} is not allowed for recipe {create_pipeline_command.recipeId.value}."
    )


@pytest.mark.parametrize(
    "status",
    (
        recipe_version.RecipeVersionStatus.Created,
        recipe_version.RecipeVersionStatus.Creating,
        recipe_version.RecipeVersionStatus.Failed,
        recipe_version.RecipeVersionStatus.Retired,
        recipe_version.RecipeVersionStatus.Testing,
        recipe_version.RecipeVersionStatus.Updating,
        recipe_version.RecipeVersionStatus.Validated,
    ),
)
def test_create_pipeline_command_should_raise_an_exception_if_recipe_version_status_is_invalid(
    get_create_pipeline_command,
    get_test_recipe_version_with_specific_version_name_and_status,
    message_bus_mock,
    recipe_version_query_service_mock,
    status,
    uow_mock,
    recipe_query_service_mock,
    mock_recipe_object,
    pipeline_service_mock,
):
    # ARRANGE
    create_pipeline_command = get_create_pipeline_command()
    recipe_version_query_service_mock.get_recipe_version.return_value = (
        get_test_recipe_version_with_specific_version_name_and_status(status=status, version_name="1.0.0")
    )
    recipe_query_service_mock.get_recipe.return_value = mock_recipe_object
    pipeline_service_mock.get_pipeline_allowed_build_instance_types.return_value = TEST_BUILD_INSTANCE_TYPES

    # ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        create_pipeline_command_handler.handle(
            command=create_pipeline_command,
            message_bus=message_bus_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
            recipe_qry_srv=recipe_query_service_mock,
            pipeline_srv=pipeline_service_mock,
            uow=uow_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(
        f"Version {create_pipeline_command.recipeVersionId.value} of recipe "
        f"{create_pipeline_command.recipeId.value} has not been released."
    )


@pytest.mark.parametrize("project_id", (None, ""))
def test_create_pipeline_command_should_raise_an_exception_with_invalid_project_id(
    get_create_pipeline_command,
    project_id,
):
    # ARRANGE & ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        get_create_pipeline_command(project_id=project_id)

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to("Project ID cannot be empty.")


@pytest.mark.parametrize(
    "build_instance_types,exception_message",
    (
        (None, "Pipeline build instance types cannot be empty."),
        (list(), "Pipeline build instance types cannot be empty."),
        ([None], "Build instance type value cannot be empty."),
        ([""], "Build instance type value cannot be empty."),
    ),
)
def test_create_pipeline_command_should_raise_an_exception_with_invalid_build_instance_types(
    build_instance_types,
    exception_message,
    get_create_pipeline_command,
):
    # ARRANGE & ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        get_create_pipeline_command(build_instance_types=build_instance_types)

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(exception_message)


@pytest.mark.parametrize("pipeline_description", (None, "", "1" * 1025))
def test_create_pipeline_command_should_raise_an_exception_with_invalid_pipeline_description(
    get_create_pipeline_command,
    pipeline_description,
):
    # ARRANGE & ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        get_create_pipeline_command(pipeline_description=pipeline_description)

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(
        "Pipeline description should be between 1 and 1024 characters."
    )


@pytest.mark.parametrize("pipeline_name", (None, "", "1" * 129))
def test_create_pipeline_command_should_raise_an_exception_with_invalid_pipeline_name(
    get_create_pipeline_command,
    pipeline_name,
):
    # ARRANGE & ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        get_create_pipeline_command(pipeline_name=pipeline_name)

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(
        "Pipeline name should match ^[-_A-Za-z-0-9][-_A-Za-z0-9 ]{1,126}[-_A-Za-z-0-9]$ pattern."
    )


@pytest.mark.parametrize(
    "exception_message,pipeline_schedule",
    (
        ("Pipeline schedule cannot be empty.", None),
        ("Pipeline schedule cannot be empty.", ""),
        ("Pipeline schedule must contain exactly 6 fields.", "*"),
        ("Pipeline schedule must contain exactly 6 fields.", "* *"),
        ("Invalid combination of day-of-month and day-of-week - One must be a ?.", "0 10 1 * 1 *"),
        ("Field minute doesn't match the required cron pattern.", "60 10 * * ? *"),
        ("Field minute doesn't match the required cron pattern.", "a 10 * * ? *"),
        ("Field hour doesn't match the required cron pattern.", "0 24 * * ? *"),
        ("Field hour doesn't match the required cron pattern.", "0 a * * ? *"),
        ("Field day-of-month doesn't match the required cron pattern.", "0 10 0 * ? *"),
        ("Field day-of-month doesn't match the required cron pattern.", "0 10 32 * ? *"),
        ("Field day-of-month doesn't match the required cron pattern.", "0 10 a * ? *"),
        ("Field month doesn't match the required cron pattern.", "0 10 * 0 ? *"),
        ("Field month doesn't match the required cron pattern.", "0 10 * 13 ? *"),
        ("Field month doesn't match the required cron pattern.", "0 10 * a ? *"),
        ("Field day-of-week doesn't match the required cron pattern.", "0 10 ? * 0 *"),
        ("Field day-of-week doesn't match the required cron pattern.", "0 10 ? * 8 *"),
        ("Field day-of-week doesn't match the required cron pattern.", "0 10 ? * a *"),
        ("Field year doesn't match the required cron pattern.", "0 10 * * ? 1969"),
        ("Field year doesn't match the required cron pattern.", "0 10 * * ? 2200"),
        ("Field year doesn't match the required cron pattern.", "0 10 * * ? a"),
    ),
)
def test_create_pipeline_command_should_raise_an_exception_with_invalid_pipeline_schedule(
    exception_message,
    get_create_pipeline_command,
    pipeline_schedule,
):
    # ARRANGE & ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        get_create_pipeline_command(pipeline_schedule=pipeline_schedule)

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(exception_message)
