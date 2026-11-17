import pytest
from assertpy import assert_that

from infra.helpers import mcp_openapi_transform as openapi_transform


def _spec_with(paths: dict) -> dict:
    return {"openapi": "3.0.1", "info": {"title": "t", "version": "1.0"}, "paths": paths}


def test_resolve_base_url_prefers_custom_domain_when_present():
    # ARRANGE / ACT / ASSERT
    assert_that(
        openapi_transform.resolve_base_url("https://api.execute", {"api1": "https://custom/projects"}, "api1")
    ).is_equal_to("https://custom/projects")


def test_resolve_base_url_falls_back_to_execute_api_when_no_custom_domain():
    assert_that(openapi_transform.resolve_base_url("https://api.execute", {}, "api1")).is_equal_to(
        "https://api.execute"
    )


def test_transform_strips_internal_swagger_docs_and_options():
    # ARRANGE
    spec = _spec_with(
        {
            "/internal/health": {"get": {"operationId": "health"}},
            "/_swagger": {"get": {"operationId": "swagger"}},
            "/openapi.json": {"get": {"operationId": "openapi"}},
            "/docs": {"get": {"operationId": "docs"}},
            "/widgets": {"get": {"operationId": "listWidgets"}, "options": {"operationId": "opt"}},
        }
    )

    # ACT
    result = openapi_transform.transform(spec, "https://base/x")

    # ASSERT
    assert_that(list(result["paths"].keys())).is_equal_to(["/widgets"])
    assert_that(result["paths"]["/widgets"]).does_not_contain_key("options")


def test_transform_sets_server_to_base_url():
    result = openapi_transform.transform(_spec_with({"/w": {"get": {"operationId": "g"}}}), "https://base/w")
    assert_that(result["servers"]).is_equal_to([{"url": "https://base/w"}])


def test_transform_does_not_mutate_input():
    # ARRANGE
    spec = _spec_with({"/internal/x": {"get": {"operationId": "x"}}, "/w": {"get": {"operationId": "g"}}})

    # ACT
    openapi_transform.transform(spec, "https://base")

    # ASSERT — original still has the internal path and no servers injected
    assert_that(spec["paths"]).contains_key("/internal/x")
    assert_that(spec).does_not_contain_key("servers")


def test_transform_folds_summary_into_description():
    # ARRANGE
    spec = _spec_with(
        {"/w": {"post": {"operationId": "updateWidget", "summary": "Update a widget", "description": "Details."}}}
    )

    # ACT
    op = openapi_transform.transform(spec, "https://base")["paths"]["/w"]["post"]

    # ASSERT
    assert_that(op["description"]).is_equal_to("Update a widget. Details.")
    assert_that(op["operationId"]).is_equal_to("updateWidget")


def test_transform_uses_summary_as_description_when_description_absent():
    spec = _spec_with({"/w": {"post": {"operationId": "u", "summary": "Update a widget"}}})
    op = openapi_transform.transform(spec, "https://base")["paths"]["/w"]["post"]
    assert_that(op["description"]).is_equal_to("Update a widget")


def test_transform_folds_parameter_constraints_into_description():
    # ARRANGE
    spec = _spec_with(
        {
            "/w": {
                "get": {
                    "operationId": "listWidgets",
                    "parameters": [
                        {
                            "name": "mode",
                            "in": "query",
                            "description": "Update strategy.",
                            "schema": {"type": "string", "enum": ["merge", "replace"], "default": "merge"},
                        }
                    ],
                }
            }
        }
    )

    # ACT
    param = openapi_transform.transform(spec, "https://base")["paths"]["/w"]["get"]["parameters"][0]

    # ASSERT
    assert_that(param["description"]).contains("allowed values: merge, replace").contains("default: merge")


def test_transform_folds_request_body_property_constraints():
    # ARRANGE
    spec = _spec_with(
        {
            "/w": {
                "post": {
                    "operationId": "createWidget",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "priority": {
                                            "type": "integer",
                                            "description": "Priority.",
                                            "minimum": 1,
                                            "maximum": 10,
                                        }
                                    },
                                }
                            }
                        }
                    },
                }
            }
        }
    )

    # ACT
    props = openapi_transform.transform(spec, "https://base")["paths"]["/w"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]["properties"]

    # ASSERT
    assert_that(props["priority"]["description"]).contains("min: 1").contains("max: 10")


def test_transform_coerces_datetime_info_version_to_string():
    # ARRANGE — yaml.safe_load turns `version: 2023-10-31T12:00:00Z` into a datetime
    import datetime

    spec = _spec_with({"/w": {"get": {"operationId": "g"}}})
    spec["info"]["version"] = datetime.datetime(2023, 10, 31, 12, 0, tzinfo=datetime.timezone.utc)

    # ACT
    result = openapi_transform.transform(spec, "https://base")

    # ASSERT
    assert_that(result["info"]["version"]).is_instance_of(str)


