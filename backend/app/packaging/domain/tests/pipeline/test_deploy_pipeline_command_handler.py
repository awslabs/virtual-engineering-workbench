import assertpy
import pytest

from app.packaging.domain.command_handlers.pipeline import deploy_pipeline_command_handler
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.pipeline import pipeline
from app.packaging.domain.model.recipe import recipe_version


def test_deploy_pipeline_command_handler_should_deploy_pipeline(
    get_deploy_pipeline_command,
    get_pipeline_entity,
    get_test_pipeline_arn,
    get_test_pipeline_distribution_config_arn,
    get_test_pipeline_infrastructure_config_arn,
    get_test_recipe_version_with_specific_version_name_and_status,
    generic_repo_mock,
    logger_mock,
    pipeline_query_service_mock,
    pipeline_service_mock,
    recipe_version_query_service_mock,
    uow_mock,
):
    # ARRANGE
    deploy_pipeline_command = get_deploy_pipeline_command()
    pipeline_entity = get_pipeline_entity()
    pipeline_query_service_mock.get_pipeline.return_value = pipeline_entity
    pipeline_service_mock.create_distribution_config.return_value = get_test_pipeline_distribution_config_arn()
    pipeline_service_mock.create_infrastructure_config.return_value = get_test_pipeline_infrastructure_config_arn()
    pipeline_service_mock.create_pipeline.return_value = get_test_pipeline_arn()
    recipe_version_entity = get_test_recipe_version_with_specific_version_name_and_status(
        status=recipe_version.RecipeVersionStatus.Released, version_name="1.0.0"
    )
    recipe_version_query_service_mock.get_recipe_version.return_value = recipe_version_entity

    # ACT
    deploy_pipeline_command_handler.handle(
        command=deploy_pipeline_command,
        logger=logger_mock,
        pipeline_qry_srv=pipeline_query_service_mock,
        pipeline_srv=pipeline_service_mock,
        recipe_version_qry_srv=recipe_version_query_service_mock,
        uow=uow_mock,
    )

    # ASSERT
    generic_repo_mock.update_attributes.assert_called_with(
        pipeline.PipelinePrimaryKey(
            projectId=pipeline_entity.projectId,
            pipelineId=pipeline_entity.pipelineId,
        ),
        distributionConfigArn=get_test_pipeline_distribution_config_arn(),
        infrastructureConfigArn=get_test_pipeline_infrastructure_config_arn(),
        pipelineArn=get_test_pipeline_arn(),
        status=pipeline.PipelineStatus.Created,
    )
    pipeline_service_mock.create_distribution_config.assert_called_with(
        description=f"Distribution configuration for {pipeline_entity.pipelineName} pipeline.",
        image_tags={"Name": f"Version {recipe_version_entity.recipeVersionName} of {recipe_version_entity.recipeName}"},
        name=pipeline_entity.pipelineId,
    )
    pipeline_service_mock.create_infrastructure_config.assert_called_with(
        description=f"Infrastructure configuration for {pipeline_entity.pipelineName} pipeline.",
        instance_types=pipeline_entity.buildInstanceTypes,
        name=pipeline_entity.pipelineId,
    )
    pipeline_service_mock.create_pipeline.assert_called_with(
        description=pipeline_entity.pipelineDescription,
        distribution_config_arn=get_test_pipeline_distribution_config_arn(),
        infrastructure_config_arn=get_test_pipeline_infrastructure_config_arn(),
        name=pipeline_entity.pipelineId,
        recipe_version_arn=recipe_version_entity.recipeVersionArn,
        schedule=pipeline_entity.pipelineSchedule,
    )
    uow_mock.commit.assert_called()


