import pytest
from assertpy import assertpy
from freezegun import freeze_time

from app.packaging.domain.command_handlers.pipeline import update_pipeline_command_handler
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.pipeline import pipeline
from app.packaging.domain.model.recipe import recipe_version
from app.packaging.domain.tests.conftest import TEST_BUILD_INSTANCE_TYPES, TEST_DATE, TEST_PRODUCT_ID, TEST_USER_ID
from app.packaging.domain.value_objects.pipeline import pipeline_build_instance_types_value_object


@freeze_time(TEST_DATE)
def test_update_pipeline_command_handler_should_create_pipeline(
    generic_repo_mock,
    get_update_pipeline_command,
    get_pipeline_update_started_event,
    get_pipeline_entity,
    get_test_recipe_version_with_specific_version_name_and_status,
    message_bus_mock,
    recipe_version_query_service_mock,
    pipeline_query_service_mock,
    get_test_pipeline_schedule,
    get_test_build_instance_types,
    get_test_recipe_version_id,
    uow_mock,
    mock_recipe_object,
    recipe_query_service_mock,
    pipeline_service_mock,
):
    # ARRANGE
    update_pipeline_command = get_update_pipeline_command(
        pipeline_schedule=get_test_pipeline_schedule,
        build_instance_types=get_test_build_instance_types,
        recipe_version_id=get_test_recipe_version_id,
    )
    pipeline_update_started_event = get_pipeline_update_started_event(pipeline_id="pipe-11111111")
    pipeline_entity = get_pipeline_entity(pipeline_id="pipe-11111111")
    pipeline_entity.status = pipeline.PipelineStatus.Created
    recipe_version_entity = get_test_recipe_version_with_specific_version_name_and_status(
        status=recipe_version.RecipeVersionStatus.Released, version_name="1.1.0"
    )
    pipeline_query_service_mock.get_pipeline.side_effect = [pipeline_entity]
    recipe_version_query_service_mock.get_recipe_version.return_value = recipe_version_entity
    recipe_query_service_mock.get_recipe.return_value = mock_recipe_object
    pipeline_service_mock.get_pipeline_allowed_build_instance_types.return_value = TEST_BUILD_INSTANCE_TYPES

    # ACT
    update_pipeline_command_handler.handle(
        command=update_pipeline_command,
        message_bus=message_bus_mock,
        recipe_version_qry_srv=recipe_version_query_service_mock,
        pipeline_qry_srv=pipeline_query_service_mock,
        recipe_qry_srv=recipe_query_service_mock,
        pipeline_srv=pipeline_service_mock,
        uow=uow_mock,
    )

    # ASSERT
    generic_repo_mock.update_attributes.assert_called_with(
        pipeline.PipelinePrimaryKey(
            pipelineId=pipeline_entity.pipelineId,
            projectId=pipeline_entity.projectId,
        ),
        recipeVersionId=recipe_version_entity.recipeVersionId,
        recipeVersionName="1.1.0",
        buildInstanceTypes=update_pipeline_command.buildInstanceTypes.value,
        pipelineSchedule=update_pipeline_command.pipelineSchedule.value,
        lastUpdateDate=TEST_DATE,
        lastUpdatedBy=TEST_USER_ID,
        status=pipeline.PipelineStatus.Updating,
        productId=None,
    )
    message_bus_mock.publish.assert_called_with(pipeline_update_started_event)
    uow_mock.commit.assert_called()


