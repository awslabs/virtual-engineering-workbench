import importlib
import json
from types import SimpleNamespace
from unittest import mock

import boto3
import moto
import pytest

from app.packaging.adapters.query_services.dynamodb_component_query_service import DynamoDBComponentQueryService
from app.packaging.adapters.query_services.dynamodb_component_version_query_service import (
    DynamoDBComponentVersionQueryService,
)
from app.packaging.adapters.query_services.dynamodb_recipe_query_service import DynamoDBRecipeQueryService
from app.packaging.adapters.query_services.dynamodb_recipe_version_query_service import (
    DynamoDBRecipeVersionQueryService,
)
from app.packaging.adapters.repository import dynamo_entity_config
from app.packaging.domain.command_handlers.component import (
    create_component_command_handler,
    create_component_version_command_handler,
)
from app.packaging.domain.command_handlers.recipe import create_recipe_command_handler
from app.packaging.domain.commands.component import create_component_command, create_component_version_command
from app.packaging.domain.commands.recipe import create_recipe_command
from app.packaging.domain.ports.service_client_project_access_service import ServiceClientProjectAccessService
from app.packaging.domain.query_services.component_domain_query_service import ComponentDomainQueryService
from app.packaging.domain.query_services.component_version_domain_query_service import (
    ComponentVersionDomainQueryService,
)
from app.packaging.domain.query_services.image_domain_query_service import ImageDomainQueryService
from app.packaging.domain.query_services.pipeline_domain_query_service import PipelineDomainQueryService
from app.packaging.domain.query_services.recipe_domain_query_service import RecipeDomainQueryService
from app.packaging.domain.query_services.recipe_version_domain_query_service import RecipeVersionDomainQueryService
from app.packaging.entrypoints.s2s_api import bootstrapper
from app.shared.adapters.message_bus import in_memory_command_bus
from app.shared.adapters.message_bus.message_bus import MessageBus
from app.shared.adapters.unit_of_work_v2 import dynamodb_unit_of_work

PACKAGING_TABLE = "packaging-s2s-e2e"
ENTITIES_GSI = "entities"
INVERTED_GSI = "inverted"
STATUS_GSI = "status"


class ProjectAccess(ServiceClientProjectAccessService):
    def require_access(self, client_id: str, project_id: str) -> None:
        return None


