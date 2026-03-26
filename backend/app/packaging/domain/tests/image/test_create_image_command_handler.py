from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.packaging.domain.command_handlers.image import create_image_command_handler
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.pipeline import pipeline
from app.packaging.domain.tests.conftest import TEST_DATE


@pytest.mark.parametrize("project_id", (None, ""))
def test_create_image_command_should_raise_an_exception_with_invalid_project_id(
    get_create_image_command,
    project_id,
):
    # ARRANGE & ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        get_create_image_command(project_id=project_id)

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to("Project ID cannot be empty.")


@pytest.mark.parametrize("pipeline_id", (None, ""))
def test_create_image_command_should_raise_an_exception_with_invalid_pipeline_id(
    get_create_image_command,
    pipeline_id,
):
    # ARRANGE & ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        get_create_image_command(pipeline_id=pipeline_id)

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to("Pipeline ID cannot be empty.")


def test_create_image_command_handler_should_raise_an_exception_when_pipeline_can_not_be_found(
    get_create_image_command,
    pipeline_query_service_mock,
    pipeline_service_mock,
    uow_mock,
):
    # ARRANGE
    create_image_command_mock = get_create_image_command()
    pipeline_query_service_mock.get_pipeline.return_value = None

    # ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        create_image_command_handler.handle(
            command=create_image_command_mock,
            pipeline_qry_srv=pipeline_query_service_mock,
            pipeline_srv=pipeline_service_mock,
            uow=uow_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(
        f"Pipeline {create_image_command_mock.pipelineId.value} can not be found."
    )


@pytest.mark.parametrize(
    "status",
    (
        pipeline.PipelineStatus.Creating,
        pipeline.PipelineStatus.Failed,
        pipeline.PipelineStatus.Retired,
        pipeline.PipelineStatus.Updating,
    ),
)
def test_create_image_command_handler_should_raise_an_exception_when_pipeline_status_is_invalid(
    get_create_image_command,
    get_pipeline_entity,
    pipeline_query_service_mock,
    pipeline_service_mock,
    status,
    uow_mock,
):
    # ARRANGE
    create_image_command_mock = get_create_image_command()
    pipeline_entity = get_pipeline_entity(status=status)
    pipeline_query_service_mock.get_pipeline.return_value = pipeline_entity

    # ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        create_image_command_handler.handle(
            command=create_image_command_mock,
            pipeline_qry_srv=pipeline_query_service_mock,
            pipeline_srv=pipeline_service_mock,
            uow=uow_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(
        f"Pipeline status should be {pipeline.PipelineStatus.Created.value} to "
        f"allow execution, but is {pipeline_entity.status.value}."
    )


@pytest.mark.parametrize("image_build_version_arn", (None, "", "a"))
def test_create_image_command_handler_should_raise_an_exception_when_image_build_version_arn_is_invalid(
    get_create_image_command,
    get_pipeline_entity,
    image_build_version_arn,
    pipeline_query_service_mock,
    pipeline_service_mock,
    uow_mock,
):
    # ARRANGE
    create_image_command_mock = get_create_image_command()
    pipeline_entity = get_pipeline_entity(status=pipeline.PipelineStatus.Created)
    pipeline_query_service_mock.get_pipeline.return_value = pipeline_entity
    pipeline_service_mock.start_pipeline_execution.return_value = image_build_version_arn

    with pytest.raises(domain_exception.DomainException) as exec_info:
        create_image_command_handler.handle(
            command=create_image_command_mock,
            pipeline_qry_srv=pipeline_query_service_mock,
            pipeline_srv=pipeline_service_mock,
            uow=uow_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(
        "Image build version ARN should match ^arn:aws[^:]*:imagebuilder:[^:]+:(?:[0-9]{12}|aws):image/[a-z0-9-_]+/[0-9]+\.[0-9]+\.[0-9]+/[0-9]+$ pattern."  # noqa: W605
    )


@freeze_time(TEST_DATE)
@mock.patch("app.packaging.domain.model.image.image.random.choice", lambda _: "1")
def test_create_image_command_handler_should_create_image(
    generic_repo_mock,
    get_create_image_command,
    get_image_entity,
    get_pipeline_entity,
    get_test_image_build_version_arn,
    pipeline_query_service_mock,
    pipeline_service_mock,
    uow_mock,
):
    # ARRANGE
    create_image_command_mock = get_create_image_command()
    image_entity = get_image_entity(image_id="image-11111111")
    pipeline_entity = get_pipeline_entity(status=pipeline.PipelineStatus.Created)
    pipeline_query_service_mock.get_pipeline.return_value = pipeline_entity
    pipeline_service_mock.start_pipeline_execution.return_value = get_test_image_build_version_arn(
        build_version=1, recipe_name=pipeline_entity.recipeName, version_name=pipeline_entity.recipeVersionName
    )

    # ACT
    create_image_command_handler.handle(
        command=create_image_command_mock,
        pipeline_qry_srv=pipeline_query_service_mock,
        pipeline_srv=pipeline_service_mock,
        uow=uow_mock,
    )

    # ASSERT
    generic_repo_mock.add.assert_called_with(image_entity)
    uow_mock.commit.assert_called()