def test_deploy_pipeline_command_handler_should_update_distribution_configuration_and_deploy_pipeline(
    get_deploy_pipeline_command,
    get_pipeline_entity,
    get_test_pipeline_arn,
    get_test_pipeline_distribution_config_arn,
    get_test_pipeline_infrastructure_config_arn,
    get_test_recipe_version_with_specific_version_name_and_status,
    generic_repo_mock,
    logger_mock,
    pipeline_query_service_mock,
    pipeline_service_mock,
    recipe_version_query_service_mock,
    uow_mock,
):
    # ARRANGE
    deploy_pipeline_command = get_deploy_pipeline_command()
    pipeline_entity = get_pipeline_entity(distribution_config_arn=get_test_pipeline_distribution_config_arn())
    pipeline_query_service_mock.get_pipeline.return_value = pipeline_entity
    pipeline_service_mock.update_distribution_config.return_value = get_test_pipeline_distribution_config_arn()
    pipeline_service_mock.create_infrastructure_config.return_value = get_test_pipeline_infrastructure_config_arn()
    pipeline_service_mock.create_pipeline.return_value = get_test_pipeline_arn()
    recipe_version_entity = get_test_recipe_version_with_specific_version_name_and_status(
        status=recipe_version.RecipeVersionStatus.Released, version_name="1.0.0"
    )
    recipe_version_query_service_mock.get_recipe_version.return_value = recipe_version_entity

    # ACT
    deploy_pipeline_command_handler.handle(
        command=deploy_pipeline_command,
        logger=logger_mock,
        pipeline_qry_srv=pipeline_query_service_mock,
        pipeline_srv=pipeline_service_mock,
        recipe_version_qry_srv=recipe_version_query_service_mock,
        uow=uow_mock,
    )

    # ASSERT
    generic_repo_mock.update_attributes.assert_called_with(
        pipeline.PipelinePrimaryKey(
            projectId=pipeline_entity.projectId,
            pipelineId=pipeline_entity.pipelineId,
        ),
        distributionConfigArn=get_test_pipeline_distribution_config_arn(),
        infrastructureConfigArn=get_test_pipeline_infrastructure_config_arn(),
        pipelineArn=get_test_pipeline_arn(),
        status=pipeline.PipelineStatus.Created,
    )
    pipeline_service_mock.update_distribution_config.assert_called_with(
        description=f"Distribution configuration for {pipeline_entity.pipelineName} pipeline.",
        distribution_config_arn=pipeline_entity.distributionConfigArn,
        image_tags={"Name": f"Version {recipe_version_entity.recipeVersionName} of {recipe_version_entity.recipeName}"},
    )
    pipeline_service_mock.create_infrastructure_config.assert_called_with(
        description=f"Infrastructure configuration for {pipeline_entity.pipelineName} pipeline.",
        instance_types=pipeline_entity.buildInstanceTypes,
        name=pipeline_entity.pipelineId,
    )
    pipeline_service_mock.create_pipeline.assert_called_with(
        description=pipeline_entity.pipelineDescription,
        distribution_config_arn=get_test_pipeline_distribution_config_arn(),
        infrastructure_config_arn=get_test_pipeline_infrastructure_config_arn(),
        name=pipeline_entity.pipelineId,
        recipe_version_arn=recipe_version_entity.recipeVersionArn,
        schedule=pipeline_entity.pipelineSchedule,
    )
    uow_mock.commit.assert_called()


