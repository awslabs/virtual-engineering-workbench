"""AgentCore Gateway REQUEST interceptor.

Configured with ``passRequestHeaders: true``, so the gateway includes the
inbound request headers in the event. The gateway has already validated the
CUSTOM_JWT token; this interceptor re-emits the caller's ``Authorization`` header
so it is forwarded to the target bounded context API, where the existing shared
authorizer performs the real authorization.

The forwarded token is never logged — only
non-sensitive metadata (method, tool name, header keys, presence of auth).

Uses only the standard library so the Lambda needs no dependency layer.
"""

import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def extract_authorization(headers: dict) -> str | None:
    """Return the Authorization value, matching the header name case-insensitively."""
    if not isinstance(headers, dict):
        return None
    for key, value in headers.items():
        if key.lower() == "authorization":
            return value
    return None


def _as_dict(value) -> dict:
    """Treat a missing, null or non-object field as empty, so a malformed event cannot crash the interceptor."""
    return value if isinstance(value, dict) else {}


def handler(event: dict, context=None) -> dict:
    try:
        gateway_request = _as_dict(_as_dict(event).get("mcp")).get("gatewayRequest")
        gateway_request = _as_dict(gateway_request)
        headers = _as_dict(gateway_request.get("headers"))
        authorization = extract_authorization(headers)

        # The body is forwarded unchanged; it is only inspected for log metadata.
        body = gateway_request.get("body")
        body_fields = _as_dict(body)
        method = body_fields.get("method")
        tool = _as_dict(body_fields.get("params")).get("name")

        # Non-sensitive metadata only — never the token value.
        logger.info(
            "interceptor request: keys=%s http=%s method=%s tool=%s headers=%s has_auth=%s",
            list(_as_dict(event).keys()),
            gateway_request.get("httpMethod"),
            method,
            tool,
            sorted(headers.keys()),
            authorization is not None,
        )

        transformed: dict = {"body": body}
        if authorization is not None:
            transformed["headers"] = {"Authorization": authorization}

        logger.info(
            "interceptor output: forwarded_authorization=%s body_present=%s",
            authorization is not None,
            body is not None,
        )
        return {"interceptorOutputVersion": "1.0", "mcp": {"transformedGatewayRequest": transformed}}
    except Exception:
        logger.exception("interceptor failed to process request")
        raise
