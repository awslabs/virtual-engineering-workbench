import assertpy

from app.packaging.entrypoints.component_version_testing.model import step_function_model


def test_handle_launch_test_environment(
    mock_dependencies,
    lambda_context,
    mock_component_id,
    mock_component_version_id,
    mock_test_execution_id,
):
    # ARRANGE
    from app.packaging.entrypoints.component_version_testing import handler

    handler.dependencies = mock_dependencies

    request = step_function_model.LaunchTestEnvironmentRequest(
        componentId=mock_component_id,
        componentVersionId=mock_component_version_id,
        testExecutionId=mock_test_execution_id,
    )

    # ACT
    response = handler.handler(request.model_dump(by_alias=True), lambda_context)

    # ASSERT
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response).is_equal_to(
        step_function_model.LaunchTestEnvironmentResponse().model_dump(by_alias=True)
    )


def test_check_test_environment_launch_status(
    mock_dependencies,
    lambda_context,
    mock_component_version_id,
    mock_test_execution_id,
    mock_instances_status,
):
    # ARRANGE
    from app.packaging.entrypoints.component_version_testing import handler

    handler.dependencies = mock_dependencies

    request = step_function_model.CheckTestEnvironmentLaunchStatusRequest(
        componentVersionId=mock_component_version_id,
        testExecutionId=mock_test_execution_id,
    )

    # ACT
    response = handler.handler(request.model_dump(by_alias=True), lambda_context)

    # ASSERT
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response).is_equal_to(
        step_function_model.CheckTestEnvironmentLaunchStatusResponse(instancesStatus=mock_instances_status).model_dump(
            by_alias=True
        )
    )


def test_setup_test_environment(
    mock_dependencies,
    lambda_context,
    mock_component_version_id,
    mock_test_execution_id,
):
    # ARRANGE
    from app.packaging.entrypoints.component_version_testing import handler

    handler.dependencies = mock_dependencies

    request = step_function_model.SetupTestEnvironmentRequest(
        componentVersionId=mock_component_version_id,
        testExecutionId=mock_test_execution_id,
    )

    # ACT
    response = handler.handler(request.model_dump(by_alias=True), lambda_context)

    # ASSERT
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response).is_equal_to(
        step_function_model.SetupTestEnvironmentResponse().model_dump(by_alias=True)
    )


def test_check_test_environment_setup_status(
    mock_dependencies,
    lambda_context,
    mock_component_version_id,
    mock_test_execution_id,
    mock_commands_status,
):
    # ARRANGE
    from app.packaging.entrypoints.component_version_testing import handler

    handler.dependencies = mock_dependencies

    request = step_function_model.CheckTestEnvironmentSetupStatusRequest(
        componentVersionId=mock_component_version_id,
        testExecutionId=mock_test_execution_id,
    )

    # ACT
    response = handler.handler(request.model_dump(by_alias=True), lambda_context)

    # ASSERT
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response).is_equal_to(
        step_function_model.CheckTestEnvironmentSetupStatusResponse(
            setupCommandsStatus=mock_commands_status
        ).model_dump(by_alias=True)
    )


def test_run_component_test(
    mock_dependencies,
    lambda_context,
    mock_component_id,
    mock_component_version_id,
    mock_test_execution_id,
):
    # ARRANGE
    from app.packaging.entrypoints.component_version_testing import handler

    handler.dependencies = mock_dependencies

    request = step_function_model.RunComponentVersionTestRequest(
        componentId=mock_component_id,
        componentVersionId=mock_component_version_id,
        testExecutionId=mock_test_execution_id,
    )

    # ACT
    response = handler.handler(request.model_dump(by_alias=True), lambda_context)

    # ASSERT
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response).is_equal_to(
        step_function_model.RunComponentVersionTestResponse().model_dump(by_alias=True)
    )


def test_check_component_test_status(
    mock_dependencies,
    lambda_context,
    mock_component_version_id,
    mock_test_execution_id,
    mock_commands_status,
):
    # ARRANGE
    from app.packaging.entrypoints.component_version_testing import handler

    handler.dependencies = mock_dependencies

    request = step_function_model.CheckComponentVersionTestStatusRequest(
        componentVersionId=mock_component_version_id,
        testExecutionId=mock_test_execution_id,
    )

    # ACT
    response = handler.handler(request.model_dump(by_alias=True), lambda_context)

    # ASSERT
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response).is_equal_to(
        step_function_model.CheckComponentVersionTestStatusResponse(
            testCommandsStatus=mock_commands_status,
        ).model_dump(by_alias=True)
    )


def test_complete_component_test(
    mock_dependencies,
    lambda_context,
    mock_component_id,
    mock_component_version_id,
    mock_test_execution_id,
    mock_component_version_test_status,
):
    # ARRANGE
    from app.packaging.entrypoints.component_version_testing import handler

    handler.dependencies = mock_dependencies

    request = step_function_model.CompleteComponentVersionTestRequest(
        componentId=mock_component_id,
        componentVersionId=mock_component_version_id,
        testExecutionId=mock_test_execution_id,
    )

    # ACT
    response = handler.handler(request.model_dump(by_alias=True), lambda_context)

    # ASSERT
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response).is_equal_to(
        step_function_model.CompleteComponentVersionTestResponse(
            componentVersionTestStatus=mock_component_version_test_status,
        ).model_dump(by_alias=True)
    )
