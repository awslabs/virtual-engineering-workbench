import assertpy
import pytest
from freezegun import freeze_time

from app.packaging.domain.command_handlers.pipeline import retire_pipeline_command_handler
from app.packaging.domain.events.pipeline import pipeline_retirement_started
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.pipeline import pipeline
from app.packaging.domain.tests.conftest import TEST_PIPELINE_ID


@pytest.mark.parametrize("project_id", (None, ""))
def test_command_should_raise_an_exception_with_invalid_project_id(
    get_retire_pipeline_command,
    project_id,
):
    # ARRANGE & ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        get_retire_pipeline_command(project_id=project_id)

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to("Project ID cannot be empty.")


@pytest.mark.parametrize("pipeline_id", (None, ""))
def test_command_should_raise_an_exception_with_invalid_pipeline_id(
    get_retire_pipeline_command,
    pipeline_id,
):
    # ARRANGE & ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        get_retire_pipeline_command(pipeline_id=pipeline_id)

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to("Pipeline ID cannot be empty.")


@pytest.mark.parametrize("last_update_by", (None, ""))
def test_command_should_raise_an_exception_with_invalid_last_update_by(
    get_retire_pipeline_command,
    last_update_by,
):
    # ARRANGE & ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        get_retire_pipeline_command(last_update_by=last_update_by)

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to("User ID cannot be empty.")


def test_handle_should_raise_exception_when_pipeline_is_not_found(
    get_retire_pipeline_command,
    message_bus_mock,
    pipeline_query_service_mock,
    uow_mock,
):
    # ARRANGE
    pipeline_query_service_mock.get_pipeline.return_value = None
    retire_pipeline_command_mock = get_retire_pipeline_command()

    # ACT
    with pytest.raises(domain_exception.DomainException) as exc_info:
        retire_pipeline_command_handler.handle(
            command=retire_pipeline_command_mock,
            message_bus=message_bus_mock,
            pipeline_qry_srv=pipeline_query_service_mock,
            uow=uow_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exc_info.value)).is_equal_to(
        f"Pipeline {retire_pipeline_command_mock.pipelineId.value} can not be found."
    )


@pytest.mark.parametrize(
    "status",
    (
        pipeline.PipelineStatus.Creating,
        pipeline.PipelineStatus.Retired,
        pipeline.PipelineStatus.Updating,
    ),
)
def test_handle_should_raise_exception_when_status_is_invalid(
    get_pipeline_entity,
    get_retire_pipeline_command,
    message_bus_mock,
    pipeline_query_service_mock,
    status,
    uow_mock,
):
    # ARRANGE
    pipeline_entity = get_pipeline_entity(status=status)
    pipeline_query_service_mock.get_pipeline.return_value = pipeline_entity
    retire_pipeline_command_mock = get_retire_pipeline_command()

    # ACT
    with pytest.raises(domain_exception.DomainException) as exc_info:
        retire_pipeline_command_handler.handle(
            command=retire_pipeline_command_mock,
            message_bus=message_bus_mock,
            pipeline_qry_srv=pipeline_query_service_mock,
            uow=uow_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exc_info.value)).is_equal_to(
        f"Pipeline {retire_pipeline_command_mock.pipelineId.value} can not be retired while in {pipeline_entity.status} status."
    )


@freeze_time("2023-10-12")
@pytest.mark.parametrize(
    "distribution_config_arn,infrastructure_config_arn,pipeline_arn,status",
    (
        (
            f"arn:aws:imagebuilder:us-east-1:123456789012:distribution-configuration/{TEST_PIPELINE_ID}",
            f"arn:aws:imagebuilder:us-east-1:123456789012:infrastructure-configuration/{TEST_PIPELINE_ID}",
            f"arn:aws:imagebuilder:us-east-1:123456789012:image-pipeline/{TEST_PIPELINE_ID}",
            pipeline.PipelineStatus.Created,
        ),
        (
            None,
            None,
            None,
            pipeline.PipelineStatus.Failed,
        ),
        (
            f"arn:aws:imagebuilder:us-east-1:123456789012:distribution-configuration/{TEST_PIPELINE_ID}",
            None,
            None,
            pipeline.PipelineStatus.Failed,
        ),
        (
            f"arn:aws:imagebuilder:us-east-1:123456789012:distribution-configuration/{TEST_PIPELINE_ID}",
            f"arn:aws:imagebuilder:us-east-1:123456789012:infrastructure-configuration/{TEST_PIPELINE_ID}",
            None,
            pipeline.PipelineStatus.Failed,
        ),
        (
            f"arn:aws:imagebuilder:us-east-1:123456789012:distribution-configuration/{TEST_PIPELINE_ID}",
            f"arn:aws:imagebuilder:us-east-1:123456789012:infrastructure-configuration/{TEST_PIPELINE_ID}",
            f"arn:aws:imagebuilder:us-east-1:123456789012:image-pipeline/{TEST_PIPELINE_ID}",
            pipeline.PipelineStatus.Failed,
        ),
    ),
)
def test_handle_should_retire_version(
    distribution_config_arn,
    generic_repo_mock,
    get_pipeline_entity,
    get_retire_pipeline_command,
    infrastructure_config_arn,
    message_bus_mock,
    pipeline_arn,
    pipeline_query_service_mock,
    status,
    uow_mock,
):
    # ARRANGE
    pipeline_entity = get_pipeline_entity(
        distribution_config_arn=distribution_config_arn,
        infrastructure_config_arn=infrastructure_config_arn,
        pipeline_arn=pipeline_arn,
        status=status,
    )
    pipeline_query_service_mock.get_pipeline.return_value = pipeline_entity
    retire_pipeline_command_mock = get_retire_pipeline_command()
    pipeline_retirement_started_kwargs = {
        "projectId": retire_pipeline_command_mock.projectId.value,
        "pipelineId": retire_pipeline_command_mock.pipelineId.value,
    }
    if pipeline_entity.distributionConfigArn:
        pipeline_retirement_started_kwargs["distributionConfigArn"] = pipeline_entity.distributionConfigArn
    if pipeline_entity.infrastructureConfigArn:
        pipeline_retirement_started_kwargs["infrastructureConfigArn"] = pipeline_entity.infrastructureConfigArn
    if pipeline_entity.pipelineArn:
        pipeline_retirement_started_kwargs["pipelineArn"] = pipeline_entity.pipelineArn

    # ACT
    retire_pipeline_command_handler.handle(
        command=retire_pipeline_command_mock,
        message_bus=message_bus_mock,
        pipeline_qry_srv=pipeline_query_service_mock,
        uow=uow_mock,
    )

    # ASSERT
    generic_repo_mock.update_attributes.assert_called_once_with(
        pipeline.PipelinePrimaryKey(
            projectId=retire_pipeline_command_mock.projectId.value,
            pipelineId=retire_pipeline_command_mock.pipelineId.value,
        ),
        lastUpdateDate="2023-10-12T00:00:00+00:00",
        lastUpdateBy=retire_pipeline_command_mock.lastUpdateBy.value,
        status=pipeline.PipelineStatus.Updating,
    )
    uow_mock.commit.assert_called()
    message_bus_mock.publish.assert_called_once_with(
        pipeline_retirement_started.PipelineRetirementStarted(**pipeline_retirement_started_kwargs)
    )