def test_transform_coerces_numeric_openapi_and_version_to_string():
    spec = {"openapi": 3.0, "info": {"title": "t", "version": 1.0}, "paths": {"/w": {"get": {"operationId": "g"}}}}
    result = openapi_transform.transform(spec, "https://base")
    assert_that(result["openapi"]).is_equal_to("3.0")
    assert_that(result["info"]["version"]).is_equal_to("1.0")


def test_transform_strips_authorization_header_parameter():
    # ARRANGE — specs declare an Authorization header param; it must not become a tool input
    spec = _spec_with(
        {
            "/w": {
                "get": {
                    "operationId": "g",
                    "parameters": [
                        {"name": "Authorization", "in": "header", "required": True, "schema": {"type": "string"}},
                        {"name": "authorization", "in": "header", "schema": {"type": "string"}},
                        {"name": "pageSize", "in": "query", "schema": {"type": "integer"}},
                    ],
                }
            }
        }
    )

    # ACT
    params = openapi_transform.transform(spec, "https://base")["paths"]["/w"]["get"]["parameters"]

    # ASSERT — both Authorization variants gone, other params kept
    names = [p["name"] for p in params]
    assert_that(names).is_equal_to(["pageSize"])


def test_transform_raises_when_operation_id_missing():
    # ARRANGE
    spec = _spec_with({"/w": {"get": {"summary": "no id"}}})

    # ACT / ASSERT
    with pytest.raises(openapi_transform.MissingOperationIdError) as exc:
        openapi_transform.transform(spec, "https://base")
    assert_that(str(exc.value)).contains("GET /w")


def test_transform_does_not_flag_excluded_operations_for_missing_id():
    # options methods are stripped, so their missing operationId must not fail validation
    spec = _spec_with({"/w": {"get": {"operationId": "g"}, "options": {}}})
    result = openapi_transform.transform(spec, "https://base")
    assert_that(result["paths"]["/w"]).does_not_contain_key("options")


def _substantive_description(label: str) -> str:
    return (
        f"{label} performs a documented gateway action for a specific project and returns the "
        "result needed by the next workflow step without requiring hidden caller context."
    )


