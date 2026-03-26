import logging
import typing
from typing import Self
from unittest import mock

import pytest
from assertpy import assert_that
from aws_lambda_powertools.utilities.data_classes import EventBridgeEvent, api_gateway_authorizer_event
from pydantic import Field, ValidationError

from app.shared.adapters.boto import orchestration_service
from app.shared.adapters.message_bus import command_bus
from app.shared.ddd import value_object
from app.shared.middleware import event_handler, event_handler_middleware
from app.shared.middleware.custom_events import scheduled_job_event, step_function_event


class FakeEvent(event_handler.EventBase):
    fake_param: str = Field(..., alias="FakeParam")


class FakeEventNoParams(event_handler.EventBase):
    pass


class FakeValueObject(value_object.ValueObject):
    value: str

    @classmethod
    def from_obj(cls, value: typing.Any | None) -> Self:
        if isinstance(value, cls):
            return value

        if not isinstance(value, str):
            raise ValidationError("value must be a string")

        if value is None:
            raise Exception("cannot be empty")

        return cls(value=value)


class FakeCommand(command_bus.SagaCommand):
    some_param: FakeValueObject = Field(..., alias="someParam")


def test_event_bridge_resolver_when_exists_should_invoke_correct_handler(lambda_context):
    # ARRANGE
    logger = mock.create_autospec(spec=logging.Logger)
    app = event_handler.EventBridgeEventResolver(logger=logger)
    passed_evt: typing.Optional[FakeEvent] = None

    @app.handle(FakeEvent)
    def fake_event_handler(evt: FakeEvent):
        nonlocal passed_evt
        passed_evt = evt

    event = EventBridgeEvent({"detail-type": "FakeEvent", "detail": {"FakeParam": "Test"}})

    # ACT
    app.resolve(event, lambda_context)

    # ASSERT
    assert_that(passed_evt).is_not_none()
    assert_that(passed_evt.fake_param).is_equal_to("Test")


def test_event_bridge_resolver_when_has_middleware_should_invoke_middleware(lambda_context):
    # ARRANGE
    middleware_called = False
    middleware2_called = False

    def __middleware(event_name: str, event: typing.Any, next: event_handler.HandlerFunc):
        nonlocal middleware_called
        middleware_called = True
        return next(event_name, event)

    def __middleware2(event_name: str, event: typing.Any, next: event_handler.HandlerFunc):
        nonlocal middleware2_called
        middleware2_called = True
        return next(event_name, event)

    logger = mock.create_autospec(spec=logging.Logger)
    app = event_handler.EventBridgeEventResolver(logger=logger, middleware=[__middleware, __middleware2])
    passed_evt: typing.Optional[FakeEvent] = None

    @app.handle(FakeEvent)
    def fake_event_handler(evt: FakeEvent):
        nonlocal passed_evt
        passed_evt = evt

    event = EventBridgeEvent({"detail-type": "FakeEvent", "detail": {"FakeParam": "Test"}})

    # ACT
    app.resolve(event, lambda_context)

    # ASSERT
    assert_that(middleware_called).is_true()
    assert_that(middleware2_called).is_true()
    assert_that(passed_evt).is_not_none()
    assert_that(passed_evt.fake_param).is_equal_to("Test")


def test_event_bridge_resolver_when_has_orchestration_middleware_should_send_failure(lambda_context):
    # ARRANGE
    logger = mock.create_autospec(spec=logging.Logger)
    orchestration_svc = mock.create_autospec(spec=orchestration_service.OrchestrationService)
    app = event_handler.SagaEventResolver(
        logger=logger, middleware=[event_handler_middleware.use_orchestration(orchestration_svc=orchestration_svc)]
    )

    @app.handle(FakeCommand)
    def fake_event_handler(cmd: FakeCommand):
        raise Exception("Test Exception")

    event = {
        "saga-command-name": "FakeCommand",
        "saga-command": {"someParam": "Test", "callback_token": "test-callback-token"},
    }

    # ACT
    with pytest.raises(Exception):
        app.resolve(event, lambda_context)

    # ASSERT
    orchestration_svc.send_callback_failure.assert_called_once_with(
        callback_token="test-callback-token", error_type="Exception", error_message="Test Exception"
    )


def test_event_bridge_resolver_when_request_completes_should_clear_context(lambda_context):
    # ARRANGE
    logger = mock.create_autospec(spec=logging.Logger)
    app = event_handler.EventBridgeEventResolver(logger=logger)
    ctx_during_runtime = None

    @app.handle(FakeEvent)
    def fake_event_handler(evt: FakeEvent):
        app.append_context(a="b")
        nonlocal ctx_during_runtime
        ctx_during_runtime = app.context.copy()
        return {}

    event = EventBridgeEvent({"detail-type": "FakeEvent", "detail": {"FakeParam": "Test"}})

    # ACT
    app.resolve(event, lambda_context)

    # ASSERT
    assert_that(app.context).is_equal_to({})
    assert_that(ctx_during_runtime).is_equal_to({"a": "b"})


