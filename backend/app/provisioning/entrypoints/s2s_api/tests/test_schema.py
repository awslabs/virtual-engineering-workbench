import assertpy
from openapi_spec_validator import validate_spec

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