@freeze_time(TEST_DATE)
def test_update_pipeline_command_handler_should_create_pipeline_with_pipeline_schedule_only(
    generic_repo_mock,
    get_update_pipeline_command,
    get_pipeline_update_started_event,
    get_pipeline_entity,
    get_test_recipe_version_with_specific_version_name_and_status,
    message_bus_mock,
    recipe_version_query_service_mock,
    pipeline_query_service_mock,
    get_test_pipeline_schedule,
    uow_mock,
    recipe_query_service_mock,
    mock_recipe_object,
    pipeline_service_mock,
):
    # ARRANGE
    update_pipeline_command = get_update_pipeline_command(pipeline_schedule=get_test_pipeline_schedule)
    update_pipeline_command.buildInstanceTypes = None
    pipeline_update_started_event = get_pipeline_update_started_event(pipeline_id="pipe-11111111")
    pipeline_entity = get_pipeline_entity(pipeline_id="pipe-11111111")
    pipeline_entity.status = pipeline.PipelineStatus.Created
    recipe_version_entity = get_test_recipe_version_with_specific_version_name_and_status(
        status=recipe_version.RecipeVersionStatus.Released, version_name="1.1.0"
    )
    pipeline_query_service_mock.get_pipeline.side_effect = [pipeline_entity]
    recipe_version_query_service_mock.get_recipe_version.return_value = recipe_version_entity
    recipe_query_service_mock.get_recipe.return_value = mock_recipe_object
    pipeline_service_mock.get_pipeline_allowed_build_instance_types.return_value = TEST_BUILD_INSTANCE_TYPES

    # ACT
    update_pipeline_command_handler.handle(
        command=update_pipeline_command,
        message_bus=message_bus_mock,
        recipe_version_qry_srv=recipe_version_query_service_mock,
        pipeline_qry_srv=pipeline_query_service_mock,
        recipe_qry_srv=recipe_query_service_mock,
        pipeline_srv=pipeline_service_mock,
        uow=uow_mock,
    )

    # ASSERT
    generic_repo_mock.update_attributes.assert_called_with(
        pipeline.PipelinePrimaryKey(
            pipelineId=pipeline_entity.pipelineId,
            projectId=pipeline_entity.projectId,
        ),
        pipelineSchedule=update_pipeline_command.pipelineSchedule.value,
        lastUpdateDate=TEST_DATE,
        lastUpdatedBy=TEST_USER_ID,
        status=pipeline.PipelineStatus.Updating,
        productId=None,
    )
    message_bus_mock.publish.assert_called_with(pipeline_update_started_event)
    uow_mock.commit.assert_called()


@freeze_time(TEST_DATE)
def test_update_pipeline_command_handler_should_create_pipeline_with_build_instance_types_only(
    generic_repo_mock,
    get_update_pipeline_command,
    get_pipeline_update_started_event,
    get_pipeline_entity,
    get_test_recipe_version_with_specific_version_name_and_status,
    message_bus_mock,
    recipe_version_query_service_mock,
    pipeline_query_service_mock,
    get_test_build_instance_types,
    uow_mock,
    recipe_query_service_mock,
    mock_recipe_object,
    pipeline_service_mock,
):
    # ARRANGE
    update_pipeline_command = get_update_pipeline_command(build_instance_types=get_test_build_instance_types)
    update_pipeline_command.pipelineSchedule = None
    pipeline_update_started_event = get_pipeline_update_started_event(pipeline_id="pipe-11111111")
    pipeline_entity = get_pipeline_entity(pipeline_id="pipe-11111111")
    pipeline_entity.status = pipeline.PipelineStatus.Created
    recipe_version_entity = get_test_recipe_version_with_specific_version_name_and_status(
        status=recipe_version.RecipeVersionStatus.Released, version_name="1.1.0"
    )
    pipeline_query_service_mock.get_pipeline.side_effect = [pipeline_entity]
    recipe_version_query_service_mock.get_recipe_version.return_value = recipe_version_entity
    recipe_query_service_mock.get_recipe.return_value = mock_recipe_object
    pipeline_service_mock.get_pipeline_allowed_build_instance_types.return_value = TEST_BUILD_INSTANCE_TYPES

    # ACT
    update_pipeline_command_handler.handle(
        command=update_pipeline_command,
        message_bus=message_bus_mock,
        recipe_version_qry_srv=recipe_version_query_service_mock,
        pipeline_qry_srv=pipeline_query_service_mock,
        recipe_qry_srv=recipe_query_service_mock,
        pipeline_srv=pipeline_service_mock,
        uow=uow_mock,
    )

    # ASSERT
    generic_repo_mock.update_attributes.assert_called_with(
        pipeline.PipelinePrimaryKey(
            pipelineId=pipeline_entity.pipelineId,
            projectId=pipeline_entity.projectId,
        ),
        buildInstanceTypes=update_pipeline_command.buildInstanceTypes.value,
        lastUpdateDate=TEST_DATE,
        lastUpdatedBy=TEST_USER_ID,
        status=pipeline.PipelineStatus.Updating,
        productId=None,
    )
    message_bus_mock.publish.assert_called_with(pipeline_update_started_event)
    uow_mock.commit.assert_called()