def test_transform_strips_path_level_authorization_header_parameter():
    spec = _spec_with(
        {
            "/w": {
                "parameters": [
                    {
                        "name": "Authorization",
                        "in": "header",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "get": {"operationId": "g"},
            }
        }
    )

    result = openapi_transform.transform(spec, "https://base")

    assert result["paths"]["/w"]["parameters"] == []


def test_transform_enriches_referenced_request_body_properties():
    spec = _spec_with(
        {
            "/w": {
                "post": {
                    "operationId": "createWidget",
                    "requestBody": {
                        "content": {
                            "application/json": {"schema": {"$ref": "#/components/schemas/CreateWidgetRequest"}}
                        }
                    },
                }
            }
        }
    )
    spec["components"] = {
        "schemas": {
            "CreateWidgetRequest": {
                "type": "object",
                "properties": {
                    "priority": {
                        "type": "integer",
                        "description": "Priority from one through ten.",
                        "minimum": 1,
                        "maximum": 10,
                    }
                },
            }
        }
    }

    result = openapi_transform.transform(spec, "https://base")

    description = result["components"]["schemas"]["CreateWidgetRequest"]["properties"]["priority"]["description"]
    assert_that(description).contains("min: 1").contains("max: 10")


def test_target_validation_rejects_duplicate_operation_ids_across_targets():
    first = _spec_with(
        {"/first": {"get": {"operationId": "GetWidget", "description": _substantive_description("First")}}}
    )
    second = _spec_with(
        {"/second": {"get": {"operationId": "GetWidget", "description": _substantive_description("Second")}}}
    )

    with pytest.raises(openapi_transform.TargetMetadataError, match="duplicate operationId/tool name 'GetWidget'"):
        openapi_transform.validate_target_specs({"first": first, "second": second})


def test_target_validation_rejects_duplicate_tool_descriptions_across_targets():
    description = _substantive_description("Shared")
    first = _spec_with({"/first": {"get": {"operationId": "GetFirst", "description": description}}})
    second = _spec_with({"/second": {"get": {"operationId": "GetSecond", "description": description}}})

    with pytest.raises(openapi_transform.TargetMetadataError, match="duplicate tool description"):
        openapi_transform.validate_target_specs({"first": first, "second": second})


def test_target_validation_checks_all_surviving_parameters():
    spec = _spec_with(
        {
            "/w": {
                "get": {
                    "operationId": "GetWidget",
                    "description": _substantive_description("GetWidget"),
                    "parameters": [
                        {"name": "trace", "in": "header", "schema": {"type": "string"}},
                        {"name": "projectId", "in": "path", "schema": {"type": "string"}},
                    ],
                }
            }
        }
    )

    with pytest.raises(openapi_transform.TargetMetadataError) as exc:
        openapi_transform.validate_target_specs({"widgets": spec})

    assert "parameter 'projectId'" in str(exc.value)
    assert "parameter 'trace'" in str(exc.value)


def test_target_validation_resolves_referenced_request_properties():
    spec = _spec_with(
        {
            "/w": {
                "post": {
                    "operationId": "CreateWidget",
                    "description": _substantive_description("CreateWidget"),
                    "requestBody": {
                        "content": {
                            "application/json": {"schema": {"$ref": "#/components/schemas/CreateWidgetRequest"}}
                        }
                    },
                }
            }
        }
    )
    spec["components"] = {
        "schemas": {
            "CreateWidgetRequest": {
                "type": "object",
                "properties": {"priority": {"type": "integer"}},
            }
        }
    }

    with pytest.raises(openapi_transform.TargetMetadataError, match="request property 'priority'"):
        openapi_transform.validate_target_specs({"widgets": spec})


def test_transform_applies_explicit_mcp_operation_id_without_mutating_source():
    spec = _spec_with(
        {
            "/w": {
                "get": {
                    "operationId": "GetAvailableProducts",
                    "x-mcp-operation-id": "ListProvisionableProducts",
                }
            }
        }
    )

    result = openapi_transform.transform(spec, "https://base")

    operation = result["paths"]["/w"]["get"]
    assert operation["operationId"] == "ListProvisionableProducts"
    assert "x-mcp-operation-id" not in operation
    assert spec["paths"]["/w"]["get"]["operationId"] == "GetAvailableProducts"


def test_transform_enriches_path_level_parameters():
    spec = _spec_with(
        {
            "/w": {
                "parameters": [
                    {
                        "name": "mode",
                        "in": "query",
                        "description": "Update strategy.",
                        "schema": {
                            "type": "string",
                            "enum": ["merge", "replace"],
                            "default": "merge",
                        },
                    }
                ],
                "get": {"operationId": "listWidgets"},
            }
        }
    )

    result = openapi_transform.transform(spec, "https://base")

    description = result["paths"]["/w"]["parameters"][0]["description"]
    assert_that(description).contains("allowed values: merge, replace").contains("default: merge")


def test_transform_strips_referenced_authorization_parameter():
    spec = _spec_with(
        {
            "/w": {
                "parameters": [{"$ref": "#/components/parameters/Authorization"}],
                "get": {"operationId": "getWidget"},
            }
        }
    )
    spec["components"] = {
        "parameters": {
            "Authorization": {
                "name": "Authorization",
                "in": "header",
                "required": True,
                "schema": {"type": "string"},
            }
        }
    }

    result = openapi_transform.transform(spec, "https://base")

    assert result["paths"]["/w"]["parameters"] == []


@pytest.mark.parametrize(
    "exposed_value,missing_ref",
    [
        (
            {"parameters": [{"$ref": "#/components/parameters/Missing"}]},
            "#/components/parameters/Missing",
        ),
        (
            {"requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/Missing"}}}}},
            "#/components/schemas/Missing",
        ),
    ],
)
def test_transform_rejects_unresolved_local_refs_in_exposed_inputs(exposed_value, missing_ref):
    operation = {"operationId": "updateWidget", **exposed_value}
    spec = _spec_with({"/w": {"post": operation}})

    with pytest.raises(openapi_transform.UnresolvedLocalRefError, match=missing_ref):
        openapi_transform.transform(spec, "https://base")


def test_target_validation_rejects_unresolved_nested_request_property_ref():
    spec = _spec_with(
        {
            "/w": {
                "post": {
                    "operationId": "CreateWidget",
                    "description": _substantive_description("CreateWidget"),
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"widget": {"$ref": "#/components/schemas/Missing"}},
                                }
                            }
                        }
                    },
                }
            }
        }
    )

    with pytest.raises(
        openapi_transform.UnresolvedLocalRefError,
        match="#/components/schemas/Missing",
    ):
        openapi_transform.validate_target_specs({"widgets": spec})


def test_recursive_request_schema_terminates_and_validates():
    spec = _spec_with(
        {
            "/nodes": {
                "post": {
                    "operationId": "CreateNode",
                    "description": _substantive_description("CreateNode"),
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"root": {"$ref": "#/components/schemas/Node"}},
                                }
                            }
                        }
                    },
                }
            }
        }
    )
    spec["components"] = {
        "schemas": {
            "Node": {
                "type": "object",
                "description": "A node in the recursive request tree.",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The display name for this node.",
                    },
                    "child": {"$ref": "#/components/schemas/Node"},
                },
            }
        }
    }

    published = openapi_transform.transform(spec, "https://base")

    openapi_transform.validate_target_specs({"nodes": published})
