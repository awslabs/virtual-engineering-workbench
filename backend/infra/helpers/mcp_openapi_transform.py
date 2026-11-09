"""Pure transform: repository OpenAPI spec -> Published_Spec consumed by an
AgentCore OpenAPI target.

Run at CDK synth by the MCP gateway stack (imported from ``infra``) — there is no
runtime consumer, so this lives in ``infra/helpers`` alongside ``openapi_parser``
rather than in an app bounded context. ``base_url`` may be a CDK token; the dict
is uploaded via ``BucketDeployment(Source.jsonData)`` which resolves it at deploy.

Three concerns, and nothing else:
1. strip Internal_Endpoints,
2. set ``servers`` to the reachable Base_Url,
3. enrich operation/parameter ``description`` with anything AgentCore's OpenAPI
   parser drops -- ``summary`` and numeric/length constraints.

Every function is side-effect free and works on plain dicts, so the whole module
is unit-testable without AWS. The input spec is never mutated.
"""

from __future__ import annotations

import copy

# Paths never exposed as tools. Single shared list.
EXCLUDED_PATH_PREFIXES = ("/internal/", "/_swagger", "/openapi.json", "/docs")
# Non-operation / non-callable methods dropped from every retained path.
EXCLUDED_METHODS = ("options",)
# OpenAPI operation methods we treat as callable operations.
HTTP_METHODS = ("get", "put", "post", "delete", "patch", "head", "trace")


class MissingOperationIdError(ValueError):
    """A retained operation has no ``operationId``."""


def resolve_base_url(api_url: str, custom_domain_urls: dict[str, str], api_id: str) -> str:
    """Return the reachable Base_Url for a bounded context.

    Prefers the custom-domain URL when the api-integration map has one for this
    API id (custom DNS on); otherwise falls back to the raw execute-api url from
    the registration (custom DNS off).
    """
    return custom_domain_urls.get(api_id) or api_url


def transform(spec: dict, base_url: str) -> dict:
    """Produce the Published_Spec for one bounded context.

    Order: coerce string fields -> strip -> set server -> enrich -> validate.
    Raises :class:`MissingOperationIdError` if any retained operation lacks an
    ``operationId``.
    """
    result = copy.deepcopy(spec)
    _coerce_string_fields(result)
    _strip_excluded(result)
    _strip_auth_parameters(result)
    _set_server(result, base_url)
    _enrich(result)
    _validate_operation_ids(result)
    return result


def _strip_auth_parameters(spec: dict) -> None:
    """Remove any ``Authorization`` header parameter from operations.

    The bounded-context specs declare an ``Authorization`` header param; if left in,
    AgentCore turns it into a (required) tool input, so a caller would have to pass a
    bearer token as a tool argument and every call fails validation. The REQUEST
    interceptor injects the real ``Authorization`` header, so it must not be a tool
    parameter.
    """
    for _path, _method, operation in _iter_operations(spec):
        params = operation.get("parameters")
        if isinstance(params, list):
            operation["parameters"] = [
                p
                for p in params
                if not (
                    isinstance(p, dict)
                    and p.get("in") == "header"
                    and str(p.get("name", "")).lower() == "authorization"
                )
            ]


def _coerce_string_fields(spec: dict) -> None:
    """Force OpenAPI fields that must be strings but are often written unquoted in
    YAML (so ``yaml.safe_load`` returns a number) — e.g. ``info.version: 1.0``.
    AgentCore rejects a spec whose ``info.version`` is not a JSON string.
    """
    if spec.get("openapi") is not None:
        spec["openapi"] = str(spec["openapi"])
    info = spec.get("info")
    if isinstance(info, dict) and info.get("version") is not None:
        info["version"] = str(info["version"])


def _is_excluded_path(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in EXCLUDED_PATH_PREFIXES)


def _strip_excluded(spec: dict) -> None:
    paths = spec.get("paths", {})
    for path in list(paths.keys()):
        if _is_excluded_path(path):
            del paths[path]
            continue
        for method in EXCLUDED_METHODS:
            paths[path].pop(method, None)


def _set_server(spec: dict, base_url: str) -> None:
    spec["servers"] = [{"url": base_url}]


def _iter_operations(spec: dict):
    for path, methods in spec.get("paths", {}).items():
        if not isinstance(methods, dict):
            continue
        for method, operation in methods.items():
            if method.lower() in HTTP_METHODS and isinstance(operation, dict):
                yield path, method, operation


def _enrich(spec: dict) -> None:
    """Fold ``summary`` and dropped constraints into ``description`` text so a
    coding agent still sees them after AgentCore's parser drops those fields.
    ``operationId`` is never touched.
    """
    for _path, _method, operation in _iter_operations(spec):
        _enrich_operation_description(operation)
        _enrich_parameters(operation)
        _enrich_request_body(operation)


def _enrich_operation_description(operation: dict) -> None:
    summary = (operation.get("summary") or "").strip()
    description = (operation.get("description") or "").strip()
    if summary and summary not in description:
        operation["description"] = f"{summary}. {description}".strip() if description else summary


def _enrich_parameters(operation: dict) -> None:
    for param in operation.get("parameters", []):
        if not isinstance(param, dict):
            continue
        suffix = _constraint_suffix(param.get("schema", {}))
        if suffix:
            param["description"] = f"{(param.get('description') or '').strip()}{suffix}".strip()


def _enrich_request_body(operation: dict) -> None:
    schema = operation.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema", {})
    for prop in schema.get("properties", {}).values():
        if not isinstance(prop, dict):
            continue
        suffix = _constraint_suffix(prop)
        if suffix:
            prop["description"] = f"{(prop.get('description') or '').strip()}{suffix}".strip()


def _constraint_suffix(schema: dict) -> str:
    """Build a ``" (allowed values: ...; min: ...; ...)"`` suffix from the schema
    fields AgentCore drops. Empty string when there is nothing to add.
    """
    parts: list[str] = []
    if "enum" in schema:
        parts.append("allowed values: " + ", ".join(str(v) for v in schema["enum"]))
    if "minimum" in schema:
        parts.append(f"min: {schema['minimum']}")
    if "maximum" in schema:
        parts.append(f"max: {schema['maximum']}")
    if "maxLength" in schema:
        parts.append(f"max length: {schema['maxLength']}")
    if "default" in schema:
        parts.append(f"default: {schema['default']}")
    return f" ({'; '.join(parts)})" if parts else ""


def _validate_operation_ids(spec: dict) -> None:
    missing = [
        f"{method.upper()} {path}"
        for path, method, operation in _iter_operations(spec)
        if not operation.get("operationId")
    ]
    if missing:
        raise MissingOperationIdError("operationId missing for: " + ", ".join(missing))
