import re

import assertpy
from openapi_spec_validator import validate_spec

from app.packaging.entrypoints.api.model import api_model
from app.shared.test_utils import openapi_analyzer


def test_api_schema_should_be_valid(api_schema):
    # ACT / ASSERT
    validate_spec(api_schema)


def test_api_schema_should_have_http_method_cors_configured(api_schema):
    # ARRANGE
    path_contexts = openapi_analyzer.OpenAPIAnalyzer.from_dict(api_schema).path_contexts

    # ACT
    result = {
        path_context.path: path_context.cors_method_error
        for path_context in path_contexts
        if path_context.cors_method_error
    }

    # ASSERT
    assertpy.assert_that(result).described_as("HTTP methods not configured with CORS").is_empty()


def test_api_schema_should_have_header_cors_configured(api_schema):
    # ARRANGE
    path_contexts = openapi_analyzer.OpenAPIAnalyzer.from_dict(api_schema).path_contexts

    # ACT
    result = {
        path_context.path: path_context.cors_header_error
        for path_context in path_contexts
        if path_context.cors_header_error
    }

    # ASSERT
    assertpy.assert_that(result).described_as("HTTP headers not configured with CORS").is_empty()


def test_api_schema_should_have_correct_roles_configured(api_schema):
    # ARRANGE
    path_contexts = openapi_analyzer.OpenAPIAnalyzer.from_dict(api_schema).path_contexts

    # ACT
    incorrect_roles = {ctx.path: ctx.tag_name_errors for ctx in path_contexts if ctx.tag_name_errors}

    # ASSERT
    assertpy.assert_that(incorrect_roles).described_as("Incorrect role names detected").is_empty()


def test_api_schema_should_have_auth_configured(api_schema):
    # ARRANGE
    path_contexts = openapi_analyzer.OpenAPIAnalyzer.from_dict(api_schema).path_contexts

    # ACT
    methods_wo_auth = {ctx.path: ctx.auth_errors for ctx in path_contexts if ctx.auth_errors}

    # ASSERT
    assertpy.assert_that(methods_wo_auth).described_as("Methods without auth detected").is_empty()


def test_client_token_pattern_matches_between_schema_and_model(api_schema):
    # The schema and the request model each declare the clientToken charset; they must agree.
    schema_prop = api_schema["components"]["schemas"]["CreateAgreementRequestRequest"]["properties"]["clientToken"]
    model_prop = api_model.CreateAgreementRequestRequest.model_json_schema()["properties"]["clientToken"]["anyOf"][0]

    assert schema_prop["pattern"] == model_prop["pattern"] == api_model.CLIENT_TOKEN_PATTERN


def test_api_schema_should_accept_both_marketplace_product_id_formats_as_parent_image(api_schema):
    """API Gateway validates the body against these patterns before the Lambda runs."""
    # ARRANGE
    schemas = api_schema["components"]["schemas"]
    patterns = {
        name: schemas[name]["properties"]["parentImageProductId"]["pattern"]
        for name in ("CreateRecipeVersionRequest", "UpdateRecipeVersionRequest")
    }

    # ACT / ASSERT
    for name, pattern in patterns.items():
        for product_id in ("prod-ib2w5aw4ynhey", "47489723-7305-4e22-8b22-b0d57054f216"):
            assertpy.assert_that(re.match(pattern, product_id)).described_as(f"{name} {product_id}").is_not_none()
        assertpy.assert_that(re.match(pattern, "ami-0123")).described_as(name).is_none()
    assertpy.assert_that(re.match(patterns["UpdateRecipeVersionRequest"], "")).is_not_none()
