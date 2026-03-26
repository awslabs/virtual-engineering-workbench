import assertpy
import pytest
from freezegun import freeze_time

from app.packaging.domain.command_handlers.pipeline import remove_pipeline_command_handler
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.pipeline import pipeline
from app.packaging.domain.tests.conftest import TEST_PIPELINE_ID


@freeze_time("2023-10-12")
def test_handle_should_raise_exception_when_pipeline_can_t_be_deleted(
    generic_repo_mock,
    get_remove_pipeline_command,
    pipeline_service_mock,
    uow_mock,
):
    # ARRANGE
    remove_pipeline_command_mock = get_remove_pipeline_command()
    pipeline_service_mock.delete_pipeline.side_effect = Exception()

    # ACT
    with pytest.raises(domain_exception.DomainException) as exc_info:
        remove_pipeline_command_handler.handle(
            command=remove_pipeline_command_mock,
            pipeline_srv=pipeline_service_mock,
            uow=uow_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exc_info.value)).is_equal_to(
        f"Pipeline {remove_pipeline_command_mock.pipelineArn.value} can not be deleted."
    )
    generic_repo_mock.update_attributes.assert_called_once_with(
        pipeline.PipelinePrimaryKey(
            projectId=remove_pipeline_command_mock.projectId.value,
            pipelineId=remove_pipeline_command_mock.pipelineId.value,
        ),
        lastUpdateDate="2023-10-12T00:00:00+00:00",
        status=pipeline.PipelineStatus.Failed,
    )
    uow_mock.commit.assert_called()


@freeze_time("2023-10-12")
def test_handle_should_raise_exception_when_infrastructure_config_can_t_be_deleted(
    generic_repo_mock,
    get_remove_pipeline_command,
    pipeline_service_mock,
    uow_mock,
):
    # ARRANGE
    remove_pipeline_command_mock = get_remove_pipeline_command()
    pipeline_service_mock.delete_infrastructure_config.side_effect = Exception()

    # ACT
    with pytest.raises(domain_exception.DomainException) as exc_info:
        remove_pipeline_command_handler.handle(
            command=remove_pipeline_command_mock,
            pipeline_srv=pipeline_service_mock,
            uow=uow_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exc_info.value)).is_equal_to(
        f"Pipeline infrastructure configuration {remove_pipeline_command_mock.infrastructureConfigArn.value} can not be deleted."
    )
    generic_repo_mock.update_attributes.assert_called_once_with(
        pipeline.PipelinePrimaryKey(
            projectId=remove_pipeline_command_mock.projectId.value,
            pipelineId=remove_pipeline_command_mock.pipelineId.value,
        ),
        lastUpdateDate="2023-10-12T00:00:00+00:00",
        status=pipeline.PipelineStatus.Failed,
    )
    uow_mock.commit.assert_called()


@freeze_time("2023-10-12")
def test_handle_should_raise_exception_when_distribution_config_can_t_be_deleted(
    generic_repo_mock,
    get_remove_pipeline_command,
    pipeline_service_mock,
    uow_mock,
):
    # ARRANGE
    remove_pipeline_command_mock = get_remove_pipeline_command()
    pipeline_service_mock.delete_distribution_config.side_effect = Exception()

    # ACT
    with pytest.raises(domain_exception.DomainException) as exc_info:
        remove_pipeline_command_handler.handle(
            command=remove_pipeline_command_mock,
            pipeline_srv=pipeline_service_mock,
            uow=uow_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exc_info.value)).is_equal_to(
        f"Pipeline distribution configuration {remove_pipeline_command_mock.distributionConfigArn.value} can not be deleted."
    )
    generic_repo_mock.update_attributes.assert_called_once_with(
        pipeline.PipelinePrimaryKey(
            projectId=remove_pipeline_command_mock.projectId.value,
            pipelineId=remove_pipeline_command_mock.pipelineId.value,
        ),
        lastUpdateDate="2023-10-12T00:00:00+00:00",
        status=pipeline.PipelineStatus.Failed,
    )
    uow_mock.commit.assert_called()


@pytest.mark.parametrize(
    "distribution_config_arn,infrastructure_config_arn,pipeline_arn",
    (
        (
            None,
            None,
            None,
        ),
        (
            f"arn:aws:imagebuilder:us-east-1:123456789012:distribution-configuration/{TEST_PIPELINE_ID}",
            None,
            None,
        ),
        (
            f"arn:aws:imagebuilder:us-east-1:123456789012:distribution-configuration/{TEST_PIPELINE_ID}",
            f"arn:aws:imagebuilder:us-east-1:123456789012:infrastructure-configuration/{TEST_PIPELINE_ID}",
            None,
        ),
        (
            f"arn:aws:imagebuilder:us-east-1:123456789012:distribution-configuration/{TEST_PIPELINE_ID}",
            f"arn:aws:imagebuilder:us-east-1:123456789012:infrastructure-configuration/{TEST_PIPELINE_ID}",
            f"arn:aws:imagebuilder:us-east-1:123456789012:image-pipeline/{TEST_PIPELINE_ID}",
        ),
    ),
)
@freeze_time("2023-10-12")
def test_handle_should_remove_pipeline(
    distribution_config_arn,
    generic_repo_mock,
    get_remove_pipeline_command,
    infrastructure_config_arn,
    pipeline_arn,
    pipeline_service_mock,
    uow_mock,
):
    # ARRANGE
    remove_pipeline_command_mock = get_remove_pipeline_command(
        distribution_config_arn=distribution_config_arn,
        infrastructure_config_arn=infrastructure_config_arn,
        pipeline_arn=pipeline_arn,
    )

    # ACT
    remove_pipeline_command_handler.handle(
        command=remove_pipeline_command_mock,
        pipeline_srv=pipeline_service_mock,
        uow=uow_mock,
    )

    # ASSERT
    if distribution_config_arn:
        pipeline_service_mock.delete_distribution_config.assert_called_once_with(
            distribution_config_arn=remove_pipeline_command_mock.distributionConfigArn.value
        )
    if infrastructure_config_arn:
        pipeline_service_mock.delete_infrastructure_config.assert_called_once_with(
            infrastructure_config_arn=remove_pipeline_command_mock.infrastructureConfigArn.value
        )
    if pipeline_arn:
        pipeline_service_mock.delete_pipeline.assert_called_once_with(
            pipeline_arn=remove_pipeline_command_mock.pipelineArn.value
        )
    generic_repo_mock.update_attributes.assert_called_once_with(
        pipeline.PipelinePrimaryKey(
            projectId=remove_pipeline_command_mock.projectId.value,
            pipelineId=remove_pipeline_command_mock.pipelineId.value,
        ),
        lastUpdateDate="2023-10-12T00:00:00+00:00",
        status=pipeline.PipelineStatus.Retired,
    )
    uow_mock.commit.assert_called()
