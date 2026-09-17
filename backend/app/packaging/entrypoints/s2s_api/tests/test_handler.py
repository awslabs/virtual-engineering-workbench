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
