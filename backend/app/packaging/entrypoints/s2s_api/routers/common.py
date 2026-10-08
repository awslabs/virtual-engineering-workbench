from aws_lambda_powertools import Metrics
from aws_lambda_powertools.event_handler import api_gateway

from app.packaging.domain.exceptions.s2s_exception import InsufficientScope

NO_STORE = {"Cache-Control": "no-store"}
api_metrics = Metrics(service="PackagingS2S")


def client_id(router: api_gateway.Router) -> str:
    return router.context["user_principal"].user_name


def require_scope(router: api_gateway.Router, required_scope: str) -> None:
    claims = router.current_event.raw_event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    granted_scopes = set(str(claims.get("scope", "")).split())
    if required_scope not in granted_scopes:
        raise InsufficientScope(required_scope)
