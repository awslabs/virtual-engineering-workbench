import assertpy

from app.packaging.entrypoints.recipe_version_testing.model import step_function_model


def test_handle_launch_test_environment(
    mock_dependencies,
    lambda_context,
    mock_project_id,
    mock_recipe_id,
    mock_recipe_version_id,
    mock_test_execution_id,
):
    # ARRANGE
    from app.packaging.entrypoints.recipe_version_testing import handler

    handler.dependencies = mock_dependencies

    request = step_function_model.LaunchTestEnvironmentRequest(
        projectId=mock_project_id,
        recipeId=mock_recipe_id,
        recipeVersionId=mock_recipe_version_id,
        testExecutionId=mock_test_execution_id,
    )

    # ACT
    response = handler.handler(request.dict(by_alias=True), lambda_context)

    # ASSERT
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response).is_equal_to(step_function_model.LaunchTestEnvironmentResponse().dict(by_alias=True))


def test_check_test_environment_launch_status(
    mock_dependencies,
    lambda_context,
    mock_recipe_version_id,
    mock_test_execution_id,
    mock_instance_status,
):
    # ARRANGE
    from app.packaging.entrypoints.recipe_version_testing import handler

    handler.dependencies = mock_dependencies

    request = step_function_model.CheckTestEnvironmentLaunchStatusRequest(
        recipeVersionId=mock_recipe_version_id,
        testExecutionId=mock_test_execution_id,
    )

    # ACT
    response = handler.handler(request.dict(by_alias=True), lambda_context)

    # ASSERT
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response).is_equal_to(
        step_function_model.CheckTestEnvironmentLaunchStatusResponse(instanceStatus=mock_instance_status).dict(
            by_alias=True
        )
    )


def test_setup_test_environment(
    mock_dependencies,
    lambda_context,
    mock_recipe_version_id,
    mock_test_execution_id,
):
    # ARRANGE
    from app.packaging.entrypoints.recipe_version_testing import handler

    handler.dependencies = mock_dependencies

    request = step_function_model.SetupTestEnvironmentRequest(
        recipeVersionId=mock_recipe_version_id,
        testExecutionId=mock_test_execution_id,
    )

    # ACT
    response = handler.handler(request.dict(by_alias=True), lambda_context)

    # ASSERT
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response).is_equal_to(step_function_model.SetupTestEnvironmentResponse().dict(by_alias=True))


def test_check_test_environment_setup_status(
    mock_dependencies,
    lambda_context,
    mock_recipe_version_id,
    mock_test_execution_id,
    mock_command_status,
):
    # ARRANGE
    from app.packaging.entrypoints.recipe_version_testing import handler

    handler.dependencies = mock_dependencies

    request = step_function_model.CheckTestEnvironmentSetupStatusRequest(
        recipeVersionId=mock_recipe_version_id,
        testExecutionId=mock_test_execution_id,
    )

    # ACT
    response = handler.handler(request.dict(by_alias=True), lambda_context)

    # ASSERT
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response).is_equal_to(
        step_function_model.CheckTestEnvironmentSetupStatusResponse(setupCommandStatus=mock_command_status).dict(
            by_alias=True
        )
    )


def test_run_recipe_test(
    mock_dependencies,
    lambda_context,
    mock_recipe_id,
    mock_recipe_version_id,
    mock_test_execution_id,
):
    # ARRANGE
    from app.packaging.entrypoints.recipe_version_testing import handler

    handler.dependencies = mock_dependencies

    request = step_function_model.RunRecipeVersionTestRequest(
        recipeId=mock_recipe_id,
        recipeVersionId=mock_recipe_version_id,
        testExecutionId=mock_test_execution_id,
    )

    # ACT
    response = handler.handler(request.dict(by_alias=True), lambda_context)

    # ASSERT
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response).is_equal_to(step_function_model.RunRecipeVersionTestResponse().dict(by_alias=True))


def test_check_recipe_test_status(
    mock_dependencies,
    lambda_context,
    mock_recipe_version_id,
    mock_test_execution_id,
    mock_command_status,
):
    # ARRANGE
    from app.packaging.entrypoints.recipe_version_testing import handler

    handler.dependencies = mock_dependencies

    request = step_function_model.CheckRecipeVersionTestStatusRequest(
        recipeVersionId=mock_recipe_version_id,
        testExecutionId=mock_test_execution_id,
    )

    # ACT
    response = handler.handler(request.dict(by_alias=True), lambda_context)

    # ASSERT
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response).is_equal_to(
        step_function_model.CheckRecipeVersionTestStatusResponse(
            testCommandStatus=mock_command_status,
        ).dict(by_alias=True)
    )


def test_complete_recipe_test(
    mock_dependencies,
    lambda_context,
    mock_project_id,
    mock_recipe_id,
    mock_recipe_version_id,
    mock_test_execution_id,
    mock_recipe_version_test_status,
):
    # ARRANGE
    from app.packaging.entrypoints.recipe_version_testing import handler

    handler.dependencies = mock_dependencies

    request = step_function_model.CompleteRecipeVersionTestRequest(
        projectId=mock_project_id,
        recipeId=mock_recipe_id,
        recipeVersionId=mock_recipe_version_id,
        testExecutionId=mock_test_execution_id,
    )

    # ACT
    response = handler.handler(request.dict(by_alias=True), lambda_context)

    # ASSERT
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response).is_equal_to(
        step_function_model.CompleteRecipeVersionTestResponse(
            recipeVersionTestStatus=mock_recipe_version_test_status,
        ).dict(by_alias=True)
    )
