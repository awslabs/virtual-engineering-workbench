import importlib
import json
from unittest import mock

from aws_lambda_powertools.event_handler.exceptions import NotFoundError

from app.packaging.domain.exceptions.s2s_exception import ProjectAccessDenied


def load_handler(monkeypatch, dependencies):
    from app.packaging.entrypoints.s2s_api import bootstrapper

    monkeypatch.setattr(bootstrapper, "bootstrap", mock.Mock(return_value=dependencies))
    from app.packaging.entrypoints.s2s_api import handler

    return importlib.reload(handler)


def test_create_component_generates_an_internal_id_and_uses_service_actor(
    monkeypatch, mocked_dependencies, lambda_context, client_event, component_body
):
    handler = load_handler(monkeypatch, mocked_dependencies)

    response = handler.handler(
        client_event(
            "POST",
            "/projects/proj-1/components",
            component_body,
            scopes=["clients/packaging/component.write"],
        ),
        lambda_context,
    )

    assert response["statusCode"] == 201
    component_id = json.loads(response["body"])["componentId"]
    assert component_id.startswith("comp-")
    command = mocked_dependencies.command_bus.handle.call_args.args[0]
    assert command.componentId.value == component_id
    assert command.createdBy.value == "service:client-1"


def test_create_component_version_returns_the_handler_generated_id(
    monkeypatch, mocked_dependencies, lambda_context, client_event, version_body
):
    mocked_dependencies.command_bus.handle.return_value = {"componentVersionId": "vers-1"}
    handler = load_handler(monkeypatch, mocked_dependencies)

    response = handler.handler(
        client_event(
            "POST",
            "/projects/proj-1/components/comp-1/versions",
            version_body,
            scopes=["clients/packaging/component.write"],
        ),
        lambda_context,
    )

    assert response["statusCode"] == 202
    assert json.loads(response["body"]) == {"componentVersionId": "vers-1"}
    command = mocked_dependencies.command_bus.handle.call_args.args[0]
    assert command.componentId.value == "comp-1"
    assert command.createdBy.value == "service:client-1"
    assert "componentVersionId" not in command.model_dump()


def test_component_version_requires_parent_project_membership_before_looking_up_version(
    monkeypatch, mocked_dependencies, lambda_context, client_event
):
    mocked_dependencies.component_domain_qry_srv.require_component_in_project.side_effect = NotFoundError(
        "Component comp-1 not found in project proj-1."
    )
    handler = load_handler(monkeypatch, mocked_dependencies)

    response = handler.handler(
        client_event(
            "GET",
            "/projects/proj-1/components/comp-1/versions/vers-1",
            scopes=["clients/packaging/component.read"],
        ),
        lambda_context,
    )

    assert response["statusCode"] == 404
    mocked_dependencies.component_version_qry_srv.get_component_version.assert_not_called()


def test_component_release_requires_release_scope_before_command(
    monkeypatch, mocked_dependencies, lambda_context, client_event
):
    handler = load_handler(monkeypatch, mocked_dependencies)

    response = handler.handler(
        client_event(
            "POST",
            "/projects/proj-1/components/comp-1/versions/vers-1/release",
            scopes=["clients/packaging/component.write"],
        ),
        lambda_context,
    )

    assert response["statusCode"] == 403
    assert json.loads(response["body"])["code"] == "INSUFFICIENT_SCOPE"
    mocked_dependencies.command_bus.handle.assert_not_called()


def test_retire_component_version_uses_service_authorization(
    monkeypatch, mocked_dependencies, lambda_context, client_event
):
    mocked_dependencies.command_bus.handle.return_value = {"componentVersionId": "vers-1"}
    handler = load_handler(monkeypatch, mocked_dependencies)

    response = handler.handler(
        client_event(
            "DELETE",
            "/projects/proj-1/components/comp-1/versions/vers-1",
            scopes=["clients/packaging/component.write"],
        ),
        lambda_context,
    )

    assert response["statusCode"] == 202
    command = mocked_dependencies.command_bus.handle.call_args.args[0]
    assert command.serviceAuthorized is True
    assert command.lastUpdatedBy.value == "service:client-1"


def test_project_denial_happens_before_component_query(monkeypatch, mocked_dependencies, lambda_context, client_event):
    mocked_dependencies.project_access_service.require_access.side_effect = ProjectAccessDenied()
    handler = load_handler(monkeypatch, mocked_dependencies)

    response = handler.handler(
        client_event("GET", "/projects/proj-1/components/comp-1", scopes=["clients/packaging/component.read"]),
        lambda_context,
    )

    assert response["statusCode"] == 403
    assert json.loads(response["body"])["code"] == "PROJECT_ACCESS_DENIED"
    mocked_dependencies.component_domain_qry_srv.require_component_in_project.assert_not_called()


def test_create_recipe_uses_service_actor_and_returns_generated_id(
    monkeypatch, mocked_dependencies, lambda_context, client_event, recipe_body
):
    mocked_dependencies.command_bus.handle.return_value = {"recipeId": "reci-1"}
    handler = load_handler(monkeypatch, mocked_dependencies)

    response = handler.handler(
        client_event(
            "POST",
            "/projects/proj-1/recipes",
            recipe_body,
            scopes=["clients/packaging/recipe.write"],
        ),
        lambda_context,
    )

    assert response["statusCode"] == 201
    assert json.loads(response["body"]) == {"recipeId": "reci-1"}
    command = mocked_dependencies.command_bus.handle.call_args.args[0]
    assert command.createdBy.value == "service:client-1"