def test_event_bridge_resolver_when_request_fails_should_clear_context(lambda_context):
    # ARRANGE
    logger = mock.create_autospec(spec=logging.Logger)
    app = event_handler.EventBridgeEventResolver(logger=logger)

    @app.handle(FakeEvent)
    def fake_event_handler(evt: FakeEvent):
        app.append_context(a="b")
        raise Exception("Test")

    event = EventBridgeEvent({"detail-type": "FakeEvent", "detail": {"FakeParam": "Test"}})

    # ACT
    with pytest.raises(Exception):
        app.resolve(event, lambda_context)

    # ASSERT
    assert_that(app.context).is_equal_to({})


def test_event_bridge_resolver_when_does_not_exist_should_raise(lambda_context):
    # ARRANGE
    logger = mock.create_autospec(spec=logging.Logger)
    app = event_handler.EventBridgeEventResolver(logger=logger)

    @app.handle(FakeEvent)
    def fake_event_handler(evt: FakeEvent):
        pass

    event = EventBridgeEvent({"detail-type": "NonExistentHandler", "detail": {"FakeParam": "Test"}})

    # ACT / ASSERT
    with pytest.raises(event_handler.EventResolverException) as e:
        app.resolve(event, lambda_context)

        assert_that(str(e)).starts_with("Event handler for NonExistentHandler is not registered. ")


def test_event_bridge_resolver_when_payload_is_invalid_should_raise(lambda_context):
    # ARRANGE
    logger = mock.create_autospec(spec=logging.Logger)
    app = event_handler.EventBridgeEventResolver(logger=logger)

    @app.handle(FakeEvent)
    def fake_event_handler(evt: FakeEvent):
        pass

    event = EventBridgeEvent({"detail-type": "FakeEvent", "detail": {"FakeParamNonExistent": "Test"}})

    # ACT / ASSERT
    with pytest.raises(ValidationError):
        app.resolve(event, lambda_context)


def test_event_bridge_resolver_when_wrong_type_should_raise(lambda_context):
    # ARRANGE
    logger = mock.create_autospec(spec=logging.Logger)
    app = event_handler.EventBridgeEventResolver(logger=logger)

    @app.handle(FakeEvent)
    def fake_event_handler(evt: FakeEvent):
        pass

    event = {"detail-type": "FakeEvent", "detail": {"FakeParam": "Test"}}

    # ACT / ASSERT
    with pytest.raises(event_handler.EventResolverException):
        app.resolve(event, lambda_context)


def test_step_function_resolver_should_invoke_correct_handler(lambda_context):
    # ARRANGE
    logger = mock.create_autospec(spec=logging.Logger)
    app = event_handler.StepFunctionEventResolver(logger=logger)
    passed_evt: typing.Optional[FakeEvent] = None

    @app.handle(FakeEvent)
    def fake_event_handler(evt: FakeEvent):
        nonlocal passed_evt
        passed_evt = evt

    event = step_function_event.StepFunctionEvent({"FakeParam": "Test", "eventType": "FakeEvent"})

    # ACT
    app.resolve(event, lambda_context)

    # ASSERT
    assert_that(passed_evt).is_not_none()
    assert_that(passed_evt.fake_param).is_equal_to("Test")


def test_step_function_resolver_should_clear_context_after_completion(lambda_context):
    # ARRANGE
    logger = mock.create_autospec(spec=logging.Logger)
    app = event_handler.StepFunctionEventResolver(logger=logger)
    ctx_during_runtime = None

    @app.handle(FakeEvent)
    def fake_event_handler(evt: FakeEvent):
        app.append_context(a="b")
        nonlocal ctx_during_runtime
        ctx_during_runtime = app.context.copy()
        return {}

    event = step_function_event.StepFunctionEvent({"FakeParam": "Test", "eventType": "FakeEvent"})

    # ACT
    app.resolve(event, lambda_context)

    # ASSERT
    assert_that(app.context).is_equal_to({})
    assert_that(ctx_during_runtime).is_equal_to({"a": "b"})


def test_scheduled_job_resolver_should_invoke_correct_handler(lambda_context):
    # ARRANGE
    logger = mock.create_autospec(spec=logging.Logger)
    app = event_handler.ScheduledJobEventResolver(logger=logger)
    passed_evt: typing.Optional[FakeEvent] = None

    @app.handle(FakeEvent)
    def fake_event_handler(evt: FakeEvent):
        nonlocal passed_evt
        passed_evt = evt

    event = scheduled_job_event.ScheduledJobEvent({"jobName": "FakeEvent", "parameters": {"FakeParam": "Test"}})

    # ACT
    app.resolve(event, lambda_context)

    # ASSERT
    assert_that(passed_evt).is_not_none()
    assert_that(passed_evt.fake_param).is_equal_to("Test")