def test_deploy_pipeline_command_handler_should_update_infrastructure_configuration_and_deploy_pipeline(
    get_deploy_pipeline_command,
    get_pipeline_entity,
    get_test_pipeline_arn,
    get_test_pipeline_distribution_config_arn,
    get_test_pipeline_infrastructure_config_arn,
    get_test_recipe_version_with_specific_version_name_and_status,
    generic_repo_mock,
    logger_mock,
    pipeline_query_service_mock,
    pipeline_service_mock,
    recipe_version_query_service_mock,
    uow_mock,
):
    # ARRANGE
    deploy_pipeline_command = get_deploy_pipeline_command()
    pipeline_entity = get_pipeline_entity(
        distribution_config_arn=get_test_pipeline_distribution_config_arn(),
        infrastructure_config_arn=get_test_pipeline_infrastructure_config_arn(),
    )
    pipeline_query_service_mock.get_pipeline.return_value = pipeline_entity
    pipeline_service_mock.update_distribution_config.return_value = get_test_pipeline_distribution_config_arn()
    pipeline_service_mock.update_infrastructure_config.return_value = get_test_pipeline_infrastructure_config_arn()
    pipeline_service_mock.create_pipeline.return_value = get_test_pipeline_arn()
    recipe_version_entity = get_test_recipe_version_with_specific_version_name_and_status(
        status=recipe_version.RecipeVersionStatus.Released, version_name="1.0.0"
    )
    recipe_version_query_service_mock.get_recipe_version.return_value = recipe_version_entity

    # ACT
    deploy_pipeline_command_handler.handle(
        command=deploy_pipeline_command,
        logger=logger_mock,
        pipeline_qry_srv=pipeline_query_service_mock,
        pipeline_srv=pipeline_service_mock,
        recipe_version_qry_srv=recipe_version_query_service_mock,
        uow=uow_mock,
    )

    # ASSERT
    generic_repo_mock.update_attributes.assert_called_with(
        pipeline.PipelinePrimaryKey(
            projectId=pipeline_entity.projectId,
            pipelineId=pipeline_entity.pipelineId,
        ),
        distributionConfigArn=get_test_pipeline_distribution_config_arn(),
        infrastructureConfigArn=get_test_pipeline_infrastructure_config_arn(),
        pipelineArn=get_test_pipeline_arn(),
        status=pipeline.PipelineStatus.Created,
    )
    pipeline_service_mock.update_distribution_config.assert_called_with(
        description=f"Distribution configuration for {pipeline_entity.pipelineName} pipeline.",
        distribution_config_arn=pipeline_entity.distributionConfigArn,
        image_tags={"Name": f"Version {recipe_version_entity.recipeVersionName} of {recipe_version_entity.recipeName}"},
    )
    pipeline_service_mock.update_infrastructure_config.assert_called_with(
        description=f"Infrastructure configuration for {pipeline_entity.pipelineName} pipeline.",
        infrastructure_config_arn=pipeline_entity.infrastructureConfigArn,
        instance_types=pipeline_entity.buildInstanceTypes,
    )
    pipeline_service_mock.create_pipeline.assert_called_with(
        description=pipeline_entity.pipelineDescription,
        distribution_config_arn=get_test_pipeline_distribution_config_arn(),
        infrastructure_config_arn=get_test_pipeline_infrastructure_config_arn(),
        name=pipeline_entity.pipelineId,
        recipe_version_arn=recipe_version_entity.recipeVersionArn,
        schedule=pipeline_entity.pipelineSchedule,
    )
    uow_mock.commit.assert_called()


