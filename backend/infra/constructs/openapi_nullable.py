"""Make OpenAPI `nullable: true` mean the same thing to API Gateway's request validator.

API Gateway turns an imported OpenAPI 3.0 schema into a JSON Schema draft 4 model, and draft 4 has no
`nullable`: a field declared `{type: string, nullable: true}` still rejects `null` with
400 BAD_REQUEST_BODY, although the OpenAPI document - and the Lambda behind it - accept it. Clients
that send `null` for an unset optional field (the elva-labs/vew Terraform provider does) are
therefore refused before they reach the handler.

`accept_null_in_nullable_fields` rewrites only the copy handed to API Gateway: each nullable schema
loses `nullable` and the keywords that reject `null` - `type`, `enum`, `oneOf` and `anyOf` - while the type-specific
ones such as `maxLength`, `minimum`, `properties` or `items` still apply to non-null values. It only
removes keywords, so the import (which fails the deployment on any warning) sees nothing new. The
published OpenAPI document keeps the original schema, and the handlers' pydantic models still check
every value, null or not.
"""

import copy
import typing

# Draft 4 keywords that make a schema reject null. `allOf` is not removed: dropping it would drop the
# whole schema, and the tests fail if a nullable request field ever needs it.
NULL_REJECTING_KEYWORDS = ("type", "enum", "oneOf", "anyOf")
# `nullable` itself goes too: API Gateway ignores it, and without `type` it would only be noise to the import.
REMOVED_KEYWORDS = (*NULL_REJECTING_KEYWORDS, "nullable")


def accept_null_in_nullable_fields(schema: typing.Any) -> typing.Any:
    """Return a deep copy of an OpenAPI document or schema whose nullable schemas also accept null."""
    result = copy.deepcopy(schema)
    _rewrite(result)
    return result


def _rewrite(node: typing.Any) -> None:
    if isinstance(node, dict):
        if node.get("nullable") is True and "$ref" not in node:
            for keyword in REMOVED_KEYWORDS:
                node.pop(keyword, None)
        for value in node.values():
            _rewrite(value)
    elif isinstance(node, list):
        for item in node:
            _rewrite(item)


def nullable_refs(schema: typing.Any, path: str = "") -> list[str]:
    """Paths of schemas that combine `$ref` with `nullable`; API Gateway ignores `nullable` there too."""
    found: list[str] = []
    if isinstance(schema, dict):
        if schema.get("nullable") is True and "$ref" in schema:
            found.append(path)
        for key, value in schema.items():
            found.extend(nullable_refs(value, f"{path}/{key}"))
    elif isinstance(schema, list):
        for index, item in enumerate(schema):
            found.extend(nullable_refs(item, f"{path}/{index}"))
    return found
