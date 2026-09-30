"""API Gateway's request validator accepts null for every field an API schema declares nullable.

API Gateway validates request bodies against JSON Schema draft 4, which ignores OpenAPI `nullable`.
infra/constructs/openapi_nullable.py rewrites the definition handed to API Gateway; these tests check
the rewrite itself and send null to every nullable field of every request body the APIs validate.
"""

import pathlib

import jsonschema
import pytest
import yaml

from infra.constructs.openapi_nullable import accept_null_in_nullable_fields, nullable_refs

SCHEMAS = sorted((pathlib.Path(__file__).parents[3] / "app").glob("*/entrypoints/*/schema/*-api-schema.yaml"))
METHODS = ("get", "put", "post", "delete", "patch")


def _draft4(schema):
    return jsonschema.Draft4Validator(schema)


@pytest.mark.parametrize(
    "schema,value",
    [
        ({"type": "string", "nullable": True, "maxLength": 3}, "abc"),
        ({"type": "integer", "nullable": True, "minimum": 1}, 5),
        ({"type": "boolean", "nullable": True}, True),
        ({"type": "array", "nullable": True, "items": {"type": "string"}}, ["a"]),
        ({"type": "object", "nullable": True, "properties": {"a": {"type": "string"}}}, {"a": "x"}),
        ({"type": "string", "nullable": True, "enum": ["A", "B"]}, "A"),
        ({"nullable": True, "oneOf": [{"type": "object"}, {"type": "array", "items": {}}]}, {"a": 1}),
    ],
)
def test_nullable_schema_accepts_null_and_its_values(schema, value):
    rewritten = accept_null_in_nullable_fields(schema)

    assert _draft4(schema).is_valid(None) is False  # what API Gateway does without the rewrite
    assert _draft4(rewritten).is_valid(None)
    assert _draft4(rewritten).is_valid(value)


@pytest.mark.parametrize(
    "schema,invalid",
    [
        ({"type": "string", "nullable": True, "maxLength": 3}, "abcd"),
        ({"type": "integer", "nullable": True, "minimum": 1}, 0),
        ({"type": "array", "nullable": True, "items": {"type": "string"}}, [1]),
        ({"type": "object", "nullable": True, "properties": {"a": {"type": "string"}}}, {"a": 1}),
    ],
)
def test_constraints_on_non_null_values_still_apply(schema, invalid):
    assert _draft4(accept_null_in_nullable_fields(schema)).is_valid(invalid) is False


def test_rewrite_only_removes_keywords():
    # The import fails the deployment on any warning: the rewrite must add nothing API Gateway could
    # object to, so every rewritten node is a subset of the original.
    for schema_path in SCHEMAS:
        original = yaml.safe_load(schema_path.read_text())
        _assert_subset(accept_null_in_nullable_fields(original), original, schema_path.name)


def _assert_subset(rewritten, original, where):
    if isinstance(rewritten, dict):
        assert set(rewritten) <= set(original), where
        for key, value in rewritten.items():
            _assert_subset(value, original[key], f"{where}/{key}")
    elif isinstance(rewritten, list):
        assert len(rewritten) == len(original), where
        for index, item in enumerate(rewritten):
            _assert_subset(item, original[index], f"{where}/{index}")
    else:
        assert rewritten == original, where


def test_non_nullable_schemas_are_unchanged_and_the_input_is_not_modified():
    schema = {"type": "object", "properties": {"a": {"type": "string"}, "b": {"type": "string", "nullable": True}}}

    rewritten = accept_null_in_nullable_fields(schema)

    assert rewritten["properties"]["a"] == {"type": "string"}
    assert "type" not in rewritten["properties"]["b"]
    assert schema["properties"]["b"]["type"] == "string"


def _request_body_schemas(document):
    for path, operations in document.get("paths", {}).items():
        for method in METHODS:
            operation = (operations or {}).get(method)
            if not isinstance(operation, dict):
                continue
            body = operation.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema")
            if body is not None:
                yield f"{method.upper()} {path}", body


def _nullable_fields(schema, components, path, seen):  # noqa: C901
    """(path, schema) of every nullable schema reachable from a request body, following $refs."""
    if isinstance(schema, dict):
        if "$ref" in schema:
            name = schema["$ref"].split("/")[-1]
            if name not in seen:
                yield from _nullable_fields(components[name], components, f"{path}->{name}", seen | {name})
            return
        if schema.get("nullable") is True:
            yield path, schema
        for key, value in schema.items():
            if key == "properties":
                for name, child in value.items():
                    yield from _nullable_fields(child, components, f"{path}.{name}", seen)
            elif key in ("items", "additionalProperties") and isinstance(value, dict):
                yield from _nullable_fields(value, components, f"{path}[]", seen)
            elif key in ("allOf", "anyOf", "oneOf"):
                for child in value:
                    yield from _nullable_fields(child, components, path, seen)


def _cases():
    for schema_path in SCHEMAS:
        original = yaml.safe_load(schema_path.read_text())
        components = original.get("components", {}).get("schemas", {})
        for operation, body in _request_body_schemas(original):
            for field, schema in _nullable_fields(body, components, operation, frozenset()):
                bounded_context = schema_path.parents[2].name
                yield pytest.param(schema, id=f"{bounded_context}/{schema_path.parents[1].name}:{field}")


@pytest.mark.parametrize("schema", list(_cases()))
def test_every_nullable_request_field_accepts_null(schema):
    # The field's schema as API Gateway receives it (the rewrite is local to each schema node).
    assert _draft4(accept_null_in_nullable_fields(schema)).is_valid(None)


@pytest.mark.parametrize("schema_path", SCHEMAS, ids=lambda p: p.name)
def test_no_nullable_ref_in_a_request_body(schema_path):
    # `nullable` next to `$ref` is ignored by OpenAPI 3.0 and by API Gateway; the rewrite cannot fix it.
    document = yaml.safe_load(schema_path.read_text())
    components = document.get("components", {}).get("schemas", {})
    for operation, body in _request_body_schemas(document):
        closure = [body]
        seen: set[str] = set()
        while closure:
            node = closure.pop()
            assert not nullable_refs(node), f"{operation}: nullable $ref at {nullable_refs(node)}"
            for ref in _refs(node):
                if ref not in seen:
                    seen.add(ref)
                    closure.append(components[ref])


def _refs(node):
    if isinstance(node, dict):
        if "$ref" in node:
            yield node["$ref"].split("/")[-1]
        for value in node.values():
            yield from _refs(value)
    elif isinstance(node, list):
        for item in node:
            yield from _refs(item)