@freeze_time(TEST_DATE)
def test_update_pipeline_command_handler_should_create_pipeline_with_recipe_version_id_only(
    generic_repo_mock,
    get_update_pipeline_command,
    get_pipeline_update_started_event,
    get_pipeline_entity,
    get_test_recipe_version_with_specific_version_name_and_status,
    message_bus_mock,
    recipe_version_query_service_mock,
    pipeline_query_service_mock,
    get_test_recipe_version_id,
    uow_mock,
    recipe_query_service_mock,
    mock_recipe_object,
    pipeline_service_mock,
):
    # ARRANGE
    update_pipeline_command = get_update_pipeline_command(recipe_version_id=get_test_recipe_version_id)
    update_pipeline_command.pipelineSchedule = None
    pipeline_update_started_event = get_pipeline_update_started_event(pipeline_id="pipe-11111111")
    pipeline_entity = get_pipeline_entity(pipeline_id="pipe-11111111")
    pipeline_entity.status = pipeline.PipelineStatus.Created
    recipe_version_entity = get_test_recipe_version_with_specific_version_name_and_status(
        status=recipe_version.RecipeVersionStatus.Released, version_name="1.1.0"
    )
    pipeline_query_service_mock.get_pipeline.side_effect = [pipeline_entity]
    recipe_version_query_service_mock.get_recipe_version.return_value = recipe_version_entity
    recipe_query_service_mock.get_recipe.return_value = mock_recipe_object
    pipeline_service_mock.get_pipeline_allowed_build_instance_types.return_value = TEST_BUILD_INSTANCE_TYPES

    # ACT
    update_pipeline_command_handler.handle(
        command=update_pipeline_command,
        message_bus=message_bus_mock,
        recipe_version_qry_srv=recipe_version_query_service_mock,
        pipeline_qry_srv=pipeline_query_service_mock,
        recipe_qry_srv=recipe_query_service_mock,
        pipeline_srv=pipeline_service_mock,
        uow=uow_mock,
    )

    # ASSERT
    generic_repo_mock.update_attributes.assert_called_with(
        pipeline.PipelinePrimaryKey(
            pipelineId=pipeline_entity.pipelineId,
            projectId=pipeline_entity.projectId,
        ),
        recipeVersionId=update_pipeline_command.recipeVersionId.value,
        recipeVersionName="1.1.0",
        lastUpdateDate=TEST_DATE,
        lastUpdatedBy=TEST_USER_ID,
        status=pipeline.PipelineStatus.Updating,
        productId=None,
    )
    message_bus_mock.publish.assert_called_with(pipeline_update_started_event)
    uow_mock.commit.assert_called()


@freeze_time(TEST_DATE)
def test_update_pipeline_command_handler_should_update_pipeline_with_product_id_only(
    generic_repo_mock,
    get_update_pipeline_command,
    get_pipeline_update_started_event,
    get_pipeline_entity,
    get_test_recipe_version_with_specific_version_name_and_status,
    message_bus_mock,
    recipe_version_query_service_mock,
    pipeline_query_service_mock,
    uow_mock,
    recipe_query_service_mock,
    mock_recipe_object,
    pipeline_service_mock,
):
    # ARRANGE
    update_pipeline_command = get_update_pipeline_command(product_id=TEST_PRODUCT_ID)
    update_pipeline_command.pipelineSchedule = None
    pipeline_update_started_event = get_pipeline_update_started_event(pipeline_id="pipe-11111111")
    pipeline_entity = get_pipeline_entity(pipeline_id="pipe-11111111")
    pipeline_entity.status = pipeline.PipelineStatus.Created
    recipe_version_entity = get_test_recipe_version_with_specific_version_name_and_status(
        status=recipe_version.RecipeVersionStatus.Released, version_name="1.1.0"
    )
    pipeline_query_service_mock.get_pipeline.side_effect = [pipeline_entity]
    recipe_version_query_service_mock.get_recipe_version.return_value = recipe_version_entity
    recipe_query_service_mock.get_recipe.return_value = mock_recipe_object
    pipeline_service_mock.get_pipeline_allowed_build_instance_types.return_value = TEST_BUILD_INSTANCE_TYPES

    # ACT
    update_pipeline_command_handler.handle(
        command=update_pipeline_command,
        message_bus=message_bus_mock,
        recipe_version_qry_srv=recipe_version_query_service_mock,
        pipeline_qry_srv=pipeline_query_service_mock,
        recipe_qry_srv=recipe_query_service_mock,
        pipeline_srv=pipeline_service_mock,
        uow=uow_mock,
    )

    # ASSERT
    generic_repo_mock.update_attributes.assert_called_with(
        pipeline.PipelinePrimaryKey(
            pipelineId=pipeline_entity.pipelineId,
            projectId=pipeline_entity.projectId,
        ),
        productId=TEST_PRODUCT_ID,
        lastUpdateDate=TEST_DATE,
        lastUpdatedBy=TEST_USER_ID,
        status=pipeline.PipelineStatus.Updating,
    )
    message_bus_mock.publish.assert_called_with(pipeline_update_started_event)
    uow_mock.commit.assert_called()


