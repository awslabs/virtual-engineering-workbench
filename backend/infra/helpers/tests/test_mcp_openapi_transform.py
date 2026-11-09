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
