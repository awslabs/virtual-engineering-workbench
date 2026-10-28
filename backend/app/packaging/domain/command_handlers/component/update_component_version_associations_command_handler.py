import logging
import random
import time
from datetime import datetime, timezone
from typing import Callable

from app.packaging.domain.commands.component import update_component_version_associations_command
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component_version
from app.packaging.domain.model.shared import component_version_entry
from app.packaging.domain.ports import component_version_query_service
from app.shared.adapters.unit_of_work_v2 import repository_exception, unit_of_work

# Attempts of one optimistic association write, with a jittered exponential backoff between them.
WRITE_ATTEMPTS = 8
WRITE_BACKOFF_SECONDS = 0.1


def __get_component_version(
    component_id: str,
    component_version_id: str,
    component_version_qry_srv: component_version_query_service.ComponentVersionQueryService,
    logger: logging.Logger,
) -> component_version.ComponentVersion:
    component_version_entity = component_version_qry_srv.get_component_version(
        component_id=component_id,
        version_id=component_version_id,
    )
    if component_version_entity is None:
        exception_message = f"Version {component_version_id} for {component_id} can not be found."

        logger.exception(exception_message)

        raise domain_exception.DomainException(exception_message)

    return component_version_entity


def __validate_component_version_status(
    component_version_entity: component_version.ComponentVersion,
    logger: logging.Logger,
) -> bool:
    valid_status = [
        component_version.ComponentVersionStatus.Created.value,
        component_version.ComponentVersionStatus.Released.value,
        component_version.ComponentVersionStatus.Retired.value,
        component_version.ComponentVersionStatus.Validated.value,
    ]
    if component_version_entity.status not in valid_status:
        exception_message = (
            f"Version {component_version_entity.componentVersionName} of "
            f"component {component_version_entity.componentId} "
            f"can't be (dis-)associated while in {component_version_entity.status} status: "
            f"only {component_version.ComponentVersionStatus.Created}, "
            f"{component_version.ComponentVersionStatus.Released}, "
            f"{component_version.ComponentVersionStatus.Retired}, and "
            f"{component_version.ComponentVersionStatus.Validated} states are accepted."
        )

        logger.exception(exception_message)

        raise domain_exception.DomainException(exception_message)

    return True


def __update_associations(
    component_id: str,
    component_version_id: str,
    change: Callable[
        [list[component_version_entry.ComponentVersionEntry]], list[component_version_entry.ComponentVersionEntry]
    ],
    component_version_qry_srv: component_version_query_service.ComponentVersionQueryService,
    logger: logging.Logger,
    uow: unit_of_work.UnitOfWork,
) -> None:
    """Applies `change` to a component version's associatedComponentsVersions without losing a parallel change.

    Every (dis)association rewrites the whole list. Parallel ones on the same component version - a
    base component whose dependents are retired together - each read the list, change their own entry
    and write it back, so the last write dropped the others' changes and left stale entries that block
    the retirement of the base. The write is conditional on the lastUpdateDate that was read, and a
    write that lost the race reads again and retries.
    """
    for attempt in range(1, WRITE_ATTEMPTS + 1):
        entity = __get_component_version(
            component_version_qry_srv=component_version_qry_srv,
            component_id=component_id,
            component_version_id=component_version_id,
            logger=logger,
        )
        __validate_component_version_status(component_version_entity=entity, logger=logger)

        read_last_update_date = entity.lastUpdateDate
        entity.associatedComponentsVersions = change(list(entity.associatedComponentsVersions or []))
        entity.lastUpdateDate = datetime.now(timezone.utc).isoformat()

        try:
            with uow:
                uow.get_repository(
                    component_version.ComponentVersionPrimaryKey, component_version.ComponentVersion
                ).update_entity(
                    component_version.ComponentVersionPrimaryKey(
                        componentId=entity.componentId,
                        componentVersionId=entity.componentVersionId,
                    ),
                    entity,
                    expected={"lastUpdateDate": read_last_update_date},
                )
                uow.commit()
            return
        except repository_exception.ConditionalCheckFailedException:
            if attempt == WRITE_ATTEMPTS:
                raise
            logger.info(
                f"Version {component_version_id} of component {component_id} changed concurrently, "
                f"retrying its associations (attempt {attempt} of {WRITE_ATTEMPTS})."
            )
            time.sleep(random.uniform(0, WRITE_BACKOFF_SECONDS * 2**attempt))


def __without(
    associated: list[component_version_entry.ComponentVersionEntry],
    entity: component_version.ComponentVersion,
) -> list[component_version_entry.ComponentVersionEntry]:
    """The associations without the entry of this component version (same component and version id)."""
    return [
        associated_component_version
        for associated_component_version in associated
        if not (
            associated_component_version.componentId == entity.componentId
            and associated_component_version.componentVersionId == entity.componentVersionId
        )
    ]


def handle(
    command: update_component_version_associations_command.UpdateComponentVersionAssociationsCommand,
    component_version_qry_srv: component_version_query_service.ComponentVersionQueryService,
    logger: logging.Logger,
    uow: unit_of_work.UnitOfWork,
):
    component_version_entity = __get_component_version(
        component_version_qry_srv=component_version_qry_srv,
        component_id=command.componentId.value,
        component_version_id=command.componentVersionId.value,
        logger=logger,
    )

    __validate_component_version_status(component_version_entity=component_version_entity, logger=logger)

    associated_component_version_entity = component_version_entry.ComponentVersionEntry(
        componentId=component_version_entity.componentId,
        componentName=component_version_entity.componentName,
        componentVersionId=component_version_entity.componentVersionId,
        componentVersionName=component_version_entity.componentVersionName,
    )

    for component_version_dependency in command.componentsVersionDependencies.value:
        # Replace any previous entry of this component version (e.g. its release candidate name)
        __update_associations(
            component_id=component_version_dependency.componentId,
            component_version_id=component_version_dependency.componentVersionId,
            change=lambda associated: __without(associated, component_version_entity)
            + [associated_component_version_entity],
            component_version_qry_srv=component_version_qry_srv,
            logger=logger,
            uow=uow,
        )

    if command.previousComponentsVersionDependencies:
        for previous_component_version_dependency in command.previousComponentsVersionDependencies.value:
            if not any(
                component_version_dependency
                for component_version_dependency in command.componentsVersionDependencies.value
                if previous_component_version_dependency.componentId == component_version_dependency.componentId
                and previous_component_version_dependency.componentVersionId
                == component_version_dependency.componentVersionId
            ):
                # Remove the component version because it is no longer a dependency
                __update_associations(
                    component_id=previous_component_version_dependency.componentId,
                    component_version_id=previous_component_version_dependency.componentVersionId,
                    change=lambda associated: __without(associated, component_version_entity),
                    component_version_qry_srv=component_version_qry_srv,
                    logger=logger,
                    uow=uow,
                )
