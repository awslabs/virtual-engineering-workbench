import json

import assertpy
import pytest

from app.shared.middleware.metric import metric_handlers


@pytest.fixture
def metric_event():
    return {
        "requestContext": {
            "operationName": "GetProjectAccounts",
            "authorizer": {"userName": "TestUser"},
        }
    }


def test_metric_handlers_when_rest_operation_then_dimension_exists(lambda_context, capsys, metric_event):
    # ARRANGE
    secret_name = "audit-logging-key"

    @metric_handlers.report_invocation_metrics(service="foo", namespace="bar", secret_name=secret_name)
    def handler(event, context):
        return {}

    # ACT
    handler(event=metric_event, context=lambda_context)

    # ASSERT
    results = json.loads(capsys.readouterr().out.strip())
    assertpy.assert_that(results).contains_key("operationName")
    assertpy.assert_that(results.get("operationName")).is_equal_to("GetProjectAccounts")