def test_deploy_pipeline_command_handler_should_update_pipeline(
    get_deploy_pipeline_command,
    get_pipeline_entity,
    get_test_pipeline_arn,
    get_test_pipeline_distribution_config_arn,
    get_test_pipeline_infrastructure_config_arn,
    get_test_recipe_version_with_specific_version_name_and_status,
    generic_repo_mock,
    logger_mock,
    pipeline_query_service_mock,
    pipeline_service_mock,
    recipe_version_query_service_mock,
    uow_mock,
):
    # ARRANGE
    deploy_pipeline_command = get_deploy_pipeline_command()
    pipeline_entity = get_pipeline_entity(
        distribution_config_arn=get_test_pipeline_distribution_config_arn(),
        infrastructure_config_arn=get_test_pipeline_infrastructure_config_arn(),
        pipeline_arn=get_test_pipeline_arn(),
    )
    pipeline_query_service_mock.get_pipeline.return_value = pipeline_entity
    pipeline_service_mock.update_distribution_config.return_value = get_test_pipeline_distribution_config_arn()
    pipeline_service_mock.update_infrastructure_config.return_value = get_test_pipeline_infrastructure_config_arn()
    pipeline_service_mock.update_pipeline.return_value = get_test_pipeline_arn()
    recipe_version_entity = get_test_recipe_version_with_specific_version_name_and_status(
        status=recipe_version.RecipeVersionStatus.Released, version_name="1.0.0"
    )
    recipe_version_query_service_mock.get_recipe_version.return_value = recipe_version_entity

    # ACT
    deploy_pipeline_command_handler.handle(
        command=deploy_pipeline_command,
        logger=logger_mock,
        pipeline_qry_srv=pipeline_query_service_mock,
        pipeline_srv=pipeline_service_mock,
        recipe_version_qry_srv=recipe_version_query_service_mock,
        uow=uow_mock,
    )

    # ASSERT
    generic_repo_mock.update_attributes.assert_called_with(
        pipeline.PipelinePrimaryKey(
            projectId=pipeline_entity.projectId,
            pipelineId=pipeline_entity.pipelineId,
        ),
        distributionConfigArn=get_test_pipeline_distribution_config_arn(),
        infrastructureConfigArn=get_test_pipeline_infrastructure_config_arn(),
        pipelineArn=get_test_pipeline_arn(),
        status=pipeline.PipelineStatus.Created,
    )
    pipeline_service_mock.update_distribution_config.assert_called_with(
        description=f"Distribution configuration for {pipeline_entity.pipelineName} pipeline.",
        distribution_config_arn=pipeline_entity.distributionConfigArn,
        image_tags={"Name": f"Version {recipe_version_entity.recipeVersionName} of {recipe_version_entity.recipeName}"},
    )
    pipeline_service_mock.update_infrastructure_config.assert_called_with(
        description=f"Infrastructure configuration for {pipeline_entity.pipelineName} pipeline.",
        infrastructure_config_arn=pipeline_entity.infrastructureConfigArn,
        instance_types=pipeline_entity.buildInstanceTypes,
    )
    pipeline_service_mock.update_pipeline.assert_called_with(
        description=pipeline_entity.pipelineDescription,
        distribution_config_arn=get_test_pipeline_distribution_config_arn(),
        infrastructure_config_arn=get_test_pipeline_infrastructure_config_arn(),
        pipeline_arn=pipeline_entity.pipelineArn,
        recipe_version_arn=recipe_version_entity.recipeVersionArn,
        schedule=pipeline_entity.pipelineSchedule,
    )
    uow_mock.commit.assert_called()


@pytest.mark.parametrize("project_id", (None, ""))
def test_deploy_pipeline_command_should_raise_an_exception_with_invalid_project_id(
    get_deploy_pipeline_command,
    project_id,
):
    # ARRANGE & ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        get_deploy_pipeline_command(project_id=project_id)

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to("Project ID cannot be empty.")


@pytest.mark.parametrize("pipeline_id", (None, ""))
def test_deploy_pipeline_command_should_raise_an_exception_with_invalid_pipeline_id(
    get_deploy_pipeline_command,
    pipeline_id,
):
    # ARRANGE & ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        get_deploy_pipeline_command(pipeline_id=pipeline_id)

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to("Pipeline ID cannot be empty.")


def test_deploy_pipeline_command_should_raise_an_exception_if_pipeline_is_not_found(
    generic_repo_mock,
    get_deploy_pipeline_command,
    logger_mock,
    pipeline_query_service_mock,
    pipeline_service_mock,
    recipe_version_query_service_mock,
    uow_mock,
):
    # ARRANGE
    deploy_pipeline_command = get_deploy_pipeline_command()
    pipeline_query_service_mock.get_pipeline.return_value = None

    # ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        deploy_pipeline_command_handler.handle(
            command=deploy_pipeline_command,
            logger=logger_mock,
            pipeline_qry_srv=pipeline_query_service_mock,
            pipeline_srv=pipeline_service_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
            uow=uow_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(
        f"Pipeline {deploy_pipeline_command.pipelineId.value} can not be found."
    )
    generic_repo_mock.update_attributes.assert_called_with(
        pipeline.PipelinePrimaryKey(
            projectId=deploy_pipeline_command.projectId.value,
            pipelineId=deploy_pipeline_command.pipelineId.value,
        ),
        status=pipeline.PipelineStatus.Failed,
    )
    uow_mock.commit.assert_called()


