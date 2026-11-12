"""Transform repository OpenAPI specs into the schemas AgentCore consumes.

The gateway stack runs this module at CDK synth and passes the transformed dicts
straight to ``BucketDeployment(Source.jsonData)``. Validation therefore happens
on the final target schemas, after excluded operations and Authorization inputs
have been removed and referenced request schemas have been resolved.
"""

from __future__ import annotations

import copy
from collections import defaultdict
from collections.abc import Iterable

# Paths never exposed as tools. Single shared list.
EXCLUDED_PATH_PREFIXES = ("/internal/", "/_swagger", "/openapi.json", "/docs")
# Non-operation / non-callable methods dropped from every retained path.
EXCLUDED_METHODS = ("options",)
# OpenAPI operation methods we treat as callable operations.
HTTP_METHODS = ("get", "put", "post", "delete", "patch", "head", "trace")
MIN_OPERATION_DESCRIPTION_LENGTH = 80
MIN_INPUT_DESCRIPTION_LENGTH = 10


class MissingOperationIdError(ValueError):
    """A retained operation has no ``operationId``."""


class TargetMetadataError(ValueError):
    """The final schemas would expose ambiguous or undocumented MCP tools."""


class UnresolvedLocalRefError(TargetMetadataError):
    """An exposed local OpenAPI reference cannot be resolved to an object."""


def resolve_base_url(api_url: str, custom_domain_urls: dict[str, str], api_id: str) -> str:
    """Return the reachable base URL for a bounded context."""
    return custom_domain_urls.get(api_id) or api_url


def transform(spec: dict, base_url: str) -> dict:
    """Produce the published schema for one bounded context without mutating it."""
    result = copy.deepcopy(spec)
    _coerce_string_fields(result)
    _strip_excluded(result)
    _strip_auth_parameters(result)
    _apply_mcp_operation_ids(result)
    _set_server(result, base_url)
    _enrich(result)
    _validate_operation_ids(result)
    return result


def validate_target_specs(target_specs: dict[str, dict]) -> None:
    """Validate the complete transformed tool surface before it is uploaded.

    Tool names and descriptions must be unique across targets because AgentCore
    combines all targets into one ``tools/list`` response. Input documentation is
    checked after resolving local request-body and parameter references.
    """
    errors: list[str] = []
    operation_ids: dict[str, list[str]] = defaultdict(list)
    descriptions: dict[str, list[str]] = defaultdict(list)

    for target, spec in target_specs.items():
        _collect_target_metadata(target, spec, operation_ids, descriptions, errors)

    for operation_id, locations in operation_ids.items():
        if len(locations) > 1:
            errors.append(f"duplicate operationId/tool name '{operation_id}': {', '.join(locations)}")
    for locations in descriptions.values():
        if len(locations) > 1:
            errors.append(f"duplicate tool description: {', '.join(locations)}")

    if errors:
        raise TargetMetadataError("Invalid MCP target metadata:\n- " + "\n- ".join(errors))


def _collect_target_metadata(
    target: str,
    spec: dict,
    operation_ids: dict[str, list[str]],
    descriptions: dict[str, list[str]],
    errors: list[str],
) -> None:
    for path, method, operation in _iter_operations(spec):
        location = f"{target}: {method.upper()} {path}"
        operation_id = str(operation.get("operationId") or "").strip()
        description = str(operation.get("description") or "").strip()

        if not operation_id:
            errors.append(f"{location} has no operationId")
        else:
            operation_ids[operation_id].append(location)

        if len(description) < MIN_OPERATION_DESCRIPTION_LENGTH:
            errors.append(
                f"{location} ({operation_id or 'unnamed'}) has a non-substantive description "
                f"({len(description)} chars; minimum {MIN_OPERATION_DESCRIPTION_LENGTH})"
            )
        elif description:
            descriptions[_normalise_description(description)].append(f"{location} ({operation_id})")

        for parameter in _operation_parameters(spec, path, operation):
            name = str(parameter.get("name") or "<unnamed>")
            _check_input_description(
                parameter,
                f"{location} ({operation_id}) parameter '{name}'",
                errors,
            )

        for property_path, prop in _request_properties(spec, operation):
            _check_input_description(
                prop,
                f"{location} ({operation_id}) request property '{property_path}'",
                errors,
            )


def _check_input_description(item: dict, location: str, errors: list[str]) -> None:
    description = str(item.get("description") or "").strip()
    if len(description) < MIN_INPUT_DESCRIPTION_LENGTH:
        errors.append(
            f"{location} has no useful description "
            f"({len(description)} chars; minimum {MIN_INPUT_DESCRIPTION_LENGTH})"
        )


def _normalise_description(description: str) -> str:
    return " ".join(description.split()).casefold()


def _strip_auth_parameters(spec: dict) -> None:
    """Remove Authorization inputs before AgentCore turns them into tool arguments."""
    for path_item in spec.get("paths", {}).values():
        if not isinstance(path_item, dict):
            continue
        _strip_auth_parameter_list(spec, path_item)
        for method, operation in path_item.items():
            if method.lower() in HTTP_METHODS and isinstance(operation, dict):
                _strip_auth_parameter_list(spec, operation)


