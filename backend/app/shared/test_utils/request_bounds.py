"""Checks that every request body in an OpenAPI schema is size-bounded and that the
Pydantic request models enforce the same bounds.

The OpenAPI file is what API Gateway validates against (when a request validator
covers the body) and what KICS scans. The Pydantic models are what Lambda Powertools
validates against. If either one drifts, the KICS suppression reasons in the schema
header stop being true, so the tests fail instead.
"""

from typing import Any, Iterator

from pydantic import BaseModel

Violation = str
_BOUND_KEYS = ("maxLength", "maxItems", "maxProperties", "minimum", "maximum")


def _children(node: dict) -> Iterator[dict]:
    yield from node.get("allOf", []) + node.get("anyOf", []) + node.get("oneOf", [])
    yield from node.get("properties", {}).values()
    for key in ("items", "additionalProperties"):
        if isinstance(node.get(key), dict):
            yield node[key]


def _request_body_schemas(spec: dict) -> Iterator[dict]:
    for methods in spec["paths"].values():
        for operation in methods.values():
            if isinstance(operation, dict):
                for media in operation.get("requestBody", {}).get("content", {}).values():
                    if "schema" in media:
                        yield media["schema"]


def request_body_schema_names(spec: dict) -> set[str]:
    """Names of all component schemas reachable from any operation's request body."""
    schemas = spec["components"]["schemas"]
    found: set[str] = set()
    pending = list(_request_body_schemas(spec))
    while pending:
        node = pending.pop()
        if "$ref" in node:
            name = node["$ref"].split("/")[-1]
            if name in found:
                continue
            found.add(name)
            node = schemas[name]
        pending.extend(_children(node))
    return found


def _string_violations(path: str, node: dict) -> Iterator[Violation]:
    if "enum" not in node and "maxLength" not in node:
        yield f"{path}: string without maxLength"


def _array_violations(path: str, node: dict) -> Iterator[Violation]:
    if "maxItems" not in node:
        yield f"{path}: array without maxItems"
    yield from _unbounded(f"{path}[]", node.get("items", {}))


def _integer_violations(path: str, node: dict) -> Iterator[Violation]:
    if not {"minimum", "maximum"} <= node.keys():
        yield f"{path}: integer without minimum/maximum"


def _object_violations(path: str, node: dict) -> Iterator[Violation]:
    if isinstance(node.get("additionalProperties"), dict):
        if "maxProperties" not in node:
            yield f"{path}: map without maxProperties"
        yield from _unbounded(f"{path}{{}}", node["additionalProperties"])


_CHECKS = {
    "string": _string_violations,
    "array": _array_violations,
    "integer": _integer_violations,
    "object": _object_violations,
}


def _unbounded(path: str, node: dict) -> Iterator[Violation]:
    if "$ref" in node:
        return
    check = _CHECKS.get(node.get("type"))
    if check:
        yield from check(path, node)
    for prop, sub in node.get("properties", {}).items():
        yield from _unbounded(f"{path}.{prop}", sub)


def unbounded_request_fields(spec: dict) -> list[Violation]:
    """Every request-body string/array/integer/map that has no upper bound."""
    violations: list[Violation] = []
    for name in sorted(request_body_schema_names(spec)):
        violations.extend(_unbounded(name, spec["components"]["schemas"][name]))
    for index, inline in enumerate(s for s in _request_body_schemas(spec) if "$ref" not in s):
        violations.extend(_unbounded(f"inline-request-body-{index}", inline))
    return violations


def _bounds(node: dict) -> dict[str, Any]:
    return {k: node[k] for k in _BOUND_KEYS if k in node}


def _model_property(model_schema: dict, prop: str) -> dict:
    """Pydantic renders Optional[X] as anyOf [X, null]; return the non-null branch."""
    node = model_schema["properties"][prop]
    for branch in node.get("anyOf", []):
        if branch.get("type") != "null":
            return branch
    return node


def _property_mismatches(where: str, schema_prop: dict, model_prop: dict) -> Iterator[Violation]:
    if _bounds(schema_prop) != _bounds(model_prop):
        yield f"{where}: schema {_bounds(schema_prop)} != model {_bounds(model_prop)}"
    for child_key in ("items", "additionalProperties"):
        child = schema_prop.get(child_key)
        if isinstance(child, dict) and "$ref" not in child:
            yield from _property_mismatches(f"{where}.{child_key}", child, model_prop.get(child_key, {}))


def model_bound_mismatches(spec: dict, models: dict[str, type[BaseModel]]) -> list[Violation]:
    """Compare schema bounds with the Pydantic model of the same name, field by field."""
    mismatches: list[Violation] = []
    for name in sorted(request_body_schema_names(spec)):
        if "properties" not in spec["components"]["schemas"][name]:
            continue  # enums and other scalar schemas have no fields to compare
        model = models.get(name)
        if model is None:
            mismatches.append(f"{name}: no Pydantic model with this name")
            continue
        model_schema = model.model_json_schema()
        for prop, sub in spec["components"]["schemas"][name].get("properties", {}).items():
            if "$ref" not in sub:
                mismatches.extend(_property_mismatches(f"{name}.{prop}", sub, _model_property(model_schema, prop)))
    return mismatches


def pydantic_models(module) -> dict[str, type[BaseModel]]:
    return {
        name: obj
        for name, obj in vars(module).items()
        if isinstance(obj, type) and issubclass(obj, BaseModel) and obj is not BaseModel
    }
