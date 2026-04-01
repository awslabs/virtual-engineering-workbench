import logging
from unittest import mock

import assertpy
import pytest
import semver
from freezegun import freeze_time

from app.packaging.domain.command_handlers.component import (
    deploy_component_version_command_handler,
)
from app.packaging.domain.commands.component import deploy_component_version_command
from app.packaging.domain.events.component import component_version_published
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component, component_version
from app.packaging.domain.ports import component_version_service
from app.packaging.domain.value_objects.component import component_id_value_object
from app.packaging.domain.value_objects.component_version import (
    component_version_description_value_object,
    component_version_id_value_object,
    component_version_name_value_object,
    component_version_yaml_definition_value_object,
)
from app.packaging.domain.value_objects.shared import user_id_value_object
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work


@pytest.fixture()
def component_version_service_mock():
    return mock.create_autospec(spec=component_version_service.ComponentVersionService)


@pytest.fixture()
def deploy_component_version_command_mock(
    get_test_component_yaml_definition,
) -> deploy_component_version_command.DeployComponentVersionCommand:
    return deploy_component_version_command.DeployComponentVersionCommand(
        componentId=component_id_value_object.from_str("comp-1234abcd"),
        componentVersionId=component_version_id_value_object.from_str("vers-11111111"),
        componentVersionName=component_version_name_value_object.from_str("1.0.0"),
        componentVersionDescription=component_version_description_value_object.from_str("Test description"),
        componentVersionYamlDefinition=component_version_yaml_definition_value_object.from_str(
            get_test_component_yaml_definition()
        ),
        lastUpdatedBy=user_id_value_object.from_str("T123456"),
    )


@pytest.mark.parametrize(
    "component_downstream_version",
    (
        ("2.1.0-rc.1"),
        ("2.1.0"),
    ),
)
@freeze_time("2023-10-12")
def test_handle_should_deploy_version(
    component_downstream_version,
    deploy_component_version_command_mock,
    component_query_service_mock,
    component_version_service_mock,
    component_version_definition_service_mock,
    get_test_component_id,
):
    # ARRANGE
    component_upstream_version = semver.Version.parse(component_downstream_version).finalize_version()
    component_build_version_arn = (
        f"arn:aws:imagebuilder:us-east-1:123456789012:component/{get_test_component_id}/{component_upstream_version}/1"
    )
    component_yaml_definition_s3_prefix = f"{get_test_component_id}/{component_upstream_version}/component.yaml"
    component_yaml_definition_s3_uri = f"s3://test-bucket/{component_yaml_definition_s3_prefix}"
    component_entity = component.Component.model_validate(
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

    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {component_version.ComponentVersion: component_version_repo_mock}
    component_query_service_mock.get_component.return_value = component_entity

    component_version_service_mock.get_build_arn.return_value = None
    component_version_service_mock.create.return_value = component_build_version_arn
    component_version_definition_service_mock.upload.return_value = component_yaml_definition_s3_uri

    # Overriding version name in command mock so that the version parsing can be easily tested
    deploy_component_version_command_mock.componentVersionName = component_version_name_value_object.from_str(
        component_downstream_version
    )

    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)

    # ACT
    deploy_component_version_command_handler.handle(
        command=deploy_component_version_command_mock,
        uow=uow_mock,
        message_bus=message_bus_mock,
        component_query_service=component_query_service_mock,
        component_version_service=component_version_service_mock,
        component_version_definition_service=component_version_definition_service_mock,
        logger=mock.create_autospec(spec=logging.Logger),
    )

    # ASSERT
    component_version_service_mock.get_build_arn.assert_called_once_with(
        get_test_component_id,
        component_upstream_version,
    )
    component_version_service_mock.delete.assert_not_called()
    component_version_definition_service_mock.upload.assert_called_once_with(
        component_id=get_test_component_id,
        component_version=component_downstream_version,
        component_definition=deploy_component_version_command_mock.componentVersionYamlDefinition.value,
    )
    component_version_service_mock.create.assert_called_once_with(
        get_test_component_id,
        component_upstream_version,
        component_yaml_definition_s3_uri,
        component_entity.componentPlatform,
        component_entity.componentSupportedOsVersions,
        deploy_component_version_command_mock.componentVersionDescription.value,
    )
    component_version_repo_mock.update_attributes.assert_called_once_with(
        component_version.ComponentVersionPrimaryKey(
            componentId=deploy_component_version_command_mock.componentId.value,
            componentVersionId=deploy_component_version_command_mock.componentVersionId.value,
        ),
        componentBuildVersionArn=component_build_version_arn,
        status=component_version.ComponentVersionStatus.Created,
        componentVersionS3Uri=component_yaml_definition_s3_uri,
    )
    uow_mock.commit.assert_called()
    message_bus_mock.publish.assert_called_once_with(
        component_version_published.ComponentVersionPublished(
            component_id=deploy_component_version_command_mock.componentId.value,
            component_version_id=deploy_component_version_command_mock.componentVersionId.value,
        )
    )


