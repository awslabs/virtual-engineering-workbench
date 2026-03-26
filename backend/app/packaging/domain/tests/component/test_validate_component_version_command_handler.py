import logging
from unittest import mock

import pytest
from botocore.exceptions import ClientError
from freezegun import freeze_time

from app.packaging.domain.command_handlers.component import (
    validate_component_version_command_handler,
)
from app.packaging.domain.commands.component import validate_component_version_command
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component
from app.packaging.domain.ports import component_version_service
from app.packaging.domain.value_objects.component import component_id_value_object
from app.packaging.domain.value_objects.component_version import (
    component_version_yaml_definition_value_object,
)

PLACEHOLDER_VERSION = "1.0.0-rc.1"


@pytest.fixture()
def component_version_service_mock():
    return mock.create_autospec(spec=component_version_service.ComponentVersionService)


@pytest.fixture()
def validate_component_version_command_mock(
    get_test_component_yaml_definition,
) -> validate_component_version_command.ValidateComponentVersionCommand:
    return validate_component_version_command.ValidateComponentVersionCommand(
        componentId=component_id_value_object.from_str("comp-1234abcd"),
        componentVersionYamlDefinition=component_version_yaml_definition_value_object.from_str(
            get_test_component_yaml_definition()
        ),
    )


@freeze_time("2023-10-12")
def test_handle_should_validate_version(
    validate_component_version_command_mock,
    component_query_service_mock,
    component_version_service_mock,
    component_version_definition_service_mock,
    get_test_component_id,
):
    # ARRANGE
    current_time = "20231012.0000.000000"  # From freeze_time
    component_build_version_arn = (
        f"arn:aws:imagebuilder:us-east-1:123456789012:component/{get_test_component_id}/{current_time}/1"
    )
    component_yaml_definition_s3_prefix = f"validation/{get_test_component_id}/{current_time}"
    component_yaml_definition_s3_uri = (
        f"s3://test-bucket/{component_yaml_definition_s3_prefix}/{PLACEHOLDER_VERSION}/component.yaml"
    )
    component_entity = component.Component.parse_obj(
        {
            "componentId": get_test_component_id,
            "componentName": "test-component",
            "componentDescription": "Test description",
            "componentPlatform": "Linux",
            "componentSupportedArchitectures": ["amd64"],
            "componentSupportedOsVersions": ["Ubuntu 24"],
            "status": "CREATED",
            "createDate": "2023-11-02",
            "lastUpdateDate": "2023-11-02",
            "createdBy": "T0011AA",
            "lastUpdatedBy": "T0011BB",
        }
    )
    component_query_service_mock.get_component.return_value = component_entity
    component_version_service_mock.create.return_value = component_build_version_arn
    component_version_definition_service_mock.upload.return_value = component_yaml_definition_s3_uri

    # ACT
    validate_component_version_command_handler.handle(
        command=validate_component_version_command_mock,
        component_query_service=component_query_service_mock,
        component_version_definition_service=component_version_definition_service_mock,
        component_version_service=component_version_service_mock,
        logger=mock.create_autospec(spec=logging.Logger),
    )

    # ASSERT
    component_version_definition_service_mock.upload.assert_called_once_with(
        component_id=component_yaml_definition_s3_prefix,
        component_version=PLACEHOLDER_VERSION,
        component_definition=validate_component_version_command_mock.componentVersionYamlDefinition.value,
    )
    component_version_service_mock.create.assert_called_once_with(
        name=get_test_component_id,
        version=current_time,
        platform=component_entity.componentPlatform,
        supported_os_versions=component_entity.componentSupportedOsVersions,
        description=f"Version validation for component {get_test_component_id}",
        s3_component_uri=component_yaml_definition_s3_uri,
    )
    component_version_service_mock.delete.assert_called_once_with(component_build_version_arn)


def test_handle_should_raise_exception(
    validate_component_version_command_mock,
    component_query_service_mock,
    component_version_service_mock,
    component_version_definition_service_mock,
    get_test_component_id,
):
    # ARRANGE
    component_entity = component.Component.parse_obj(
        {
            "componentId": get_test_component_id,
            "componentName": "test-component",
            "componentDescription": "Test description",
            "componentPlatform": "Linux",
            "componentSupportedArchitectures": ["amd64"],
            "componentSupportedOsVersions": ["Ubuntu 24"],
            "status": "CREATED",
            "createDate": "2023-11-02",
            "lastUpdateDate": "2023-11-02",
            "createdBy": "T0011AA",
            "lastUpdatedBy": "T0011BB",
        }
    )
    component_query_service_mock.get_component.return_value = component_entity

    component_version_service_mock.get_build_arn.return_value = None
    error_message = {"Error": {"Code": "SomeErrorCode", "Message": "Some error occurred"}}
    component_version_service_mock.create.side_effect = ClientError(
        error_response=error_message,
        operation_name="CreateComponent",
    )

    # ACT && ASSERT
    with pytest.raises(domain_exception.DomainException) as exc_info:
        validate_component_version_command_handler.handle(
            command=validate_component_version_command_mock,
            component_query_service=component_query_service_mock,
            component_version_definition_service=component_version_definition_service_mock,
            component_version_service=component_version_service_mock,
            logger=mock.create_autospec(spec=logging.Logger),
        )
    assert str(exc_info.value) == (
        f"Version of component {validate_component_version_command_mock.componentId.value} failed to validate."
    )
    assert exc_info.value.__cause__ is not None
    assert isinstance(exc_info.value.__cause__, ClientError)