def test_deploy_pipeline_command_should_raise_an_exception_if_recipe_version_is_not_found(
    generic_repo_mock,
    get_deploy_pipeline_command,
    get_pipeline_entity,
    logger_mock,
    pipeline_query_service_mock,
    pipeline_service_mock,
    recipe_version_query_service_mock,
    uow_mock,
):
    # ARRANGE
    deploy_pipeline_command = get_deploy_pipeline_command()
    pipeline_entity = get_pipeline_entity()
    pipeline_query_service_mock.get_pipeline.return_value = pipeline_entity
    recipe_version_query_service_mock.get_recipe_version.return_value = None

    # ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        deploy_pipeline_command_handler.handle(
            command=deploy_pipeline_command,
            logger=logger_mock,
            pipeline_qry_srv=pipeline_query_service_mock,
            pipeline_srv=pipeline_service_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
            uow=uow_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(
        f"No recipe version {pipeline_entity.recipeVersionId} found for {pipeline_entity.recipeId}."
    )
    generic_repo_mock.update_attributes.assert_called_with(
        pipeline.PipelinePrimaryKey(
            projectId=deploy_pipeline_command.projectId.value,
            pipelineId=deploy_pipeline_command.pipelineId.value,
        ),
        status=pipeline.PipelineStatus.Failed,
    )
    uow_mock.commit.assert_called()


@pytest.mark.parametrize("distribution_config_arn", (None, "", "a"))
def test_deploy_pipeline_command_handler_raise_an_exception_if_distribution_config_arn_is_invalid(
    distribution_config_arn,
    generic_repo_mock,
    get_deploy_pipeline_command,
    get_pipeline_entity,
    get_test_recipe_version_with_specific_version_name_and_status,
    logger_mock,
    pipeline_query_service_mock,
    pipeline_service_mock,
    recipe_version_query_service_mock,
    uow_mock,
):
    # ARRANGE
    deploy_pipeline_command = get_deploy_pipeline_command()
    pipeline_entity = get_pipeline_entity()
    pipeline_query_service_mock.get_pipeline.return_value = pipeline_entity
    pipeline_service_mock.create_distribution_config.return_value = distribution_config_arn
    recipe_version_entity = get_test_recipe_version_with_specific_version_name_and_status(
        status=recipe_version.RecipeVersionStatus.Released, version_name="1.0.0"
    )
    recipe_version_query_service_mock.get_recipe_version.return_value = recipe_version_entity

    # ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        deploy_pipeline_command_handler.handle(
            command=deploy_pipeline_command,
            logger=logger_mock,
            pipeline_qry_srv=pipeline_query_service_mock,
            pipeline_srv=pipeline_service_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
            uow=uow_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(
        "Distribution configuration ARN should match ^arn:aws[^:]*:imagebuilder:[^:]+:(?:[0-9]{12}|aws):distribution-configuration/[a-z0-9-_]+$ pattern."
    )
    generic_repo_mock.update_attributes.assert_called_with(
        pipeline.PipelinePrimaryKey(
            projectId=deploy_pipeline_command.projectId.value,
            pipelineId=deploy_pipeline_command.pipelineId.value,
        ),
        status=pipeline.PipelineStatus.Failed,
    )
    uow_mock.commit.assert_called()


@pytest.mark.parametrize("infrastructure_config_arn", (None, "", "a"))
def test_deploy_pipeline_command_handler_raise_an_exception_if_infrastructure_config_arn_is_invalid(
    generic_repo_mock,
    get_deploy_pipeline_command,
    get_pipeline_entity,
    get_test_pipeline_distribution_config_arn,
    get_test_recipe_version_with_specific_version_name_and_status,
    infrastructure_config_arn,
    logger_mock,
    pipeline_query_service_mock,
    pipeline_service_mock,
    recipe_version_query_service_mock,
    uow_mock,
):
    # ARRANGE
    deploy_pipeline_command = get_deploy_pipeline_command()
    pipeline_entity = get_pipeline_entity()
    pipeline_query_service_mock.get_pipeline.return_value = pipeline_entity
    pipeline_service_mock.create_distribution_config.return_value = get_test_pipeline_distribution_config_arn()
    pipeline_service_mock.create_infrastructure_config.return_value = infrastructure_config_arn
    recipe_version_entity = get_test_recipe_version_with_specific_version_name_and_status(
        status=recipe_version.RecipeVersionStatus.Released, version_name="1.0.0"
    )
    recipe_version_query_service_mock.get_recipe_version.return_value = recipe_version_entity

    # ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        deploy_pipeline_command_handler.handle(
            command=deploy_pipeline_command,
            logger=logger_mock,
            pipeline_qry_srv=pipeline_query_service_mock,
            pipeline_srv=pipeline_service_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
            uow=uow_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(
        "Infrastructure configuration ARN should match ^arn:aws[^:]*:imagebuilder:[^:]+:(?:[0-9]{12}|aws):infrastructure-configuration/[a-z0-9-_]+$ pattern."
    )
    generic_repo_mock.update_attributes.assert_called_with(
        pipeline.PipelinePrimaryKey(
            projectId=deploy_pipeline_command.projectId.value,
            pipelineId=deploy_pipeline_command.pipelineId.value,
        ),
        distributionConfigArn=get_test_pipeline_distribution_config_arn(),
        status=pipeline.PipelineStatus.Failed,
    )
    pipeline_service_mock.create_distribution_config.assert_called_with(
        description=f"Distribution configuration for {pipeline_entity.pipelineName} pipeline.",
        name=pipeline_entity.pipelineId,
        image_tags={"Name": f"Version {recipe_version_entity.recipeVersionName} of {recipe_version_entity.recipeName}"},
    )
    uow_mock.commit.assert_called()