@freeze_time("2023-10-12")
def test_handle_should_raise_if_component_is_none(
    deploy_component_version_command_mock,
    component_query_service_mock,
    component_version_service_mock,
    component_version_definition_service_mock,
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {component_version.ComponentVersion: component_version_repo_mock}
    component_query_service_mock.get_component.return_value = None
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        deploy_component_version_command_handler.handle(
            command=deploy_component_version_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_query_service=component_query_service_mock,
            component_version_service=component_version_service_mock,
            component_version_definition_service=component_version_definition_service_mock,
            logger=mock.create_autospec(spec=logging.Logger),
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        f"Component {deploy_component_version_command_mock.componentId.value} can not be found."
    )

    component_version_repo_mock.update_attributes.assert_called_once_with(
        component_version.ComponentVersionPrimaryKey(
            componentId=deploy_component_version_command_mock.componentId.value,
            componentVersionId=deploy_component_version_command_mock.componentVersionId.value,
        ),
        status=component_version.ComponentVersionStatus.Failed,
    )


@pytest.mark.parametrize(
    "component_downstream_version",
    (("2.1.0"),),
)
@freeze_time("2023-10-12")
def test_handle_should_raise_if_deploying_existing_non_rc_version(
    component_downstream_version,
    deploy_component_version_command_mock,
    component_query_service_mock,
    component_version_service_mock,
    component_version_definition_service_mock,
    get_test_component_id,
):
    # ARRANGE
    component_upstream_version = semver.Version.parse(component_downstream_version).finalize_version()
    component_build_version_arn = (
        f"arn:aws:imagebuilder:us-east-1:123456789012:component/{get_test_component_id}/{component_upstream_version}/1"
    )
    component_yaml_definition_s3_prefix = f"{get_test_component_id}/{component_upstream_version}/component.yaml"
    component_yaml_definition_s3_uri = f"s3://test-bucket/{component_yaml_definition_s3_prefix}"
    component_entity = component.Component.model_validate(
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

    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {component_version.ComponentVersion: component_version_repo_mock}
    component_query_service_mock.get_component.return_value = component_entity

    component_version_service_mock.get_build_arn.return_value = component_build_version_arn
    component_version_service_mock.create.return_value = component_build_version_arn
    component_version_definition_service_mock.upload.return_value = component_yaml_definition_s3_uri

    # Overriding version name in command mock so that the version parsing can be easily tested
    deploy_component_version_command_mock.componentVersionName = component_version_name_value_object.from_str(
        component_downstream_version
    )

    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        deploy_component_version_command_handler.handle(
            command=deploy_component_version_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_query_service=component_query_service_mock,
            component_version_service=component_version_service_mock,
            component_version_definition_service=component_version_definition_service_mock,
            logger=mock.create_autospec(spec=logging.Logger),
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        f"Version {component_upstream_version} of {get_test_component_id} already exists."
    )

    component_version_service_mock.get_build_arn.assert_called_once_with(
        get_test_component_id,
        component_upstream_version,
    )


@pytest.mark.parametrize(
    "component_downstream_version",
    (("2.1.0-rc.1"),),
)
@freeze_time("2023-10-12")
def test_handle_should_update_rc_version(
    component_downstream_version,
    deploy_component_version_command_mock,
    component_query_service_mock,
    component_version_service_mock,
    component_version_definition_service_mock,
    get_test_component_id,
):
    # ARRANGE
    component_upstream_version = semver.Version.parse(component_downstream_version).finalize_version()
    component_build_version_arn = (
        f"arn:aws:imagebuilder:us-east-1:123456789012:component/{get_test_component_id}/{component_upstream_version}/1"
    )
    component_yaml_definition_s3_prefix = f"{get_test_component_id}/{component_upstream_version}/component.yaml"
    component_yaml_definition_s3_uri = f"s3://test-bucket/{component_yaml_definition_s3_prefix}"
    component_entity = component.Component.model_validate(
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

    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {component_version.ComponentVersion: component_version_repo_mock}
    component_query_service_mock.get_component.return_value = component_entity

    component_version_service_mock.get_build_arn.return_value = component_build_version_arn
    component_version_service_mock.create.return_value = component_build_version_arn
    component_version_definition_service_mock.upload.return_value = component_yaml_definition_s3_uri

    # Overriding version name in command mock so that the version parsing can be easily tested
    deploy_component_version_command_mock.componentVersionName = component_version_name_value_object.from_str(
        component_downstream_version
    )

    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)

    # ACT
    deploy_component_version_command_handler.handle(
        command=deploy_component_version_command_mock,
        uow=uow_mock,
        message_bus=message_bus_mock,
        component_query_service=component_query_service_mock,
        component_version_service=component_version_service_mock,
        component_version_definition_service=component_version_definition_service_mock,
        logger=mock.create_autospec(spec=logging.Logger),
    )

    # ASSERT
    component_version_service_mock.get_build_arn.assert_called_once_with(
        get_test_component_id,
        component_upstream_version,
    )
    component_version_service_mock.delete.assert_called_once_with(component_build_version_arn)
    component_version_definition_service_mock.upload.assert_called_once_with(
        component_id=get_test_component_id,
        component_version=component_downstream_version,
        component_definition=deploy_component_version_command_mock.componentVersionYamlDefinition.value,
    )
    component_version_service_mock.create.assert_called_once_with(
        get_test_component_id,
        component_upstream_version,
        component_yaml_definition_s3_uri,
        component_entity.componentPlatform,
        component_entity.componentSupportedOsVersions,
        deploy_component_version_command_mock.componentVersionDescription.value,
    )
    component_version_repo_mock.update_attributes.assert_called_once_with(
        component_version.ComponentVersionPrimaryKey(
            componentId=deploy_component_version_command_mock.componentId.value,
            componentVersionId=deploy_component_version_command_mock.componentVersionId.value,
        ),
        componentBuildVersionArn=component_build_version_arn,
        status=component_version.ComponentVersionStatus.Created,
        componentVersionS3Uri=component_yaml_definition_s3_uri,
    )
    uow_mock.commit.assert_called()
    message_bus_mock.publish.assert_called_once_with(
        component_version_published.ComponentVersionPublished(
            component_id=deploy_component_version_command_mock.componentId.value,
            component_version_id=deploy_component_version_command_mock.componentVersionId.value,
        )
    )
