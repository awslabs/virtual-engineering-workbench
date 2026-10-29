from openapi_spec_validator import validate_spec

from app.packaging.entrypoints.s2s_api.model import api_model
from app.shared.test_utils import request_bounds


def test_schema_is_valid(api_schema):
    validate_spec(api_schema)


def test_method_responses_use_explicit_status_codes_for_api_gateway(api_schema):
    for path, methods in api_schema["paths"].items():
        for method, operation in methods.items():
            responses = operation["responses"]
            assert all(code.isdigit() and len(code) == 3 for code in responses), (method, path)
            for code in ("400", "401", "403", "404", "409", "422", "429", "500", "503"):
                assert responses[code] == {"$ref": "#/components/responses/Problem"}


def test_schema_exposes_component_and_recipe_slices(api_schema):
    assert set(api_schema["paths"]) == {
        "/projects/{projectId}/components",
        "/projects/{projectId}/components/{componentId}",
        "/projects/{projectId}/components/{componentId}/versions",
        "/projects/{projectId}/components/{componentId}/versions/{versionId}",
        "/projects/{projectId}/components/{componentId}/versions/{versionId}/release",
        "/projects/{projectId}/recipes",
        "/projects/{projectId}/recipes/{recipeId}",
        "/projects/{projectId}/recipes/{recipeId}/versions",
        "/projects/{projectId}/recipes/{recipeId}/versions/{versionId}",
        "/projects/{projectId}/recipes/{recipeId}/versions/{versionId}/release",
        "/projects/{projectId}/pipelines",
        "/projects/{projectId}/pipelines/{pipelineId}",
        "/projects/{projectId}/images",
        "/projects/{projectId}/images/{imageId}",
    }
    assert set(api_schema["paths"]["/projects/{projectId}/components/{componentId}"]) >= {
        "put",
        "get",
        "delete",
    }
    assert set(api_schema["paths"]["/projects/{projectId}/components/{componentId}/versions/{versionId}"]) >= {
        "put",
        "get",
        "delete",
    }
    assert set(api_schema["paths"]["/projects/{projectId}/recipes/{recipeId}/versions/{versionId}"]) >= {
        "get",
        "put",
        "delete",
    }


def test_schema_applies_component_and_recipe_scopes(api_schema):
    paths = api_schema["paths"]
    assert paths["/projects/{projectId}/components"]["get"]["security"] == [
        {"ClientCredentials": ["clients/packaging/component.read"]}
    ]
    version_put = paths["/projects/{projectId}/components/{componentId}/versions/{versionId}"]["put"]
    assert version_put["security"] == [{"ClientCredentials": ["clients/packaging/component.write"]}]
    assert paths["/projects/{projectId}/components/{componentId}/versions/{versionId}/release"]["post"]["security"] == [
        {"ClientCredentials": ["clients/packaging/component.release"]}
    ]
    assert paths["/projects/{projectId}/recipes"]["get"]["security"] == [
        {"ClientCredentials": ["clients/packaging/recipe.read"]}
    ]
    assert paths["/projects/{projectId}/recipes"]["post"]["security"] == [
        {"ClientCredentials": ["clients/packaging/recipe.write"]}
    ]
    assert paths["/projects/{projectId}/recipes/{recipeId}/versions/{versionId}/release"]["post"]["security"] == [
        {"ClientCredentials": ["clients/packaging/recipe.release"]}
    ]


def test_schema_applies_pipeline_and_image_scopes(api_schema):
    paths = api_schema["paths"]
    assert paths["/projects/{projectId}/pipelines"]["get"]["security"] == [
        {"ClientCredentials": ["clients/packaging/pipeline.read"]}
    ]
    assert paths["/projects/{projectId}/pipelines"]["post"]["security"] == [
        {"ClientCredentials": ["clients/packaging/pipeline.write"]}
    ]
    pipeline = paths["/projects/{projectId}/pipelines/{pipelineId}"]
    assert pipeline["get"]["security"] == [{"ClientCredentials": ["clients/packaging/pipeline.read"]}]
    assert pipeline["put"]["security"] == [{"ClientCredentials": ["clients/packaging/pipeline.write"]}]
    assert pipeline["delete"]["security"] == [{"ClientCredentials": ["clients/packaging/pipeline.write"]}]
    assert paths["/projects/{projectId}/images"]["get"]["security"] == [
        {"ClientCredentials": ["clients/packaging/pipeline.read"]}
    ]
    assert paths["/projects/{projectId}/images"]["post"]["security"] == [
        {"ClientCredentials": ["clients/packaging/pipeline.execute"]}
    ]
    assert paths["/projects/{projectId}/images/{imageId}"]["get"]["security"] == [
        {"ClientCredentials": ["clients/packaging/pipeline.read"]}
    ]


