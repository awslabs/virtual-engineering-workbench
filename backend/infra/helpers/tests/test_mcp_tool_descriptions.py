"""Checks on the tool surface the MCP gateway publishes, built from the real API schemas.

Tool names, descriptions and the gateway instructions are what an agent reasons over to pick
a tool. Name-only descriptions ("Get a project") pass a smoke test on easy prompts and degrade
tool selection under ambiguity, so these assert on the published spec rather than the source.
"""

import glob
import os

import pytest
import yaml

from infra.backend import mcp_gateway_agentcore_app_stack
from infra.helpers import mcp_openapi_transform

MCP_BOUNDED_CONTEXTS = ["projects", "packaging", "publishing", "provisioning"]
HTTP_METHODS = ("get", "post", "put", "delete", "patch")
# Name-only restatements are ~20-40 chars; ported descriptions carry purpose and prerequisites.
MIN_DESCRIPTION_LENGTH = 80
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def _source_spec(bounded_context: str) -> dict:
    pattern = os.path.join(BACKEND_ROOT, "app", bounded_context, "entrypoints", "api", "schema", "*.yaml")
    with open(sorted(glob.glob(pattern))[0], encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _published_tools(bounded_context: str) -> dict[str, str]:
    published = mcp_openapi_transform.transform(_source_spec(bounded_context), "https://example.com")
    return {
        operation["operationId"]: (operation.get("description") or "").strip()
        for path_item in published["paths"].values()
        for method, operation in path_item.items()
        if method in HTTP_METHODS and isinstance(operation, dict)
    }


@pytest.mark.parametrize("bounded_context", MCP_BOUNDED_CONTEXTS)
def test_every_tool_has_a_substantive_description(bounded_context):
    tools = _published_tools(bounded_context)

    too_short = {name: desc for name, desc in tools.items() if len(desc) < MIN_DESCRIPTION_LENGTH}

    assert tools
    assert too_short == {}


@pytest.mark.parametrize("bounded_context", MCP_BOUNDED_CONTEXTS)
def test_tool_descriptions_are_distinct(bounded_context):
    descriptions = list(_published_tools(bounded_context).values())

    assert len(descriptions) == len(set(descriptions))


@pytest.mark.parametrize("bounded_context", MCP_BOUNDED_CONTEXTS)
def test_every_bounded_context_has_an_api_description(bounded_context):
    info = _source_spec(bounded_context).get("info") or {}

    assert len((info.get("description") or "").strip()) >= MIN_DESCRIPTION_LENGTH


def test_gateway_instructions_fit_the_agentcore_limit():
    # Built the same way as McpGatewayAgentcoreStack: one <context> block per bounded context.
    blocks = [
        f'<context name="{bc}">\n{_source_spec(bc)["info"]["description"].strip()}\n</context>'
        for bc in MCP_BOUNDED_CONTEXTS
    ]

    assert len("\n\n".join(blocks)) <= mcp_gateway_agentcore_app_stack._MAX_INSTRUCTIONS_LEN
