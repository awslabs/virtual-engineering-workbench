import logging
from datetime import datetime, timezone

from app.packaging.domain.commands.component import validate_component_version_command
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.ports import (
    component_query_service,
    component_version_definition_service,
    component_version_service,
)

PLACEHOLDER_VERSION = "1.0.0-rc.1"


def handle(
    command: validate_component_version_command.ValidateComponentVersionCommand,
    component_version_service: component_version_service.ComponentVersionService,
    component_version_definition_service: component_version_definition_service.ComponentVersionDefinitionService,
    component_query_service: component_query_service.ComponentQueryService,
    logger: logging.Logger,
):
    try:
        component = component_query_service.get_component(command.componentId.value)
        if component is None:
            raise domain_exception.DomainException(f"Component {command.componentId.value} can not be found.")

        current_time = datetime.now(timezone.utc).strftime("%Y%m%d.%H%M.%f")
        # Upload the YAML definition to S3
        component_s3_uri = component_version_definition_service.upload(
            # Add validation to the prefix to expire objects automatically
            component_id=f"validation/{command.componentId.value}/{current_time}",
            # Use a placeholder version for backward compatibility
            component_version=PLACEHOLDER_VERSION,
            component_definition=command.componentVersionYamlDefinition.value,
        )
        # Create component version in EC2 Image Builder
        component_version_build_arn = component_version_service.create(
            name=command.componentId.value,
            # Avoid conflicts with existing components versions
            version=current_time,
            s3_component_uri=component_s3_uri,
            platform=component.componentPlatform,
            supported_os_versions=component.componentSupportedOsVersions,
            description=f"Version validation for component {command.componentId.value}",
        )

        # Delete component version in EC2 Image Builder
        component_version_service.delete(component_version_build_arn)
    except domain_exception.DomainException:
        logger.exception(f"Version of component {command.componentId.value} failed to validate.")
        raise
    except Exception as e:
        error_msg = f"Version of component {command.componentId.value} failed to validate."

        logger.exception(error_msg)
        raise domain_exception.DomainException(error_msg) from e
