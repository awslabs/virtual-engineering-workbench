from datetime import datetime, timedelta

import assertpy
import pytest
from freezegun import freeze_time

from app.packaging.domain.command_handlers.recipe import (
    check_recipe_version_testing_environment_launch_status_command_handler,
)
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.recipe import recipe_version_test_execution


@pytest.mark.parametrize(
    "testing_environment, desired_environment_status, desired_recipe_version_testing_status",
    (
        (
            {"i-01234567890abcdef": recipe_version_test_execution.RecipeVersionTestExecutionInstanceStatus.Connected},
            recipe_version_test_execution.RecipeVersionTestExecutionInstanceStatus.Connected,
            recipe_version_test_execution.RecipeVersionTestExecutionStatus.Running,
        ),
        (
            {
                "i-01234567890abcdef": recipe_version_test_execution.RecipeVersionTestExecutionInstanceStatus.Disconnected
            },
            recipe_version_test_execution.RecipeVersionTestExecutionInstanceStatus.Disconnected,
            None,
        ),
    ),
)
@freeze_time("2023-09-29")
def test_handle_should_check_recipe_version_testing_launch_status(
    check_recipe_version_testing_environment_launch_status_command_mock,
    recipe_version_test_execution_query_service_mock,
    recipe_version_test_execution_repo_mock,
    recipe_version_testing_service_mock,
    get_test_recipe_version_test_execution_with_specific_instance_id_and_status,
    generic_repo_mock,
    uow_mock,
    testing_environment,
    desired_environment_status,
    desired_recipe_version_testing_status,
    mock_recipe_object,
    mock_recipe_version_object,
    get_test_recipe_version_id,
    get_test_execution_id,
):
    # ARRANGE
    instance_id = list(testing_environment.keys())[0]
    instance_status = list(testing_environment.values())[0]
    recipe_version_test_execution_query_service_mock.get_recipe_version_test_execution.return_value = (
        get_test_recipe_version_test_execution_with_specific_instance_id_and_status(
            instance_id=instance_id,
            instance_status=instance_status,
            mock_recipe_object=mock_recipe_object,
            mock_recipe_version_object=mock_recipe_version_object,
            status=(
                desired_recipe_version_testing_status
                if desired_recipe_version_testing_status
                else recipe_version_test_execution.RecipeVersionTestExecutionStatus.Pending
            ),
        )
    )
    recipe_version_testing_service_mock.get_testing_environment_creation_time.return_value = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    recipe_version_testing_service_mock.get_testing_environment_status.return_value = instance_status

    # ACT
    testing_environment_launch_status = check_recipe_version_testing_environment_launch_status_command_handler.handle(
        command=check_recipe_version_testing_environment_launch_status_command_mock,
        recipe_version_test_execution_qry_srv=recipe_version_test_execution_query_service_mock,
        recipe_version_testing_srv=recipe_version_testing_service_mock,
        uow=uow_mock,
    )

    # ASSERT
    assertpy.assert_that(testing_environment_launch_status).is_equal_to(desired_environment_status)

    recipe_version_testing_service_mock.get_testing_environment_status.assert_any_call(
        instance_id=instance_id,
    )

    if desired_recipe_version_testing_status:
        generic_repo_mock.update_attributes.assert_any_call(
            recipe_version_test_execution.RecipeVersionTestExecutionPrimaryKey(
                recipeVersionId=get_test_recipe_version_id,
                testExecutionId=get_test_execution_id,
            ),
            instanceStatus=instance_status,
            lastUpdateDate="2023-09-29T00:00:00+00:00",
            status=desired_recipe_version_testing_status,
        )
        uow_mock.commit.assert_called()
    else:
        uow_mock.commit.assert_not_called()


@pytest.mark.parametrize(
    "testing_environment, time_delta_minutes",
    (
        (
            {
                "i-01234567890abcdef": recipe_version_test_execution.RecipeVersionTestExecutionInstanceStatus.Disconnected,
            },
            10,
        ),
        (
            {
                "i-56789012345ghijkl": recipe_version_test_execution.RecipeVersionTestExecutionInstanceStatus.Disconnected,
            },
            15,
        ),
    ),
)
def test_handle_should_throw_if_launch_times_out(
    check_recipe_version_testing_environment_launch_status_command_mock,
    recipe_version_test_execution_query_service_mock,
    recipe_version_test_execution_repo_mock,
    recipe_version_testing_service_mock,
    get_test_recipe_version_test_execution_with_specific_instance_id_and_status,
    uow_mock,
    testing_environment,
    mock_recipe_object,
    mock_recipe_version_object,
    time_delta_minutes,
):
    # ARRANGE
    instance_id = list(testing_environment.keys())[0]
    instance_status = list(testing_environment.values())[0]
    recipe_version_test_execution_query_service_mock.get_recipe_version_test_execution.return_value = (
        get_test_recipe_version_test_execution_with_specific_instance_id_and_status(
            instance_id=instance_id,
            instance_status=instance_status,
            mock_recipe_object=mock_recipe_object,
            mock_recipe_version_object=mock_recipe_version_object,
        )
    )
    recipe_version_testing_service_mock.get_testing_environment_creation_time.return_value = (
        datetime.now() - timedelta(minutes=time_delta_minutes)
    ).strftime("%Y-%m-%d %H:%M:%S%z")
    recipe_version_testing_service_mock.get_testing_environment_status.return_value = instance_status

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        check_recipe_version_testing_environment_launch_status_command_handler.handle(
            command=check_recipe_version_testing_environment_launch_status_command_mock,
            recipe_version_test_execution_qry_srv=recipe_version_test_execution_query_service_mock,
            recipe_version_testing_srv=recipe_version_testing_service_mock,
            uow=uow_mock,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to("Testing environment launch has timed out.")