def test_scheduled_job_resolver_when_no_parameters_should_invoke_correct_handler(lambda_context):
    # ARRANGE
    logger = mock.create_autospec(spec=logging.Logger)
    app = event_handler.ScheduledJobEventResolver(logger=logger)
    passed_evt: typing.Optional[FakeEvent] = None

    @app.handle(FakeEventNoParams)
    def fake_event_handler(evt: FakeEventNoParams):
        nonlocal passed_evt
        passed_evt = evt

    event = scheduled_job_event.ScheduledJobEvent({"jobName": "FakeEventNoParams"})

    # ACT
    app.resolve(event, lambda_context)

    # ASSERT
    assert_that(passed_evt).is_not_none()


def test_scheduled_job_resolver_should_clear_context_after_completion(lambda_context):
    # ARRANGE
    logger = mock.create_autospec(spec=logging.Logger)
    app = event_handler.ScheduledJobEventResolver(logger=logger)
    ctx_during_runtime = None

    @app.handle(FakeEvent)
    def fake_event_handler(evt: FakeEvent):
        app.append_context(a="b")
        nonlocal ctx_during_runtime
        ctx_during_runtime = app.context.copy()
        return {}

    event = scheduled_job_event.ScheduledJobEvent({"jobName": "FakeEvent", "parameters": {"FakeParam": "Test"}})

    # ACT
    app.resolve(event, lambda_context)

    # ASSERT
    assert_that(app.context).is_equal_to({})
    assert_that(ctx_during_runtime).is_equal_to({"a": "b"})


def test_api_gateway_authorizer_resolver_when_exists_should_invoke_correct_handler(lambda_context):
    # ARRANGE
    logger = mock.create_autospec(spec=logging.Logger)
    app = event_handler.APIGatewayAuthorizerRequestEventResolver(logger=logger)
    passed_evt: typing.Optional[FakeEvent] = None

    @app.handle(FakeEvent)
    def fake_event_handler(evt: FakeEvent):
        nonlocal passed_evt
        passed_evt = evt

    event = api_gateway_authorizer_event.APIGatewayAuthorizerRequestEvent(
        {
            "type": "FakeEvent",
            "methodArn": "arn:aws:execute-api:us-east-1:123456789012:abcdef123/test/GET/path",
            "authorizationToken": "test-token",
            "resource": "/path",
            "path": "/path",
            "httpMethod": "GET",
            "headers": {"FakeParam": "Test"},
            "queryStringParameters": {},
            "pathParameters": {},
            "stageVariables": {},
            "version": "1.0",
        }
    )

    # ACT
    app.resolve(event, lambda_context)

    # ASSERT
    assert_that(passed_evt).is_not_none()
    assert_that(passed_evt.fake_param).is_equal_to("Test")


def test_api_gateway_authorizer_resolver_when_request_completes_should_clear_context(lambda_context):
    # ARRANGE
    logger = mock.create_autospec(spec=logging.Logger)
    app = event_handler.APIGatewayAuthorizerRequestEventResolver(logger=logger)
    ctx_during_runtime = None

    @app.handle(FakeEvent)
    def fake_event_handler(evt: FakeEvent):
        app.append_context(a="b")
        nonlocal ctx_during_runtime
        ctx_during_runtime = app.context.copy()
        return {}

    event = api_gateway_authorizer_event.APIGatewayAuthorizerRequestEvent(
        {
            "type": "FakeEvent",
            "methodArn": "arn:aws:execute-api:us-east-1:123456789012:abcdef123/test/GET/path",
            "authorizationToken": "test-token",
            "resource": "/path",
            "path": "/path",
            "httpMethod": "GET",
            "headers": {"FakeParam": "Test"},
            "queryStringParameters": {},
            "pathParameters": {},
            "stageVariables": {},
            "version": "1.0",
        }
    )

    # ACT
    app.resolve(event, lambda_context)

    # ASSERT
    assert_that(app.context).is_equal_to({})
    assert_that(ctx_during_runtime).is_equal_to({"a": "b"})


def test_api_gateway_authorizer_resolver_when_request_fails_should_clear_context(lambda_context):
    # ARRANGE
    logger = mock.create_autospec(spec=logging.Logger)
    app = event_handler.APIGatewayAuthorizerRequestEventResolver(logger=logger)

    @app.handle(FakeEvent)
    def fake_event_handler(evt: FakeEvent):
        app.append_context(a="b")
        raise Exception("Test")

    event = api_gateway_authorizer_event.APIGatewayAuthorizerRequestEvent(
        {
            "type": "FakeEvent",
            "methodArn": "arn:aws:execute-api:us-east-1:123456789012:abcdef123/test/GET/path",
            "authorizationToken": "test-token",
            "resource": "/path",
            "path": "/path",
            "httpMethod": "GET",
            "headers": {"FakeParam": "Test"},
            "queryStringParameters": {},
            "pathParameters": {},
            "stageVariables": {},
            "version": "1.0",
        }
    )

    # ACT
    with pytest.raises(Exception):
        app.resolve(event, lambda_context)

    # ASSERT
    assert_that(app.context).is_equal_to({})


