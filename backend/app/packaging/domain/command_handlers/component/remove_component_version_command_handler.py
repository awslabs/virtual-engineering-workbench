import logging
from datetime import datetime, timezone

from app.packaging.domain.commands.component import remove_component_version_command
from app.packaging.domain.exceptions.domain_exception import DomainException
from app.packaging.domain.model.component import component_version
from app.packaging.domain.ports import (
    component_version_definition_service,
    component_version_service,
)
from app.shared.adapters.unit_of_work_v2.unit_of_work import UnitOfWork


def handle(
    command: remove_component_version_command.RemoveComponentVersionCommand,
    uow: UnitOfWork,
    component_version_service: component_version_service.ComponentVersionService,
    component_version_definition_service: component_version_definition_service.ComponentVersionDefinitionService,
    logger: logging.Logger,
):
    logger.info(
        f"Retiring component version {command.componentVersionId.value} " f"of component {command.componentId.value}"
    )
    status = component_version.ComponentVersionStatus.Retired

    try:
        component_version_service.delete(component_build_version_arn=command.componentBuildVersionArn.value)

    except:
        status = component_version.ComponentVersionStatus.Failed

        raise DomainException(
            f"Version {command.componentVersionId.value} of component {command.componentId.value} can't be deleted."
        )
    finally:
        current_time = datetime.now(timezone.utc).isoformat()

        with uow:
            uow.get_repository(
                component_version.ComponentVersionPrimaryKey,
                component_version.ComponentVersion,
            ).update_attributes(
                component_version.ComponentVersionPrimaryKey(
                    componentId=command.componentId.value,
                    componentVersionId=command.componentVersionId.value,
                ),
                lastUpdateDate=current_time,
                status=status,
            )
            uow.commit()
