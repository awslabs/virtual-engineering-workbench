from app.shared.adapters.boto import aws_durable_functions_service


def test_send_callback_failure_should_mark_durable_function_failed(
    provider, mock_send_lambda_callback_failure_request, mock_moto_error_calls
):
    # ARRANGE
    svc = aws_durable_functions_service.AWSDurableFunctionsService(lambda_provider=provider.client("lambda"))

    # ACT

    svc.send_callback_failure(callback_token="token", error_type="error-msg", error_message="cause-msg")

    # ASSERT
    mock_send_lambda_callback_failure_request.assert_called_once_with(
        CallbackId="token", Error={"ErrorMessage": "cause-msg", "ErrorType": "error-msg"}
    )


def test_send_callback_success_should_mark_durable_function_succeeded(
    provider, mock_send_lambda_callback_success_request, mock_moto_error_calls
):
    # ARRANGE
    svc = aws_durable_functions_service.AWSDurableFunctionsService(lambda_provider=provider.client("lambda"))

    # ACT

    svc.send_callback_success(callback_token="token", result={"a": "b"})

    # ASSERT
    mock_send_lambda_callback_success_request.assert_called_once_with(CallbackId="token", Result=b'{"a": "b"}')
