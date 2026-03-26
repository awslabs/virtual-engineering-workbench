import logging

import semver

from app.packaging.domain.commands.component import deploy_component_version_command
from app.packaging.domain.events.component import component_version_published
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component_version
from app.packaging.domain.ports import (
    component_query_service,
    component_version_definition_service,
    component_version_service,
)
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def _update_attributes(
    command: deploy_component_version_command.DeployComponentVersionCommand,
    uow: unit_of_work.UnitOfWork,
    status: component_version.ComponentVersionStatus,
    component_version_build_arn: str | None = None,
    component_yaml_definition_s3_uri: str | None = None,
):
    with uow:
        kwargs = {
            "status": status,
        }
        if component_version_build_arn:
            kwargs["componentBuildVersionArn"] = component_version_build_arn
        if component_yaml_definition_s3_uri:
            kwargs["componentVersionS3Uri"] = component_yaml_definition_s3_uri
        uow.get_repository(
            component_version.ComponentVersionPrimaryKey,
            component_version.ComponentVersion,
        ).update_attributes(
            component_version.ComponentVersionPrimaryKey(
                componentId=command.componentId.value,
                componentVersionId=command.componentVersionId.value,
            ),
            **kwargs,
        )
        uow.commit()


def _handle_existing_version(
    component_version_service: component_version_service.ComponentVersionService,
    component_id: str,
    component_version_name_upstream: str,
    component_version_name_parsed: semver.Version,
    component_version_name: str,
) -> None:
    component_version_build_arn = component_version_service.get_build_arn(component_id, component_version_name_upstream)
    if component_version_build_arn:
        if component_version_name_parsed.prerelease:
            component_version_service.delete(component_version_build_arn)
        else:
            raise domain_exception.DomainException(
                f"Version {component_version_name} of {component_id} already exists."
            )


def handle(
    command: deploy_component_version_command.DeployComponentVersionCommand,
    uow: unit_of_work.UnitOfWork,
    message_bus: message_bus.MessageBus,
    component_version_service: component_version_service.ComponentVersionService,
    component_version_definition_service: component_version_definition_service.ComponentVersionDefinitionService,
    component_query_service: component_query_service.ComponentQueryService,
    logger: logging.Logger,
):
    try:
        component = component_query_service.get_component(command.componentId.value)
        if component is None:
            raise domain_exception.DomainException(f"Component {command.componentId.value} can not be found.")
        component_version_name = command.componentVersionName.value
        component_version_name_parsed = semver.Version.parse(component_version_name)
        component_version_name_upstream = str(component_version_name_parsed.finalize_version())

        _handle_existing_version(
            component_version_service,
            command.componentId.value,
            component_version_name_upstream,
            component_version_name_parsed,
            component_version_name,
        )

        # Upload the YAML definition to S3
        component_s3_uri = component_version_definition_service.upload(
            component_id=command.componentId.value,
            component_version=component_version_name,
            component_definition=command.componentVersionYamlDefinition.value,
        )

        # Create component version in EC2 Image Builder
        component_version_build_arn = component_version_service.create(
            command.componentId.value,
            component_version_name_upstream,
            component_s3_uri,
            component.componentPlatform,
            component.componentSupportedOsVersions,
            command.componentVersionDescription.value,
        )

        _update_attributes(
            command=command,
            uow=uow,
            status=component_version.ComponentVersionStatus.Created,
            component_version_build_arn=component_version_build_arn,
            component_yaml_definition_s3_uri=component_s3_uri,
        )

        message_bus.publish(
            component_version_published.ComponentVersionPublished(
                component_id=command.componentId.value,
                component_version_id=command.componentVersionId.value,
            )
        )
    except domain_exception.DomainException:
        logger.exception(
            f"Component version {command.componentVersionId.value} of {command.componentId.value} failed to create."
        )
        _update_attributes(command, uow, component_version.ComponentVersionStatus.Failed)
        raise
    except Exception as e:
        error_msg = (
            f"Component version {command.componentVersionId.value} of {command.componentId.value} failed to create."
        )
        logger.exception(error_msg)
        _update_attributes(command, uow, component_version.ComponentVersionStatus.Failed)
        raise domain_exception.DomainException(error_msg) from e