def test_update_pipeline_command_should_raise_an_exception_if_pipeline_is_not_found(
    get_update_pipeline_command,
    message_bus_mock,
    recipe_version_query_service_mock,
    pipeline_query_service_mock,
    get_pipeline_entity,
    uow_mock,
    recipe_query_service_mock,
    mock_recipe_object,
    pipeline_service_mock,
):
    # ARRANGE
    update_pipeline_command = get_update_pipeline_command()
    pipeline_query_service_mock.get_pipeline.return_value = None
    recipe_version_query_service_mock.get_recipe_version.return_value = None
    recipe_query_service_mock.get_recipe.return_value = mock_recipe_object
    pipeline_service_mock.get_pipeline_allowed_build_instance_types.return_value = TEST_BUILD_INSTANCE_TYPES

    # ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        update_pipeline_command_handler.handle(
            command=update_pipeline_command,
            message_bus=message_bus_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
            pipeline_qry_srv=pipeline_query_service_mock,
            recipe_qry_srv=recipe_query_service_mock,
            pipeline_srv=pipeline_service_mock,
            uow=uow_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(
        f"Pipeline {update_pipeline_command.pipelineId.value} can not be found."
    )


def test_update_pipeline_command_should_raise_an_exception_if_recipe_is_not_found(
    get_update_pipeline_command,
    message_bus_mock,
    recipe_version_query_service_mock,
    pipeline_query_service_mock,
    get_pipeline_entity,
    uow_mock,
    recipe_query_service_mock,
    mock_recipe_object,
    pipeline_service_mock,
    get_test_recipe_version_id,
    get_test_recipe_version_with_specific_version_name_and_status,
):
    # ARRANGE
    update_pipeline_command = get_update_pipeline_command(recipe_version_id=get_test_recipe_version_id)
    update_pipeline_command.pipelineSchedule = None
    update_pipeline_command.buildInstanceTypes = pipeline_build_instance_types_value_object.from_list(
        TEST_BUILD_INSTANCE_TYPES
    )
    pipeline_entity = get_pipeline_entity(pipeline_id="pipe-11111111")
    pipeline_entity.status = pipeline.PipelineStatus.Created
    recipe_version_entity = get_test_recipe_version_with_specific_version_name_and_status(
        status=recipe_version.RecipeVersionStatus.Released, version_name="1.1.0"
    )
    pipeline_query_service_mock.get_pipeline.side_effect = [pipeline_entity]
    recipe_version_query_service_mock.get_recipe_version.return_value = recipe_version_entity
    recipe_query_service_mock.get_recipe.return_value = None
    pipeline_service_mock.get_pipeline_allowed_build_instance_types.return_value = TEST_BUILD_INSTANCE_TYPES

    # ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        update_pipeline_command_handler.handle(
            command=update_pipeline_command,
            message_bus=message_bus_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
            pipeline_qry_srv=pipeline_query_service_mock,
            recipe_qry_srv=recipe_query_service_mock,
            pipeline_srv=pipeline_service_mock,
            uow=uow_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(f"No recipe {mock_recipe_object.recipeId} found.")