def test_schema_defines_pipeline_and_image_contracts(api_schema):
    schemas = api_schema["components"]["schemas"]
    assert schemas["CreatePipelineRequest"]["required"] == [
        "buildInstanceTypes",
        "pipelineDescription",
        "pipelineName",
        "pipelineSchedule",
        "recipeId",
        "recipeVersionId",
    ]
    assert set(schemas["UpdatePipelineRequest"]["properties"]) == {
        "buildInstanceTypes",
        "pipelineSchedule",
        "recipeVersionId",
        "productId",
    }
    assert "pipelineId" not in schemas["UpdatePipelineRequest"]["properties"]
    assert schemas["CreateImageRequest"]["required"] == ["pipelineId"]
    assert schemas["PipelinePage"]["required"] == ["pipelines"]
    assert schemas["PipelineResponse"]["required"] == ["pipeline"]
    assert schemas["ImagePage"]["required"] == ["images"]
    assert schemas["ImageResponse"]["required"] == ["image"]


def test_schema_uses_async_mutation_responses(api_schema):
    paths = api_schema["paths"]
    for path, method in [
        ("/projects/{projectId}/pipelines", "post"),
        ("/projects/{projectId}/pipelines/{pipelineId}", "put"),
        ("/projects/{projectId}/pipelines/{pipelineId}", "delete"),
        ("/projects/{projectId}/images", "post"),
    ]:
        response_ref = paths[path][method]["responses"]["202"]["$ref"]
        response = api_schema["components"]["responses"][response_ref.rsplit("/", 1)[-1]]
        assert response["headers"]["Retry-After"]["schema"]["default"] == "5"
    pipeline_action = api_schema["components"]["responses"]["PipelineAction"]
    image_action = api_schema["components"]["responses"]["ImageAction"]
    assert (
        pipeline_action["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/PipelineActionResponse"
    )
    assert image_action["content"]["application/json"]["schema"]["$ref"] == "#/components/schemas/CreateImageResponse"


def test_gateway_errors_use_problem_details(api_schema):
    responses = api_schema["x-amazon-apigateway-gateway-responses"]
    assert {
        "DEFAULT_4XX",
        "DEFAULT_5XX",
        "BAD_REQUEST_BODY",
        "BAD_REQUEST_PARAMETERS",
    } <= set(responses)
    for response in responses.values():
        assert response["responseParameters"]["gatewayresponse.header.Content-Type"] == ("'application/problem+json'")
        assert "application/problem+json" in response["responseTemplates"]


def test_components_use_generated_internal_ids_without_operation_resources(api_schema):
    paths = api_schema["paths"]
    assert "post" in paths["/projects/{projectId}/components"]
    assert "post" in paths["/projects/{projectId}/components/{componentId}/versions"]
    assert not any("/operations" in path or "external" in path.lower() for path in paths)
    parameters = api_schema["components"]["parameters"]
    assert parameters["ComponentId"]["name"] == "componentId"
    assert parameters["ComponentVersionId"]["name"] == "versionId"
    assert "IfMatch" not in parameters
    assert "ExternalId" not in parameters


def test_every_request_body_field_is_bounded(api_schema):
    # Backs the KICS maxLength / maxItems / numeric suppressions in the schema header.
    assert request_bounds.unbounded_request_fields(api_schema) == []


def test_request_models_enforce_the_schema_bounds(api_schema):
    models = request_bounds.pydantic_models(api_model)
    assert request_bounds.model_bound_mismatches(api_schema, models) == []


def test_body_operations_use_the_gateway_body_validator(api_schema):
    # The bounds are enforced by API Gateway before Lambda only if the body validator is on.
    validators = api_schema["x-amazon-apigateway-request-validators"]
    for path, methods in api_schema["paths"].items():
        for method, operation in methods.items():
            if "requestBody" in operation:
                validator = operation.get("x-amazon-apigateway-request-validator")
                assert validators[validator]["validateRequestBody"] is True, (method, path)
                # Powertools answers non-JSON bodies with 415; the handler maps it to a problem response.
                assert operation["responses"]["415"] == {"$ref": "#/components/responses/Problem"}, (method, path)
            else:
                assert "415" not in operation["responses"], (method, path)


def test_every_response_reference_has_a_body_schema(api_schema):
    # Backs the KICS a92be1d5 suppression: KICS does not follow $ref into components.responses.
    responses = api_schema["components"]["responses"]
    for path, methods in api_schema["paths"].items():
        for method, operation in methods.items():
            for code, response in operation["responses"].items():
                name = response["$ref"].split("/")[-1]
                content = responses[name]["content"]
                assert all("schema" in media for media in content.values()), (method, path, code)


def test_every_required_property_is_defined(api_schema):
    # Backs the KICS 2bd608ae suppression: remaining hits come from $ref properties KICS does not resolve.
    for name, schema in api_schema["components"]["schemas"].items():
        missing = set(schema.get("required", [])) - set(schema.get("properties", {}))
        assert not missing, (name, missing)