@pytest.mark.parametrize("pipeline_arn", (None, "", "a"))
def test_deploy_pipeline_command_handler_raise_an_exception_if_pipeline_arn_is_invalid(
    generic_repo_mock,
    get_deploy_pipeline_command,
    get_pipeline_entity,
    get_test_pipeline_distribution_config_arn,
    get_test_pipeline_infrastructure_config_arn,
    get_test_recipe_version_with_specific_version_name_and_status,
    logger_mock,
    pipeline_arn,
    pipeline_query_service_mock,
    pipeline_service_mock,
    recipe_version_query_service_mock,
    uow_mock,
):
    # ARRANGE
    deploy_pipeline_command = get_deploy_pipeline_command()
    pipeline_entity = get_pipeline_entity()
    pipeline_query_service_mock.get_pipeline.return_value = pipeline_entity
    pipeline_service_mock.create_distribution_config.return_value = get_test_pipeline_distribution_config_arn()
    pipeline_service_mock.create_infrastructure_config.return_value = get_test_pipeline_infrastructure_config_arn()
    pipeline_service_mock.create_pipeline.return_value = pipeline_arn
    recipe_version_entity = get_test_recipe_version_with_specific_version_name_and_status(
        status=recipe_version.RecipeVersionStatus.Released, version_name="1.0.0"
    )
    recipe_version_query_service_mock.get_recipe_version.return_value = recipe_version_entity

    # ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        deploy_pipeline_command_handler.handle(
            command=deploy_pipeline_command,
            logger=logger_mock,
            pipeline_qry_srv=pipeline_query_service_mock,
            pipeline_srv=pipeline_service_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
            uow=uow_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(
        "Pipeline ARN should match ^arn:aws[^:]*:imagebuilder:[^:]+:(?:[0-9]{12}|aws):image-pipeline/[a-z0-9-_]+$ pattern."
    )
    generic_repo_mock.update_attributes.assert_called_with(
        pipeline.PipelinePrimaryKey(
            projectId=deploy_pipeline_command.projectId.value,
            pipelineId=deploy_pipeline_command.pipelineId.value,
        ),
        distributionConfigArn=get_test_pipeline_distribution_config_arn(),
        infrastructureConfigArn=get_test_pipeline_infrastructure_config_arn(),
        status=pipeline.PipelineStatus.Failed,
    )
    pipeline_service_mock.create_distribution_config.assert_called_with(
        description=f"Distribution configuration for {pipeline_entity.pipelineName} pipeline.",
        name=pipeline_entity.pipelineId,
        image_tags={"Name": f"Version {recipe_version_entity.recipeVersionName} of {recipe_version_entity.recipeName}"},
    )
    pipeline_service_mock.create_infrastructure_config.assert_called_with(
        description=f"Infrastructure configuration for {pipeline_entity.pipelineName} pipeline.",
        instance_types=pipeline_entity.buildInstanceTypes,
        name=pipeline_entity.pipelineId,
    )
    uow_mock.commit.assert_called()