def test_update_pipeline_command_should_raise_an_exception_if_allowed_build_types_is_not_found(
    get_update_pipeline_command,
    message_bus_mock,
    recipe_version_query_service_mock,
    pipeline_query_service_mock,
    get_pipeline_entity,
    uow_mock,
    recipe_query_service_mock,
    mock_recipe_object,
    pipeline_service_mock,
    get_test_recipe_version_id,
    get_test_recipe_version_with_specific_version_name_and_status,
):
    # ARRANGE
    update_pipeline_command = get_update_pipeline_command(recipe_version_id=get_test_recipe_version_id)
    update_pipeline_command.pipelineSchedule = None
    update_pipeline_command.buildInstanceTypes = pipeline_build_instance_types_value_object.from_list(
        TEST_BUILD_INSTANCE_TYPES
    )
    pipeline_entity = get_pipeline_entity(pipeline_id="pipe-11111111")
    pipeline_entity.status = pipeline.PipelineStatus.Created
    recipe_version_entity = get_test_recipe_version_with_specific_version_name_and_status(
        status=recipe_version.RecipeVersionStatus.Released, version_name="1.1.0"
    )
    pipeline_query_service_mock.get_pipeline.side_effect = [pipeline_entity]
    recipe_version_query_service_mock.get_recipe_version.return_value = recipe_version_entity
    recipe_query_service_mock.get_recipe.return_value = mock_recipe_object
    pipeline_service_mock.get_pipeline_allowed_build_instance_types.return_value = ["c8a.9xlarge"]

    # ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        update_pipeline_command_handler.handle(
            command=update_pipeline_command,
            message_bus=message_bus_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
            pipeline_qry_srv=pipeline_query_service_mock,
            recipe_qry_srv=recipe_query_service_mock,
            pipeline_srv=pipeline_service_mock,
            uow=uow_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(
        f"Build instance type {TEST_BUILD_INSTANCE_TYPES[0]} is not allowed for recipe {mock_recipe_object.recipeId}."
    )


def test_update_pipeline_command_should_raise_an_exception_if_recipe_version_is_not_found(
    get_update_pipeline_command,
    message_bus_mock,
    recipe_version_query_service_mock,
    pipeline_query_service_mock,
    get_pipeline_entity,
    uow_mock,
    recipe_query_service_mock,
    mock_recipe_object,
    pipeline_service_mock,
):
    # ARRANGE
    update_pipeline_command = get_update_pipeline_command()
    pipeline_entity = get_pipeline_entity(pipeline_id="pipe-11111111")
    pipeline_entity.status = pipeline.PipelineStatus.Created
    pipeline_query_service_mock.get_pipeline.side_effect = [pipeline_entity]
    recipe_version_query_service_mock.get_recipe_version.return_value = None
    recipe_query_service_mock.get_recipe.return_value = mock_recipe_object
    pipeline_service_mock.get_pipeline_allowed_build_instance_types.return_value = TEST_BUILD_INSTANCE_TYPES

    # ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        update_pipeline_command_handler.handle(
            command=update_pipeline_command,
            message_bus=message_bus_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
            pipeline_qry_srv=pipeline_query_service_mock,
            recipe_qry_srv=recipe_query_service_mock,
            pipeline_srv=pipeline_service_mock,
            uow=uow_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(
        f"No recipe version {pipeline_entity.recipeVersionId} found for {pipeline_entity.recipeId}."
    )


@pytest.mark.parametrize("project_id", (None, ""))
def test_update_pipeline_command_should_raise_an_exception_with_invalid_project_id(
    get_update_pipeline_command,
    project_id,
):
    # ARRANGE & ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        get_update_pipeline_command(project_id=project_id)

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to("Project ID cannot be empty.")


