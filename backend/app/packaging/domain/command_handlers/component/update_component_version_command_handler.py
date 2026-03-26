from datetime import datetime, timezone

import semver

from app.packaging.domain.commands.component import update_component_version_command
from app.packaging.domain.events.component import component_version_update_started
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component_version
from app.packaging.domain.model.shared.component_version_entry import ComponentVersionEntry
from app.packaging.domain.ports import component_version_query_service
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def __fetch_and_validate_dependencies(
    component_version_qry_srv: component_version_query_service.ComponentVersionQueryService,
    dependencies: list[ComponentVersionEntry],
    acceptable_states_for_update: list[component_version.ComponentVersionStatus],
):
    for dependency in dependencies:
        component_entity = component_version_qry_srv.get_component_version(
            dependency.componentId, dependency.componentVersionId
        )

        if component_entity is None:
            raise domain_exception.DomainException(
                f"Version {dependency.componentVersionId} of component {dependency.componentId} does not exist."
            )

        if component_entity.status not in acceptable_states_for_update:
            raise domain_exception.DomainException(
                f"Version {dependency.componentVersionId} of component {dependency.componentId} is not in a valid status: {component_entity.status}."
            )


def __update_downstream_dependencies(
    update_component_version_name: str,
    component_version_entity: component_version.ComponentVersion,
    component_version_qry_srv: component_version_query_service.ComponentVersionQueryService,
    uow: unit_of_work.UnitOfWork,
):
    if component_version_entity.associatedComponentsVersions is not None:
        for associated_component_version in component_version_entity.associatedComponentsVersions:
            associated_component_version_entity = component_version_qry_srv.get_component_version(
                associated_component_version.componentId, associated_component_version.componentVersionId
            )

            if associated_component_version_entity is None:
                raise domain_exception.DomainException(
                    f"Version {associated_component_version.componentVersionId} of component "
                    f"{associated_component_version.componentId} does not exist."
                )

            for dependency in associated_component_version_entity.componentVersionDependencies:
                if dependency.componentVersionId == component_version_entity.componentVersionId:
                    dependency.componentVersionName = update_component_version_name

            with uow:
                uow.get_repository(
                    component_version.ComponentVersionPrimaryKey, component_version.ComponentVersion
                ).update_entity(
                    component_version.ComponentVersionPrimaryKey(
                        componentId=associated_component_version.componentId,
                        componentVersionId=associated_component_version.componentVersionId,
                    ),
                    associated_component_version_entity,
                )
                uow.commit()


def handle(
    command: update_component_version_command.UpdateComponentVersionCommand,
    uow: unit_of_work.UnitOfWork,
    message_bus: message_bus.MessageBus,
    component_version_qry_srv: component_version_query_service.ComponentVersionQueryService,
):
    component_version_entity = component_version_qry_srv.get_component_version(
        command.componentId.value, command.componentVersionId.value
    )

    if component_version_entity is None:
        raise domain_exception.DomainException(
            f"Version {command.componentVersionId.value} of component {command.componentId.value} does not exist."
        )

    acceptable_states_for_update = [
        component_version.ComponentVersionStatus.Failed,
        component_version.ComponentVersionStatus.Validated,
    ]
    acceptable_states_for_dependent_components = [
        component_version.ComponentVersionStatus.Released,
        component_version.ComponentVersionStatus.Validated,
    ]
    component_version_name = component_version_entity.componentVersionName
    previous_component_version_dependencies = (
        component_version_entity.componentVersionDependencies
        if component_version_entity.componentVersionDependencies
        else list()
    )

    if component_version_entity.status not in acceptable_states_for_update:
        raise domain_exception.DomainException(
            f"Version {component_version_name} of component {command.componentId.value} can't be updated while in {component_version_entity.status} status."
        )

    dependencies = sorted(command.componentVersionDependencies.value, key=lambda x: x.order)

    for dependency in dependencies:
        if dependency.componentId == command.componentId.value:
            raise domain_exception.DomainException(
                f"Component {command.componentId.value} cannot be a dependency of itself."
            )

    __fetch_and_validate_dependencies(
        component_version_qry_srv, dependencies, acceptable_states_for_dependent_components
    )

    try:
        component_version_parsed = semver.Version.parse(component_version_name)
    except:
        raise domain_exception.DomainException(f"Version {component_version_name} is not a valid SemVer string.")
    if component_version_parsed.prerelease is None:
        raise domain_exception.DomainException(
            f"Can not update an already released component version ({component_version_name}) - only release candidates are allowed."
        )

    update_component_version_name = str(component_version_parsed.bump_prerelease())
    current_time = datetime.now(timezone.utc).isoformat()
    with uow:
        component_version_entity.lastUpdatedBy = command.lastUpdatedBy.value
        component_version_entity.lastUpdateDate = current_time
        component_version_entity.componentVersionDependencies = dependencies
        component_version_entity.componentVersionName = update_component_version_name
        component_version_entity.componentVersionDescription = command.componentVersionDescription.value
        component_version_entity.softwareVendor = command.softwareVendor.value
        component_version_entity.softwareVersion = command.softwareVersion.value
        component_version_entity.licenseDashboard = command.licenseDashboard.value if command.licenseDashboard else None
        component_version_entity.notes = command.notes.value if command.notes else None
        component_version_entity.status = component_version.ComponentVersionStatus.Updating
        uow.get_repository(
            component_version.ComponentVersionPrimaryKey, component_version.ComponentVersion
        ).update_entity(
            component_version.ComponentVersionPrimaryKey(
                componentId=command.componentId.value,
                componentVersionId=command.componentVersionId.value,
            ),
            component_version_entity,
        )
        uow.commit()
    __update_downstream_dependencies(
        update_component_version_name=update_component_version_name,
        component_version_entity=component_version_entity,
        component_version_qry_srv=component_version_qry_srv,
        uow=uow,
    )
    message_bus.publish(
        component_version_update_started.ComponentVersionUpdateStarted(
            component_id=command.componentId.value,
            component_version_id=command.componentVersionId.value,
            component_version_description=command.componentVersionDescription.value,
            component_version_name=update_component_version_name,
            component_version_dependencies=dependencies,
            component_version_yaml_definition=command.componentVersionYamlDefinition.value,
            previousComponentVersionDependencies=previous_component_version_dependencies,
        )
    )
