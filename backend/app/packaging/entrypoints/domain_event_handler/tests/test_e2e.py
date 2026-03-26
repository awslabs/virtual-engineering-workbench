from datetime import datetime
from unittest.mock import MagicMock, patch

import botocore
import pytest

orig = botocore.client.BaseClient._make_api_call


@pytest.fixture()
def get_component_entity():
    def _get_component_entity(version_suffix: str = "1234abcd"):
        return {
            "PK": f"COMPONENT#comp-{version_suffix}",
            "SK": f"COMPONENT#comp-{version_suffix}",
            "componentDescription": "Document to install Google Chrome software for a Ubuntu instance",
            "componentId": f"comp-{version_suffix}",
            "componentName": f"test-component-{version_suffix}",
            "componentPlatform": "Linux",
            "componentSupportedArchitectures": ["amd64"],
            "componentSupportedOsVersions": ["Ubuntu 24"],
            "status": "CREATED",
            "createDate": "2023-11-01T17:09:44.899480+00:00",
            "createdBy": "T0011AA",
            "lastUpdateDate": "2023-11-01T17:09:44.899480+00:00",
            "lastUpdatedBy": "T0011AA",
        }

    return _get_component_entity


@pytest.fixture()
def get_component_version_entity():
    def _get_component_version_entity(version_suffix: str = "1234abcd"):
        return {
            "PK": f"COMPONENT#comp-{version_suffix}",
            "SK": f"VERSION#vers-{version_suffix}",
            "componentBuildVersionArn": None,
            "componentId": f"comp-{version_suffix}",
            "componentName": f"test-component-{version_suffix}",
            "componentPlatform": "Linux",
            "componentSupportedArchitectures": ["amd64"],
            "componentSupportedOsVersions": ["Ubuntu 24"],
            "componentVersionDescription": "Initial version",
            "componentVersionId": f"vers-{version_suffix}",
            "componentVersionName": "1.0.0-rc.1",
            "componentVersionS3Uri": None,
            "associatedComponentsVersions": [],
            "associatedRecipesVersions": [],
            "dependenciesComponentsVersions": [],
            "softwareVendor": "vector",
            "softwareVersion": "1.0.0",
            "licenseDashboard": "https://proserve.license.com/index.php?action=dashboard.view&dashboardid=1",
            "notes": "This is a test component software version.",
            "createDate": "2023-11-02T08:14:25.194377+00:00",
            "createdBy": "T0011AA",
            "lastUpdateDate": "2023-11-02T08:14:25.194377+00:00",
            "lastUpdatedBy": "T0011AA",
            "status": "VALIDATED",
        }

    return _get_component_version_entity


@pytest.fixture()
def create_component_version_entities(backend_app_dynamodb_table, get_component_entity, get_component_version_entity):
    def _create_component_version_entities(version_suffix: str = "1234abcd"):
        backend_app_dynamodb_table.put_item(Item=get_component_entity(version_suffix=version_suffix))
        backend_app_dynamodb_table.put_item(Item=get_component_version_entity(version_suffix=version_suffix))

    return _create_component_version_entities


@pytest.fixture(autouse=True)
def mock_component_version(create_component_version_entities):
    create_component_version_entities()


@pytest.fixture(autouse=True)
def mock_moto_calls(
    mocked_list_components_response,
    mocked_create_component_response,
    mocked_delete_component_response,
):
    list_components = "ListComponents"
    create_component = "CreateComponent"
    delete_component = "DeleteComponent"

    invocations = {
        list_components: MagicMock(return_value=mocked_list_components_response),
        create_component: MagicMock(return_value=mocked_create_component_response),
        delete_component: MagicMock(return_value=mocked_delete_component_response),
    }

    def _interceptor(self, operation_name, kwarg):
        if operation_name in invocations:
            return invocations[operation_name](**kwarg)

        return orig(self, operation_name, kwarg)

    with patch("botocore.client.BaseClient._make_api_call", new=_interceptor):
        yield invocations


@pytest.fixture
def mocked_list_components_response():
    return {
        "componentVersionList": [
            {
                "arn": "arn:aws:imagebuilder:us-east-1:1234567890:component/test-component/1.0.0",
                "name": "test-component",
                "version": "1.0.0/1",
                "description": "Component description",
                "platform": "Linux",
                "supportedOsVersions": ["Ubuntu 24"],
                "type": "BUILD",
                "owner": "1234567890",
                "dateCreated": datetime(2023, 10, 17),
            },
        ]
    }


@pytest.fixture
def mocked_create_component_response():
    return {
        "requestId": "req-1234567890",
        "clientToken": "token-1234567890",
        "componentBuildVersionArn": "arn:aws:imagebuilder:us-east-1:1234567890:component/test-component/1.0.0",
    }


@pytest.fixture
def mocked_delete_component_response():
    return {
        "requestId": "req-1234567890",
        "componentBuildVersionArn": "arn:aws:imagebuilder:us-east-1:1234567890:component/test-component/1.0.0",
    }


def test_component_version_creation_started(
    generate_event,
    lambda_context,
    component_version_creation_started_event_payload,
    create_component_version_entities,
):
    # ARRANGE
    from app.packaging.entrypoints.domain_event_handler import handler

    create_component_version_entities(version_suffix="1234efgh")
    event_bridge_event = generate_event(
        detail_type="ComponentVersionCreationStarted",
        detail=component_version_creation_started_event_payload,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)


def test_component_version_update_started(
    generate_event,
    lambda_context,
    component_version_update_started_event_payload,
    create_component_version_entities,
):
    # ARRANGE
    from app.packaging.entrypoints.domain_event_handler import handler

    create_component_version_entities(version_suffix="1234efgh")
    create_component_version_entities(version_suffix="1234ijkl")
    event_bridge_event = generate_event(
        detail_type="ComponentVersionUpdateStarted",
        detail=component_version_update_started_event_payload,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)
