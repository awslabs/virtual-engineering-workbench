import pytest
from assertpy import assert_that

from app.mcp_gateway_agentcore.entrypoints.interceptor import handler


def _event(headers: dict, body=None):
    return {"mcp": {"gatewayRequest": {"httpMethod": "POST", "headers": headers, "body": body}}}


def test_extract_authorization_is_case_insensitive():
    assert_that(handler.extract_authorization({"authorization": "Bearer x"})).is_equal_to("Bearer x")
    assert_that(handler.extract_authorization({"Authorization": "Bearer y"})).is_equal_to("Bearer y")
    assert_that(handler.extract_authorization({"other": "z"})).is_none()


def test_handler_re_emits_authorization_header():
    # ARRANGE
    event = _event({"authorization": "Bearer token123"}, body={"jsonrpc": "2.0"})

    # ACT
    out = handler.handler(event, None)

    # ASSERT
    assert_that(out["interceptorOutputVersion"]).is_equal_to("1.0")
    transformed = out["mcp"]["transformedGatewayRequest"]
    assert_that(transformed["headers"]).is_equal_to({"Authorization": "Bearer token123"})
    assert_that(transformed["body"]).is_equal_to({"jsonrpc": "2.0"})


def test_handler_omits_headers_when_no_authorization():
    out = handler.handler(_event({"accept": "application/json"}), None)
    assert_that(out["mcp"]["transformedGatewayRequest"]).does_not_contain_key("headers")


def test_handler_does_not_log_the_token(caplog):
    # ACT
    handler.handler(_event({"authorization": "Bearer super-secret-token"}), None)

    # ASSERT — the token value never appears in logs
    assert_that(caplog.text).does_not_contain("super-secret-token")


@pytest.mark.parametrize(
    "event",
    [
        {"mcp": {"gatewayRequest": {"headers": {}}}},
        {"mcp": {"gatewayRequest": {"headers": {}, "body": None}}},
        {"mcp": {"gatewayRequest": {"body": "raw"}}},
        {"mcp": {"gatewayRequest": {"body": {"method": "tools/call", "params": None}}}},
        {"mcp": {"gatewayRequest": {"body": {"method": "tools/call", "params": [1]}}}},
        {"mcp": {"gatewayRequest": {"headers": None}}},
        {"mcp": {"gatewayRequest": None}},
        {"mcp": None},
        {},
    ],
)
def test_handler_tolerates_malformed_events(event):
    # ACT
    out = handler.handler(event, None)

    # ASSERT: the request passes through without an Authorization header, and the body unchanged
    transformed = out["mcp"]["transformedGatewayRequest"]
    assert_that(transformed).does_not_contain_key("headers")
    assert_that(transformed["body"]).is_equal_to(((event.get("mcp") or {}).get("gatewayRequest") or {}).get("body"))
