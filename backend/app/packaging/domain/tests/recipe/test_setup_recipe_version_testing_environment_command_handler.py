import logging
from itertools import product

import assertpy
import pytest
from freezegun import freeze_time

from app.packaging.domain.command_handlers.recipe import (
    setup_recipe_version_testing_environment_command_handler,
)
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.recipe import recipe_version_test_execution


@pytest.mark.parametrize(
    "platform, architecture, os_version, instance_ids, desired_command_ids",
    (
        (
            "Linux",
            ["amd64"],
            ["Ubuntu 24"],
            ["i-01234567890abcdef"],
            ["ef7fdfd8-9b57-4151-a15c-000000000000"],
        ),
        (
            "Linux",
            ["amd64"],
            ["Ubuntu 24"],
            ["i-01234567890abcdef"],
            ["ef7fdfd8-9b57-4151-a15c-000000000000"],
        ),
        (
            "Linux",
            ["amd64", "arm64"],
            ["Ubuntu 24"],
            ["i-01234567890abcdef", "i-56789012345abcdef"],
            [
                "ef7fdfd8-9b57-4151-a15c-000000000000",
                "ef7fdfd8-9b57-4151-a15c-222222222222",
            ],
        ),
    ),
)
@freeze_time("2023-09-29")
def test_handle_should_setup_component_version_testing_environment(
    generic_repo_mock,
    recipe_version_test_execution_query_service_mock,
    recipe_version_testing_service_mock,
    get_test_recipe_version_test_execution_with_specific_instance_id_architecture_os_version_and_platform,
    setup_recipe_version_testing_environment_command_mock,
    uow_mock,
    platform,
    architecture,
    os_version,
    instance_ids,
    desired_command_ids,
    get_test_recipe_version_id,
    get_test_test_execution_id,
    mock_recipe_version_object,
):
    # ARRANGE
    for index, value in enumerate(product(architecture, os_version)):
        recipe_version_test_execution_query_service_mock.get_recipe_version_test_execution.return_value = (
            get_test_recipe_version_test_execution_with_specific_instance_id_architecture_os_version_and_platform(
                architecture=value[0],
                instance_id=instance_ids[index],
                os_version=value[1],
                platform=platform,
                mock_recipe_version_object=mock_recipe_version_object,
            )
        )
        recipe_version_testing_service_mock.setup_testing_environment.return_value = desired_command_ids[index]

        # ACT
        setup_recipe_version_testing_environment_command_handler.handle(
            command=setup_recipe_version_testing_environment_command_mock,
            recipe_version_test_execution_qry_srv=recipe_version_test_execution_query_service_mock,
            recipe_version_testing_srv=recipe_version_testing_service_mock,
            logger=logging.getLogger(),
            uow=uow_mock,
        )

    # ASSERT
    for index, value in enumerate(product(architecture, os_version)):
        instance_id = instance_ids[index]

        recipe_version_testing_service_mock.setup_testing_environment.assert_any_call(
            architecture=value[0],
            instance_id=instance_id,
            os_version=value[1],
            platform=platform,
        )
        generic_repo_mock.update_attributes.assert_any_call(
            recipe_version_test_execution.RecipeVersionTestExecutionPrimaryKey(
                recipeVersionId=get_test_recipe_version_id,
                testExecutionId=get_test_test_execution_id,
                instanceId=instance_id,
            ),
            setupCommandId=desired_command_ids[index],
            setupCommandStatus=recipe_version_test_execution.RecipeVersionTestExecutionCommandStatus.Pending,
            lastUpdateDate="2023-09-29T00:00:00+00:00",
            status=recipe_version_test_execution.RecipeVersionTestExecutionStatus.Running,
        )
    uow_mock.commit.assert_called()


@pytest.mark.parametrize(
    "platform, architecture, os_versions, instance_ids, setup_results",
    (
        (
            "Linux",
            ["amd64"],
            ["Ubuntu 24"],
            ["i-1234567890"],
            [Exception("Setup failed")],
        ),
        (
            "Linux",
            ["amd64"],
            ["Ubuntu 24"],
            ["i-01234567890abcdef"],
            [Exception("Setup failed")],
        ),
        (
            "Linux",
            ["amd64", "arm64"],
            ["Ubuntu 24"],
            [
                "i-01234567890abcdef",
                "i-56789012345abcdef",
            ],
            [
                "ef7fdfd8-9b57-4151-a15c-000000000000",
                Exception("Setup failed"),
            ],
        ),
    ),
)
def test_handle_should_raise_exception_when_environment_setup_fails(
    get_test_recipe_version_test_execution_with_specific_instance_id_architecture_os_version_and_platform,
    setup_recipe_version_testing_environment_command_mock,
    recipe_version_test_execution_query_service_mock,
    mock_recipe_version_object,
    recipe_version_testing_service_mock,
    uow_mock,
    platform,
    architecture,
    os_versions,
    instance_ids,
    setup_results,
):
    # ARRANGE
    for index, value in enumerate(product(architecture, os_versions)):
        recipe_version_test_execution_query_service_mock.get_recipe_version_test_execution.return_value = (
            get_test_recipe_version_test_execution_with_specific_instance_id_architecture_os_version_and_platform(
                architecture=value[0],
                instance_id=instance_ids[index],
                os_version=value[1],
                platform=platform,
                mock_recipe_version_object=mock_recipe_version_object,
            )
        )
        recipe_version_testing_service_mock.setup_testing_environment.return_value = setup_results[index]

        # ACT
        try:
            setup_recipe_version_testing_environment_command_handler.handle(
                command=setup_recipe_version_testing_environment_command_mock,
                recipe_version_test_execution_qry_srv=recipe_version_test_execution_query_service_mock,
                recipe_version_testing_srv=recipe_version_testing_service_mock,
                logger=logging.getLogger(),
                uow=uow_mock,
            )
        # ASSERT
        except domain_exception.DomainException as e:
            assertpy.assert_that(str(e)).is_equal_to(f"Testing environment setup failed for {instance_ids[index]}.")
