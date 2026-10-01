import json
from types import SimpleNamespace
from unittest import mock

import pytest
from openapi_spec_validator.readers import read_from_filename

from app.packaging.domain.ports.service_client_project_access_service import ServiceClientProjectAccessService
from app.shared.api import secrets_manager_api


@pytest.fixture(autouse=True)
def runtime_environment(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-west-1")
    monkeypatch.setenv("AUDIT_LOGGING_KEY_NAME", "audit-key")
    monkeypatch.setenv("POWERTOOLS_METRICS_NAMESPACE", "Tests")
    monkeypatch.setenv("POWERTOOLS_SERVICE_NAME", "Packaging")
    monkeypatch.setattr(secrets_manager_api.SecretsManagerAPI, "get_secret_value", lambda self, secret_id: "key")


@pytest.fixture()
def lambda_context():
    return SimpleNamespace(
        function_name="test",
        memory_limit_in_mb=128,
        invoked_function_arn="arn:aws:lambda:eu-west-1:000000000:function:test",
        aws_request_id="lambda-request-1",
    )


@pytest.fixture()
def client_event():
    def build(method, path, body=None, headers=None, query=None, client_id="client-1", scopes=None):
        request_headers = {"Accept": "application/json", "Content-Type": "application/json", **(headers or {})}
        return {
            "resource": path,
            "path": path,
            "httpMethod": method,
            "headers": request_headers,
            "multiValueHeaders": {key: [value] for key, value in request_headers.items()},
            "queryStringParameters": query,
            "multiValueQueryStringParameters": None,
            "pathParameters": {},
            "stageVariables": None,
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "client_id": client_id,
                        "token_use": "access",
                        "scope": " ".join(
                            scopes
                            or [
                                "clients/packaging/component.read",
                                "clients/packaging/component.write",
                                "clients/packaging/component.release",
                            ]
                        ),
                    }
                },
                "resourcePath": path,
                "httpMethod": method,
                "requestId": "api-request-1",
                "identity": {"sourceIp": "127.0.0.1"},
                "stage": "test",
            },
            "body": json.dumps(body) if body is not None else None,
            "isBase64Encoded": False,
        }

    return build


@pytest.fixture()
def mocked_dependencies():
    return SimpleNamespace(
        project_access_service=mock.create_autospec(ServiceClientProjectAccessService),
        command_bus=mock.Mock(),
        recipe_domain_qry_srv=mock.Mock(),
        recipe_version_domain_qry_srv=mock.Mock(),
        pipeline_domain_qry_srv=mock.Mock(),
        image_domain_qry_srv=mock.Mock(),
        component_domain_qry_srv=mock.Mock(),
        component_version_domain_qry_srv=mock.Mock(),
        component_version_qry_srv=mock.Mock(),
    )


@pytest.fixture()
def component_body():
    return {
        "componentName": "agent",
        "componentDescription": "installs the agent",
        "componentPlatform": "Linux",
        "componentSupportedArchitectures": ["amd64"],
        "componentSupportedOsVersions": ["Ubuntu 24"],
    }


@pytest.fixture()
def version_body():
    return {
        "componentVersionDescription": "install agent",
        "componentVersionYamlDefinition": "schemaVersion: 1\nphases: []\n",
        "componentVersionReleaseType": "MAJOR",
        "componentVersionDependencies": [],
        "softwareVendor": "Example",
        "softwareVersion": "1.0.0",
    }


@pytest.fixture()
def recipe_body():
    return {
        "recipeDescription": "builds the engineering image",
        "recipeName": "engineering-image",
        "recipePlatform": "Linux",
        "recipeArchitecture": "amd64",
        "recipeOsVersion": "Ubuntu 24",
    }


@pytest.fixture()
def pipeline_body():
    return {
        "buildInstanceTypes": ["t3.large"],
        "pipelineDescription": "builds engineering images",
        "pipelineName": "engineering-images",
        "pipelineSchedule": "0 0 ? * MON *",
        "recipeId": "reci-1",
        "recipeVersionId": "vers-1",
    }


@pytest.fixture()
def api_schema():
    schema_path = __file__.replace("tests/conftest.py", "schema/proserve-workbench-s2s-packaging-api-schema.yaml")
    specification, _ = read_from_filename(schema_path)
    return specification