def create_table(dynamodb):
    return dynamodb.create_table(
        TableName=PACKAGING_TABLE,
        KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"}, {"AttributeName": "SK", "KeyType": "RANGE"}],
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
            {"AttributeName": "GSI_PK", "AttributeType": "S"},
            {"AttributeName": "GSI_SK", "AttributeType": "S"},
            {"AttributeName": "entity", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
        GlobalSecondaryIndexes=[
            {
                "IndexName": STATUS_GSI,
                "KeySchema": [
                    {"AttributeName": "GSI_PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI_SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": ENTITIES_GSI,
                "KeySchema": [
                    {"AttributeName": "entity", "KeyType": "HASH"},
                    {"AttributeName": "SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": INVERTED_GSI,
                "KeySchema": [{"AttributeName": "SK", "KeyType": "HASH"}, {"AttributeName": "PK", "KeyType": "RANGE"}],
                "Projection": {"ProjectionType": "KEYS_ONLY"},
            },
        ],
    )


def load_handler(monkeypatch, dependencies):
    monkeypatch.setattr(bootstrapper, "bootstrap", mock.Mock(return_value=dependencies))
    from app.packaging.entrypoints.s2s_api import handler

    return importlib.reload(handler)


@pytest.fixture()
def e2e_runtime(monkeypatch):
    with moto.mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="eu-west-1")
        create_table(dynamodb)
        client = dynamodb.meta.client
        uow = dynamodb_unit_of_work.DynamoDBUnitOfWork(
            table_name=PACKAGING_TABLE,
            dynamodb_client=client,
            repo_factories=dynamo_entity_config.EntityConfigurator(table_name=PACKAGING_TABLE).repo_factories(),
            logger=mock.Mock(),
        )
        component_query = DynamoDBComponentQueryService(PACKAGING_TABLE, client, INVERTED_GSI, ENTITIES_GSI)
        version_query = DynamoDBComponentVersionQueryService(PACKAGING_TABLE, client, STATUS_GSI, ENTITIES_GSI)
        recipe_query = DynamoDBRecipeQueryService(PACKAGING_TABLE, client, ENTITIES_GSI)
        recipe_version_query = DynamoDBRecipeVersionQueryService(PACKAGING_TABLE, client, ENTITIES_GSI, STATUS_GSI)
        message_bus = mock.create_autospec(MessageBus)
        command_bus = in_memory_command_bus.InMemoryCommandBus(logger=mock.Mock())
        command_bus.register_handler(
            create_component_command.CreateComponentCommand,
            lambda command: create_component_command_handler.handle(command, uow),
        ).register_handler(
            create_component_version_command.CreateComponentVersionCommand,
            lambda command: create_component_version_command_handler.handle(
                command, uow, message_bus, component_query, version_query
            ),
        ).register_handler(
            create_recipe_command.CreateRecipeCommand,
            lambda command: create_recipe_command_handler.handle(command, uow),
        )
        dependencies = bootstrapper.Dependencies(
            project_access_service=ProjectAccess(),
            command_bus=command_bus,
            component_domain_qry_srv=ComponentDomainQueryService(component_query),
            component_version_domain_qry_srv=ComponentVersionDomainQueryService(
                component_query, version_query, mock.Mock()
            ),
            component_version_qry_srv=version_query,
            recipe_domain_qry_srv=RecipeDomainQueryService(recipe_query),
            recipe_version_domain_qry_srv=RecipeVersionDomainQueryService(recipe_query, recipe_version_query),
            pipeline_domain_qry_srv=mock.create_autospec(PipelineDomainQueryService, instance=True),
            image_domain_qry_srv=mock.create_autospec(ImageDomainQueryService, instance=True),
        )
        yield SimpleNamespace(handler=load_handler(monkeypatch, dependencies))


def call(runtime, event, context):
    return runtime.handler.handler(event, context)


def test_component_create_read_and_version_command_round_trip(
    e2e_runtime, client_event, lambda_context, component_body, version_body
):
    created = call(
        e2e_runtime,
        client_event(
            "POST", "/projects/proj-1/components", component_body, scopes=["clients/packaging/component.write"]
        ),
        lambda_context,
    )
    component_id = json.loads(created["body"])["componentId"]
    read = call(
        e2e_runtime,
        client_event("GET", f"/projects/proj-1/components/{component_id}", scopes=["clients/packaging/component.read"]),
        lambda_context,
    )
    version = call(
        e2e_runtime,
        client_event(
            "POST",
            f"/projects/proj-1/components/{component_id}/versions",
            version_body,
            scopes=["clients/packaging/component.write"],
        ),
        lambda_context,
    )

    assert created["statusCode"] == 201
    assert json.loads(read["body"])["component"]["componentId"] == component_id
    assert version["statusCode"] == 202
    assert json.loads(version["body"])["componentVersionId"].startswith("vers-")


def test_recipe_create_and_read_round_trip_uses_internal_id(e2e_runtime, client_event, lambda_context, recipe_body):
    created = call(
        e2e_runtime,
        client_event("POST", "/projects/proj-1/recipes", recipe_body, scopes=["clients/packaging/recipe.write"]),
        lambda_context,
    )
    recipe_id = json.loads(created["body"])["recipeId"]
    read = call(
        e2e_runtime,
        client_event("GET", f"/projects/proj-1/recipes/{recipe_id}", scopes=["clients/packaging/recipe.read"]),
        lambda_context,
    )

    assert created["statusCode"] == 201
    assert recipe_id.startswith("reci-")
    assert json.loads(read["body"])["recipe"]["recipeId"] == recipe_id
