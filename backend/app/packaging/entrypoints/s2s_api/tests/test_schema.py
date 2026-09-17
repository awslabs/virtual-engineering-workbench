from openapi_spec_validator import validate_spec


def test_schema_is_valid(api_schema):
    validate_spec(api_schema)


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