def test_create_component_version_rejects_an_oversized_free_text_field(
    monkeypatch, mocked_dependencies, lambda_context, client_event, version_body
):
    # softwareVendor has no value object; the request model is the only length check.
    handler = load_handler(monkeypatch, mocked_dependencies)

    response = handler.handler(
        client_event(
            "POST",
            "/projects/proj-1/components/comp-1/versions",
            {**version_body, "softwareVendor": "x" * 257},
            scopes=["clients/packaging/component.write"],
        ),
        lambda_context,
    )

    assert response["statusCode"] == 400
    assert json.loads(response["body"])["code"] == "INVALID_REQUEST"
    mocked_dependencies.command_bus.handle.assert_not_called()


def test_create_component_rejects_too_many_array_items(
    monkeypatch, mocked_dependencies, lambda_context, client_event, component_body
):
    handler = load_handler(monkeypatch, mocked_dependencies)

    response = handler.handler(
        client_event(
            "POST",
            "/projects/proj-1/components",
            {**component_body, "componentSupportedArchitectures": ["amd64"] * 21},
            scopes=["clients/packaging/component.write"],
        ),
        lambda_context,
    )

    assert response["statusCode"] == 400
    mocked_dependencies.command_bus.handle.assert_not_called()


def test_create_component_version_accepts_a_field_at_the_limit(
    monkeypatch, mocked_dependencies, lambda_context, client_event, version_body
):
    mocked_dependencies.command_bus.handle.return_value = {"componentVersionId": "vers-1"}
    handler = load_handler(monkeypatch, mocked_dependencies)

    response = handler.handler(
        client_event(
            "POST",
            "/projects/proj-1/components/comp-1/versions",
            {**version_body, "softwareVendor": "x" * 256},
            scopes=["clients/packaging/component.write"],
        ),
        lambda_context,
    )

    assert response["statusCode"] == 202


def test_non_json_body_returns_a_documented_415_problem(
    monkeypatch, mocked_dependencies, lambda_context, client_event, component_body
):
    handler = load_handler(monkeypatch, mocked_dependencies)
    event = client_event(
        "POST",
        "/projects/proj-1/components",
        component_body,
        headers={"Content-Type": "text/plain"},
        scopes=["clients/packaging/component.write"],
    )
    event["body"] = "componentName=agent"

    response = handler.handler(event, lambda_context)

    assert response["statusCode"] == 415
    assert response["headers"]["Content-Type"] == "application/problem+json"
    assert json.loads(response["body"])["code"] == "UNSUPPORTED_MEDIA_TYPE"
    mocked_dependencies.command_bus.handle.assert_not_called()


def all_log_text(caplog) -> str:
    # Message plus every extra field Powertools would serialise.
    return "\n".join(
        json.dumps({**record.__dict__, "msg": record.getMessage()}, default=str) for record in caplog.records
    )


def test_request_log_contains_metadata_but_not_body_headers_or_query_values(
    monkeypatch,
    mocked_dependencies,
    lambda_context,
    client_event,
    component_body,
    caplog,
):
    handler = load_handler(monkeypatch, mocked_dependencies)
    event = client_event(
        "POST",
        "/projects/proj-1/components",
        {**component_body, "componentDescription": "body-marker-value"},
        headers={
            "Authorization": "Bearer token-marker-value",
            "X-Custom": "header-marker-value",
        },
        query={"filter": "query-marker-value"},
        scopes=["clients/packaging/component.write"],
    )

    handler.handler(event, lambda_context)

    logs = all_log_text(caplog)
    request_logs = [r for r in caplog.records if r.getMessage() == "Packaging S2S request received"]
    assert len(request_logs) == 1
    assert request_logs[0].request == {
        "httpMethod": "POST",
        "resource": "/projects/proj-1/components",
        "path": "/projects/proj-1/components",
        "stage": "test",
        "sourceIp": "127.0.0.1",
        "queryParameterNames": ["filter"],
        "hasBody": True,
    }
    for marker in (
        "body-marker-value",
        "token-marker-value",
        "header-marker-value",
        "query-marker-value",
    ):
        assert marker not in logs


def test_validation_failure_log_names_fields_without_submitted_values(
    monkeypatch, mocked_dependencies, lambda_context, client_event, version_body, caplog
):
    handler = load_handler(monkeypatch, mocked_dependencies)
    oversized_value = "secret-marker-" + "x" * 250

    response = handler.handler(
        client_event(
            "POST",
            "/projects/proj-1/components/comp-1/versions",
            {**version_body, "softwareVendor": oversized_value},
            scopes=["clients/packaging/component.write"],
        ),
        lambda_context,
    )

    assert response["statusCode"] == 400
    logs = all_log_text(caplog)
    failure_logs = [r for r in caplog.records if r.getMessage() == "Packaging S2S request validation failed"]
    assert len(failure_logs) == 1
    errors = failure_logs[0].errors
    assert errors and all(set(item) == {"loc", "type"} for item in errors)
    assert any("softwareVendor" in item["loc"] for item in errors)
    assert "secret-marker-" not in logs