def _strip_auth_parameter_list(spec: dict, owner: dict) -> None:
    params = owner.get("parameters")
    if isinstance(params, list):
        owner["parameters"] = [
            param for param in params if not _is_authorization_parameter(_resolve_local_ref(spec, param))
        ]


def _is_authorization_parameter(parameter: object) -> bool:
    return (
        isinstance(parameter, dict)
        and parameter.get("in") == "header"
        and str(parameter.get("name", "")).casefold() == "authorization"
    )


def _apply_mcp_operation_ids(spec: dict) -> None:
    """Apply an explicit MCP-only tool name without changing the source API operationId."""
    for _path, _method, operation in _iter_operations(spec):
        mcp_operation_id = operation.pop("x-mcp-operation-id", None)
        if mcp_operation_id:
            operation["operationId"] = mcp_operation_id


def _coerce_string_fields(spec: dict) -> None:
    """Coerce OpenAPI fields that YAML may parse as numbers or datetimes."""
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
        if not isinstance(paths[path], dict):
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


def _operation_parameters(spec: dict, path: str, operation: dict) -> Iterable[dict]:
    path_item = spec.get("paths", {}).get(path, {})
    for parameter in [
        *path_item.get("parameters", []),
        *operation.get("parameters", []),
    ]:
        resolved = _resolve_local_ref(spec, parameter)
        if isinstance(resolved, dict):
            yield resolved


def _enrich(spec: dict) -> None:
    """Fold summaries and parser-dropped constraints into visible descriptions."""
    for path, _method, operation in _iter_operations(spec):
        _enrich_operation_description(operation)
        _enrich_parameters(spec, path, operation)
        _enrich_request_body(spec, operation)


def _enrich_operation_description(operation: dict) -> None:
    summary = str(operation.get("summary") or "").strip()
    description = str(operation.get("description") or "").strip()
    if summary and summary not in description:
        operation["description"] = f"{summary}. {description}".strip() if description else summary


def _enrich_parameters(spec: dict, path: str, operation: dict) -> None:
    for parameter in _operation_parameters(spec, path, operation):
        _append_constraints(parameter, parameter.get("schema", {}))


def _enrich_request_body(spec: dict, operation: dict) -> None:
    for _property_path, prop in _request_properties(spec, operation):
        _append_constraints(prop, prop)


def _append_constraints(item: dict, schema: dict) -> None:
    suffix = _constraint_suffix(schema)
    description = str(item.get("description") or "").strip()
    if suffix and suffix not in description:
        item["description"] = f"{description}{suffix}".strip()


def _request_properties(spec: dict, operation: dict) -> Iterable[tuple[str, dict]]:
    request_body = _resolve_local_ref(spec, operation.get("requestBody", {}))
    if not isinstance(request_body, dict):
        return
    content = request_body.get("content", {})
    for media_type, media in content.items():
        if not isinstance(media, dict) or not (media_type == "application/json" or media_type.endswith("+json")):
            continue
        yield from _schema_properties(spec, media.get("schema", {}), "", set())


def _schema_properties(
    spec: dict,
    schema: dict,
    prefix: str,
    resolving_refs: set[str],
) -> Iterable[tuple[str, dict]]:
    if not isinstance(schema, dict):
        return
    ref = schema.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/"):
        if ref in resolving_refs:
            return
        resolved = _resolve_local_ref(spec, schema)
        yield from _schema_properties(spec, resolved, prefix, resolving_refs | {ref})
        return

    yield from _object_schema_properties(spec, schema, prefix, resolving_refs)

    items = schema.get("items")
    if isinstance(items, dict):
        item_prefix = f"{prefix}[]" if prefix else "[]"
        yield from _schema_properties(spec, items, item_prefix, resolving_refs)

    for keyword in ("allOf", "oneOf", "anyOf"):
        for member in schema.get(keyword, []):
            yield from _schema_properties(spec, member, prefix, resolving_refs)


def _object_schema_properties(
    spec: dict,
    schema: dict,
    prefix: str,
    resolving_refs: set[str],
) -> Iterable[tuple[str, dict]]:
    for name, prop in schema.get("properties", {}).items():
        if not isinstance(prop, dict):
            continue
        path = f"{prefix}.{name}" if prefix else name
        resolved = _resolve_local_ref(spec, prop)
        documented = prop if prop.get("description") else resolved
        if isinstance(documented, dict):
            yield path, documented
        yield from _schema_properties(spec, prop, path, resolving_refs)


def _resolve_local_ref(spec: dict, value: dict) -> dict:
    if not isinstance(value, dict):
        return value
    ref = value.get("$ref")
    if not isinstance(ref, str) or not ref.startswith("#/"):
        return value

    resolved = spec
    try:
        for part in ref[2:].split("/"):
            resolved = resolved[part.replace("~1", "/").replace("~0", "~")]
    except (KeyError, TypeError):
        raise UnresolvedLocalRefError(f"Local OpenAPI $ref '{ref}' does not resolve to an object") from None
    if not isinstance(resolved, dict):
        raise UnresolvedLocalRefError(f"Local OpenAPI $ref '{ref}' does not resolve to an object")
    return resolved


def _constraint_suffix(schema: dict) -> str:
    """Build a visible suffix from fields AgentCore drops."""
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