@pytest.mark.parametrize(
    "exception_message,pipeline_schedule",
    (
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
def test_update_pipeline_command_should_raise_an_exception_with_invalid_pipeline_schedule(
    exception_message,
    get_update_pipeline_command,
    pipeline_schedule,
):
    # ARRANGE & ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        get_update_pipeline_command(pipeline_schedule=pipeline_schedule)

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(exception_message)


@pytest.mark.parametrize(
    "build_instance_types,exception_message",
    (
        ([None], "Build instance type value cannot be empty."),
        ([""], "Build instance type value cannot be empty."),
    ),
)
def test_create_pipeline_command_should_raise_an_exception_with_invalid_build_instance_types(
    build_instance_types,
    exception_message,
    get_update_pipeline_command,
):
    # ARRANGE & ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        get_update_pipeline_command(build_instance_types=build_instance_types)

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(exception_message)


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
def test_update_pipeline_command_should_raise_an_exception_if_recipe_version_status_is_invalid(
    get_update_pipeline_command,
    get_test_recipe_version_with_specific_version_name_and_status,
    message_bus_mock,
    recipe_version_query_service_mock,
    status,
    uow_mock,
    pipeline_query_service_mock,
    get_pipeline_entity,
    get_test_recipe_version_id,
    recipe_query_service_mock,
    mock_recipe_object,
    pipeline_service_mock,
):
    # ARRANGE
    update_pipeline_command = get_update_pipeline_command(
        recipe_version_id=get_test_recipe_version_id,
    )
    pipeline_entity = get_pipeline_entity(pipeline_id="pipe-11111111")
    pipeline_entity.status = pipeline.PipelineStatus.Created
    pipeline_query_service_mock.get_pipeline.side_effect = [pipeline_entity]
    recipe_entity = get_test_recipe_version_with_specific_version_name_and_status(status=status, version_name="1.0.0")
    recipe_version_query_service_mock.get_recipe_version.return_value = recipe_entity
    recipe_query_service_mock.get_recipe.return_value = mock_recipe_object
    pipeline_service_mock.get_pipeline_allowed_build_instance_types.return_value = TEST_BUILD_INSTANCE_TYPES

    # ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        update_pipeline_command_handler.handle(
            command=update_pipeline_command,
            message_bus=message_bus_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
            pipeline_qry_srv=pipeline_query_service_mock,
            recipe_qry_srv=recipe_query_service_mock,
            pipeline_srv=pipeline_service_mock,
            uow=uow_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(
        f"Version {recipe_entity.recipeVersionId} of recipe " f"{recipe_entity.recipeId} has not been released."
    )


def test_create_pipeline_command_should_raise_an_exception_with_invalid_pipeline_id(
    get_update_pipeline_command,
):
    # ARRANGE & ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        get_update_pipeline_command(pipeline_id=None)

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to("Pipeline ID cannot be empty.")


@pytest.mark.parametrize(
    "status",
    (
        pipeline.PipelineStatus.Creating,
        pipeline.PipelineStatus.Updating,
        pipeline.PipelineStatus.Retired,
    ),
)
def test_update_pipeline_command_should_raise_an_exception_if_pipeline_status_in_an_unexpected_state(
    get_update_pipeline_command,
    get_test_recipe_version_with_specific_version_name_and_status,
    message_bus_mock,
    recipe_version_query_service_mock,
    status,
    uow_mock,
    pipeline_query_service_mock,
    get_pipeline_entity,
    get_test_recipe_version_id,
    recipe_query_service_mock,
    mock_recipe_object,
    pipeline_service_mock,
):
    # ARRANGE
    update_pipeline_command = get_update_pipeline_command(
        recipe_version_id=get_test_recipe_version_id,
    )
    pipeline_entity = get_pipeline_entity(pipeline_id="pipe-11111111")
    pipeline_entity.status = status
    pipeline_query_service_mock.get_pipeline.side_effect = [pipeline_entity]
    recipe_entity = get_test_recipe_version_with_specific_version_name_and_status(status=status, version_name="1.0.0")
    recipe_version_query_service_mock.get_recipe_version.return_value = recipe_entity
    recipe_query_service_mock.get_recipe.return_value = mock_recipe_object
    pipeline_service_mock.get_pipeline_allowed_build_instance_types.return_value = TEST_BUILD_INSTANCE_TYPES

    # ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        update_pipeline_command_handler.handle(
            command=update_pipeline_command,
            message_bus=message_bus_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
            pipeline_qry_srv=pipeline_query_service_mock,
            recipe_qry_srv=recipe_query_service_mock,
            pipeline_srv=pipeline_service_mock,
            uow=uow_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(
        f"Pipeline status should be CREATED or FAILED to allow update, but is {status.value}."
    )