def test_api_gateway_authorizer_resolver_when_does_not_exist_should_raise(lambda_context):
    # ARRANGE
    logger = mock.create_autospec(spec=logging.Logger)
    app = event_handler.APIGatewayAuthorizerRequestEventResolver(logger=logger)

    @app.handle(FakeEvent)
    def fake_event_handler(evt: FakeEvent):
        pass

    event = api_gateway_authorizer_event.APIGatewayAuthorizerRequestEvent(
        {
            "type": "NonExistentHandler",
            "methodArn": "arn:aws:execute-api:us-east-1:123456789012:abcdef123/test/GET/path",
            "authorizationToken": "test-token",
            "resource": "/path",
            "path": "/path",
            "httpMethod": "GET",
            "headers": {"FakeParam": "Test"},
            "queryStringParameters": {},
            "pathParameters": {},
            "stageVariables": {},
            "version": "1.0",
        }
    )

    # ACT / ASSERT
    with pytest.raises(event_handler.EventResolverException) as e:
        app.resolve(event, lambda_context)

        assert_that(str(e)).starts_with("Event handler for NonExistentHandler is not registered. ")


def test_api_gateway_authorizer_resolver_when_payload_is_invalid_should_raise(lambda_context):
    # ARRANGE
    logger = mock.create_autospec(spec=logging.Logger)
    app = event_handler.APIGatewayAuthorizerRequestEventResolver(logger=logger)

    @app.handle(FakeEvent)
    def fake_event_handler(evt: FakeEvent):
        pass

    event = api_gateway_authorizer_event.APIGatewayAuthorizerRequestEvent(
        {
            "type": "FakeEvent",
            "methodArn": "arn:aws:execute-api:us-east-1:123456789012:abcdef123/test/GET/path",
            "authorizationToken": "test-token",
            "resource": "/path",
            "path": "/path",
            "httpMethod": "GET",
            "headers": {"FakeParamNonExistent": "Test"},
            "queryStringParameters": {},
            "pathParameters": {},
            "stageVariables": {},
            "version": "1.0",
        }
    )

    # ACT / ASSERT
    with pytest.raises(ValidationError):
        app.resolve(event, lambda_context)


def test_api_gateway_authorizer_resolver_when_wrong_type_should_raise(lambda_context):
    # ARRANGE
    logger = mock.create_autospec(spec=logging.Logger)
    app = event_handler.APIGatewayAuthorizerRequestEventResolver(logger=logger)

    @app.handle(FakeEvent)
    def fake_event_handler(evt: FakeEvent):
        pass

    event = {"type": "FakeEvent", "headers": {"FakeParam": "Test"}}

    # ACT / ASSERT
    with pytest.raises(event_handler.EventResolverException):
        app.resolve(event, lambda_context)


def test_saga_event_resolver_should_parse_event_bridge_events(lambda_context):
    # ARRANGE
    logger = mock.create_autospec(spec=logging.Logger)
    app = event_handler.SagaEventResolver(logger=logger)
    passed_evt: FakeEvent | None = None

    event = {"detail-type": "FakeEvent", "detail": {"FakeParam": "Test"}}

    @app.handle(FakeEvent)
    def fake_event_bridge_handler(evt: FakeEvent):
        nonlocal passed_evt
        passed_evt = evt

    # ACT
    app.resolve(event, lambda_context)

    # ASSERT
    assert_that(passed_evt).is_not_none()
    assert_that(passed_evt.fake_param).is_equal_to("Test")


def test_saga_event_resolver_should_parse_commands(lambda_context):
    # ARRANGE
    logger = mock.create_autospec(spec=logging.Logger)
    app = event_handler.SagaEventResolver(logger=logger)
    passed_cmd: FakeCommand | None = None

    event = {"saga-command-name": "FakeCommand", "saga-command": {"someParam": "Test"}}

    @app.handle(FakeCommand)
    def fake_saga_cmd_handler(cmd: FakeCommand):
        nonlocal passed_cmd
        passed_cmd = cmd

    # ACT
    app.resolve(event, lambda_context)

    # ASSERT
    assert_that(passed_cmd).is_not_none()
    assert_that(passed_cmd.some_param).is_not_none()
    assert_that(passed_cmd.some_param.value).is_equal_to("Test")
