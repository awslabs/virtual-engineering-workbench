from app.shared.adapters.boto import aws_step_functions_service


def test_send_callback_failure_should_mark_sfn_task_failed(
    provider, mock_send_task_failure_request, mock_moto_error_calls
):
    # ARRANGE
    svc = aws_step_functions_service.AWSStepFunctionsService(sfn_provider=provider.client("stepfunctions"))

    # ACT

    svc.send_callback_failure(callback_token="token", error_type="error-msg", error_message="cause-msg")

    # ASSERT
    mock_send_task_failure_request.assert_called_once_with(taskToken="token", error="error-msg", cause="cause-msg")


def test_send_callback_success_should_mark_sfn_task_succeeded(
    provider, mock_send_task_success_request, mock_moto_error_calls
):
    # ARRANGE
    svc = aws_step_functions_service.AWSStepFunctionsService(sfn_provider=provider.client("stepfunctions"))

    # ACT

    svc.send_callback_success(callback_token="token", result={"a": "b"})

    # ASSERT
    mock_send_task_success_request.assert_called_once_with(taskToken="token", output="{'a': 'b'}")
