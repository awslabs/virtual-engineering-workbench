import logging

import assertpy
import pytest
from freezegun import freeze_time

from app.packaging.domain.command_handlers.recipe import (
    run_recipe_version_testing_command_handler,
)
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component_version
from app.packaging.domain.model.recipe import recipe_version_test_execution
from app.packaging.domain.tests.conftest import (
    TEST_RECIPE_ID,
    TEST_RECIPE_TEST_S3_BUCKET_NAME,
    TEST_RECIPE_VERSION_ID,
)


@pytest.fixture
def get_test_recipe_version_test_execution_with_specific_instance_id():
    def _get_test_recipe_version_test_execution_with_specific_instance_id(
        instance_id: str,
        mock_recipe_version_object,
        mock_recipe_object,
        test_execution_id: str,
        status: recipe_version_test_execution.RecipeVersionTestExecutionStatus = recipe_version_test_execution.RecipeVersionTestExecutionStatus.Pending,
    ):
        return recipe_version_test_execution.RecipeVersionTestExecution(
            recipeVersionId=mock_recipe_version_object.recipeVersionId,
            testExecutionId=test_execution_id,
            instanceId=instance_id,
            instanceArchitecture=mock_recipe_object.recipeArchitecture,
            instanceImageUpstreamId=mock_recipe_version_object.parentImageUpstreamId,
            instanceOsVersion=mock_recipe_object.recipeOsVersion,
            instancePlatform=mock_recipe_object.recipePlatform,
            instanceStatus=recipe_version_test_execution.RecipeVersionTestExecutionInstanceStatus.Connected,
            setupCommandError="This is an example error",
            setupCommandId="ef7fdfd8-9b57-4151-a15c-999999999999",
            setupCommandOutput="This is an example output",
            setupCommandStatus=recipe_version_test_execution.RecipeVersionTestExecutionCommandStatus.Success,
            createDate="2000-01-01",
            lastUpdateDate="2000-01-01",
            status=status,
        )

    return _get_test_recipe_version_test_execution_with_specific_instance_id


def side_effect(component_id: str, version_id: str):
    return component_version.ComponentVersion(
        componentId=component_id,
        componentVersionId=version_id,
        componentVersionName="1.0.0",
        componentName="test-component",
        componentVersionDescription="Test description",
        componentBuildVersionArn=f"arn::{component_id}/{version_id}",
        componentVersionS3Uri="s3://test/component.yaml",
        componentPlatform="Linux",
        componentSupportedArchitectures=["arm64"],
        componentSupportedOsVersions=["Ubuntu 24"],
        status=component_version.ComponentVersionStatus.Validated,
        createDate="2023-10-27T00:00:00+00:00",
        createdBy="T000001",
        lastUpdateDate="2023-10-27T00:00:00+00:00",
        lastUpdatedBy="T000001",
    )


@freeze_time("2023-09-29")
def test_handle_should_run_recipe_version_testing(
    generic_repo_mock,
    recipe_version_query_service_mock,
    recipe_version_test_execution_query_service_mock,
    recipe_version_testing_service_mock,
    get_test_recipe_version_test_execution_with_specific_instance_id,
    run_recipe_version_testing_command_mock,
    uow_mock,
    mock_recipe_object,
    mock_recipe_version_object,
    get_test_instance_id,
    get_test_execution_id,
    get_test_command_id,
    component_version_query_service_mock,
):
    # ARRANGE
    recipe_version_query_service_mock.get_recipe_version.return_value = mock_recipe_version_object
    recipe_version_test_execution_query_service_mock.get_recipe_version_test_execution.return_value = (
        get_test_recipe_version_test_execution_with_specific_instance_id(
            get_test_instance_id,
            mock_recipe_version_object,
            mock_recipe_object,
            get_test_execution_id,
        )
    )
    recipe_version_testing_service_mock.run_testing.return_value = get_test_command_id
    recipe_version_testing_service_mock.get_recipe_test_bucket_name.return_value = TEST_RECIPE_TEST_S3_BUCKET_NAME
    component_version_query_service_mock.get_component_version.side_effect = side_effect

    # ACT
    run_recipe_version_testing_command_handler.handle(
        command=run_recipe_version_testing_command_mock,
        recipe_version_qry_srv=recipe_version_query_service_mock,
        recipe_version_test_execution_qry_srv=recipe_version_test_execution_query_service_mock,
        recipe_version_testing_srv=recipe_version_testing_service_mock,
        component_version_qry_srv=component_version_query_service_mock,
        logger=logging.getLogger(),
        uow=uow_mock,
    )

    # ASSERT

    recipe_version_testing_service_mock.run_testing.assert_any_call(
        architecture=mock_recipe_object.recipeArchitecture,
        instance_id=get_test_instance_id,
        os_version=mock_recipe_object.recipeOsVersion,
        platform=mock_recipe_object.recipePlatform,
        recipe_version_component_arn="arn:aws:imagebuilder:us-east-1:123456789123:component/comp-12345/1.0.0/1",
        recipe_id=TEST_RECIPE_ID,
        recipe_version_id=TEST_RECIPE_VERSION_ID,
    )
    generic_repo_mock.update_attributes.assert_any_call(
        recipe_version_test_execution.RecipeVersionTestExecutionPrimaryKey(
            recipeVersionId=mock_recipe_version_object.recipeVersionId,
            testExecutionId=get_test_execution_id,
        ),
        testCommandId=get_test_command_id,
        testCommandStatus=recipe_version_test_execution.RecipeVersionTestExecutionCommandStatus.Pending,
        lastUpdateDate="2023-09-29T00:00:00+00:00",
        status=recipe_version_test_execution.RecipeVersionTestExecutionStatus.Running,
        s3LogLocation=f"s3://{TEST_RECIPE_TEST_S3_BUCKET_NAME}/{TEST_RECIPE_ID}/{TEST_RECIPE_VERSION_ID}/{get_test_instance_id}/console.log",
    )
    uow_mock.commit.assert_called()


def test_handle_should_raise_exception_when_test_fails(
    recipe_version_query_service_mock,
    recipe_version_test_execution_query_service_mock,
    recipe_version_testing_service_mock,
    get_test_recipe_version_test_execution_with_specific_instance_id,
    run_recipe_version_testing_command_mock,
    uow_mock,
    mock_recipe_object,
    mock_recipe_version_object,
    get_test_instance_id,
    get_test_execution_id,
    component_version_query_service_mock,
):
    # ARRANGE
    test_result = Exception("Test failed")
    recipe_version_query_service_mock.get_recipe_version.return_value = mock_recipe_version_object
    recipe_version_test_execution_query_service_mock.get_recipe_version_test_execution.return_value = (
        get_test_recipe_version_test_execution_with_specific_instance_id(
            get_test_instance_id,
            mock_recipe_version_object,
            mock_recipe_object,
            get_test_execution_id,
        )
    )
    recipe_version_testing_service_mock.run_testing.side_effect = test_result

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        run_recipe_version_testing_command_handler.handle(
            command=run_recipe_version_testing_command_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
            recipe_version_test_execution_qry_srv=recipe_version_test_execution_query_service_mock,
            recipe_version_testing_srv=recipe_version_testing_service_mock,
            component_version_qry_srv=component_version_query_service_mock,
            logger=logging.getLogger(),
            uow=uow_mock,
        )

    # ASSERT
    if isinstance(test_result, Exception):
        assertpy.assert_that(str(e.value)).is_equal_to(
            f"Running tests on {get_test_instance_id} for {mock_recipe_object.recipeId} failed."
        )
