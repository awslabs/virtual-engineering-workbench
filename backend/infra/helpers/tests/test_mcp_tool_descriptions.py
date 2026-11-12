"""Checks the final transformed OpenAPI schemas built for the MCP gateway.

These tests exercise all repository schemas through ``build_target_specs``.
The stack test separately intercepts ``Source.json_data`` to verify that the
same transformed dictionaries reach the upload boundary. A deployed AgentCore
``tools/list`` response requires user-approved deployment and is out of scope.
"""

import glob
import os

import pytest
import yaml

from infra.backend import mcp_gateway_agentcore_app_stack
from infra.helpers import mcp_openapi_transform

MCP_BOUNDED_CONTEXTS = ["projects", "packaging", "publishing", "provisioning"]
HTTP_METHODS = mcp_openapi_transform.HTTP_METHODS
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def _source_spec(bounded_context: str) -> dict:
    pattern = os.path.join(BACKEND_ROOT, "app", bounded_context, "entrypoints", "api", "schema", "*.yaml")
    with open(sorted(glob.glob(pattern))[0], encoding="utf-8") as handle:
        return yaml.safe_load(handle)


@pytest.fixture(name="source_specs", scope="module")
def source_specs_fixture() -> dict[str, dict]:
    return {context: _source_spec(context) for context in MCP_BOUNDED_CONTEXTS}


@pytest.fixture(name="target_specs", scope="module")
def target_specs_fixture(source_specs) -> dict[str, dict]:
    base_urls = {context: f"https://example.com/{context}" for context in MCP_BOUNDED_CONTEXTS}
    return mcp_gateway_agentcore_app_stack.build_target_specs(source_specs, base_urls)


def _operations(spec: dict):
    return [
        operation
        for path_item in spec["paths"].values()
        for method, operation in path_item.items()
        if method in HTTP_METHODS and isinstance(operation, dict)
    ]


def test_build_target_specs_returns_exact_transformed_specs(source_specs, target_specs):
    assert set(target_specs) == set(MCP_BOUNDED_CONTEXTS)
    for context in MCP_BOUNDED_CONTEXTS:
        base_url = f"https://example.com/{context}"
        assert target_specs[context] == mcp_openapi_transform.transform(source_specs[context], base_url)
        assert target_specs[context]["servers"] == [{"url": base_url}]


def test_final_gateway_target_metadata_is_valid(target_specs):
    mcp_openapi_transform.validate_target_specs(target_specs)


def test_authorization_is_not_exposed_as_a_tool_parameter(target_specs):
    for spec in target_specs.values():
        for operation in _operations(spec):
            assert all(
                not (parameter.get("in") == "header" and str(parameter.get("name", "")).casefold() == "authorization")
                for parameter in operation.get("parameters", [])
                if isinstance(parameter, dict)
            )


@pytest.mark.parametrize("bounded_context", MCP_BOUNDED_CONTEXTS)
def test_every_bounded_context_has_an_api_description(bounded_context):
    info = _source_spec(bounded_context).get("info") or {}

    assert len((info.get("description") or "").strip()) >= mcp_openapi_transform.MIN_OPERATION_DESCRIPTION_LENGTH


def test_gateway_instructions_fit_the_agentcore_limit():
    # Built the same way as McpGatewayAgentcoreStack: one <context> block per bounded context.
    blocks = [
        f'<context name="{context}">\n{_source_spec(context)["info"]["description"].strip()}\n</context>'
        for context in MCP_BOUNDED_CONTEXTS
    ]

    assert len("\n\n".join(blocks)) <= mcp_gateway_agentcore_app_stack._MAX_INSTRUCTIONS_LEN
