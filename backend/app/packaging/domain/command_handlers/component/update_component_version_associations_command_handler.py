import logging
from datetime import datetime, timezone

from app.packaging.domain.commands.component import update_component_version_associations_command
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component_version
from app.packaging.domain.model.shared import component_version_entry
from app.packaging.domain.ports import component_version_query_service
from app.shared.adapters.unit_of_work_v2 import unit_of_work


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

    for component_version_dependency in command.componentsVersionDependencies.value:
        component_version_dependency_entity = __get_component_version(
            component_version_qry_srv=component_version_qry_srv,
            component_id=component_version_dependency.componentId,
            component_version_id=component_version_dependency.componentVersionId,
            logger=logger,
        )

        __validate_component_version_status(
            component_version_entity=component_version_dependency_entity,
            logger=logger,
        )

        associated_component_version_entity = component_version_entry.ComponentVersionEntry(
            componentId=component_version_entity.componentId,
            componentName=component_version_entity.componentName,
            componentVersionId=component_version_entity.componentVersionId,
            componentVersionName=component_version_entity.componentVersionName,
        )
        # Remove any previous component version with the same componentId and componentVersionId
        associated_components_versions_list = (
            [
                associated_component_version
                for associated_component_version in component_version_dependency_entity.associatedComponentsVersions
                if component_version_entity.componentId != associated_component_version.componentId
                and component_version_entity.componentVersionId != associated_component_version.componentVersionId
            ]
            if component_version_dependency_entity.associatedComponentsVersions
            else list()
        )

        # Add the updated component version
        associated_components_versions_list.append(associated_component_version_entity)

        component_version_dependency_entity.associatedComponentsVersions = associated_components_versions_list
        component_version_dependency_entity.lastUpdateDate = datetime.now(timezone.utc).isoformat()

        with uow:
            uow.get_repository(
                component_version.ComponentVersionPrimaryKey, component_version.ComponentVersion
            ).update_entity(
                component_version.ComponentVersionPrimaryKey(
                    componentId=component_version_dependency_entity.componentId,
                    componentVersionId=component_version_dependency_entity.componentVersionId,
                ),
                component_version_dependency_entity,
            )
            uow.commit()

    if command.previousComponentsVersionDependencies:
        for previous_component_version_dependency in command.previousComponentsVersionDependencies.value:
            if not any(
                component_version_dependency
                for component_version_dependency in command.componentsVersionDependencies.value
                if previous_component_version_dependency.componentId == component_version_dependency.componentId
                and previous_component_version_dependency.componentVersionId
                == component_version_dependency.componentVersionId
            ):
                previous_component_version_dependency_entity = __get_component_version(
                    component_version_qry_srv=component_version_qry_srv,
                    component_id=previous_component_version_dependency.componentId,
                    component_version_id=previous_component_version_dependency.componentVersionId,
                    logger=logger,
                )

                __validate_component_version_status(
                    component_version_entity=previous_component_version_dependency_entity,
                    logger=logger,
                )

                # Remove the component version because it is no longer a dependency
                associated_components_versions_list = [
                    associated_component_version
                    for associated_component_version in previous_component_version_dependency_entity.associatedComponentsVersions
                    if component_version_entity.componentId != associated_component_version.componentId
                    and component_version_entity.componentVersionId != associated_component_version.componentVersionId
                ]

                previous_component_version_dependency_entity.associatedComponentsVersions = (
                    associated_components_versions_list
                )
                previous_component_version_dependency_entity.lastUpdateDate = datetime.now(timezone.utc).isoformat()

                with uow:
                    uow.get_repository(
                        component_version.ComponentVersionPrimaryKey, component_version.ComponentVersion
                    ).update_entity(
                        component_version.ComponentVersionPrimaryKey(
                            componentId=previous_component_version_dependency_entity.componentId,
                            componentVersionId=previous_component_version_dependency_entity.componentVersionId,
                        ),
                        previous_component_version_dependency_entity,
                    )
                    uow.commit()
