from datetime import datetime, timezone

import semver

from app.packaging.domain.commands.component import create_component_version_command
from app.packaging.domain.events.component import component_version_creation_started
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component, component_version
from app.packaging.domain.ports import component_query_service, component_version_query_service
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work

INITIAL_VERSION = "1.0.0-rc.1"


def _calculate_new_version_name(
    component_version_qry_srv: component_version_query_service.ComponentVersionQueryService,
    command: create_component_version_command.CreateComponentVersionCommand,
):
    new_component_version_name = INITIAL_VERSION
    latest_component_version_name = component_version_qry_srv.get_latest_component_version_name(
        command.componentId.value
    )
    if latest_component_version_name:
        try:
            latest_component_version_parsed = semver.Version.parse(latest_component_version_name)
        except:
            raise domain_exception.DomainException(
                f"Version {latest_component_version_name} is not a valid SemVer string."
            )

        if command.componentVersionReleaseType.value == component_version.ComponentVersionReleaseType.Major:
            new_component_version_name = str(latest_component_version_parsed.bump_major().bump_prerelease())
        elif command.componentVersionReleaseType.value == component_version.ComponentVersionReleaseType.Minor:
            new_component_version_name = str(latest_component_version_parsed.bump_minor().bump_prerelease())
        elif command.componentVersionReleaseType.value == component_version.ComponentVersionReleaseType.Patch:
            new_component_version_name = str(latest_component_version_parsed.bump_patch().bump_prerelease())

    return new_component_version_name


def handle(
    command: create_component_version_command.CreateComponentVersionCommand,
    uow: unit_of_work.UnitOfWork,
    message_bus: message_bus.MessageBus,
    component_qry_srv: component_query_service.ComponentQueryService,
    component_version_qry_srv: component_version_query_service.ComponentVersionQueryService,
):
    new_component_version_name = _calculate_new_version_name(component_version_qry_srv, command)

    component_entity = component_qry_srv.get_component(command.componentId.value)

    if component_entity is None:
        raise domain_exception.DomainException(f"Component {command.componentId.value} can not be found.")
    if component_entity.status is component.ComponentStatus.Archived:
        raise domain_exception.DomainException(
            f"Component {command.componentId.value} is in {component.ComponentStatus.Archived} status."
        )

    if command.componentVersionDependencies.value:
        valid_component_status = [
            component_version.ComponentVersionStatus.Validated.value,
            component_version.ComponentVersionStatus.Released.value,
        ]
        for dependency_component in command.componentVersionDependencies.value:
            dependency_component_version_entity: component_version.ComponentVersion = (
                component_version_qry_srv.get_component_version(
                    component_id=dependency_component.componentId,
                    version_id=dependency_component.componentVersionId,
                )
            )
            if not dependency_component_version_entity:
                raise domain_exception.DomainException(
                    f"Component {dependency_component.componentId}/{dependency_component.componentName} not found."
                )
            if dependency_component_version_entity.status not in valid_component_status:
                raise domain_exception.DomainException(
                    f"Component {dependency_component.componentId}/{dependency_component.componentName} not in a"
                    f" valid status: {dependency_component_version_entity.status}."
                )

    current_time = datetime.now(timezone.utc).isoformat()
    component_version_entity = component_version.ComponentVersion(
        componentId=command.componentId.value,
        componentVersionName=new_component_version_name,
        componentName=component_entity.componentName,
        componentVersionDescription=command.componentVersionDescription.value,
        componentSupportedArchitectures=component_entity.componentSupportedArchitectures,
        componentSupportedOsVersions=component_entity.componentSupportedOsVersions,
        componentPlatform=component_entity.componentPlatform,
        componentVersionDependencies=command.componentVersionDependencies.value,
        softwareVendor=command.softwareVendor.value,
        softwareVersion=command.softwareVersion.value,
        licenseDashboard=command.licenseDashboard.value if command.licenseDashboard else None,
        notes=command.notes.value if command.notes else None,
        status=component_version.ComponentVersionStatus.Creating,
        createDate=current_time,
        lastUpdateDate=current_time,
        createdBy=command.createdBy.value,
        lastUpdatedBy=command.createdBy.value,
    )

    with uow:
        uow.get_repository(component_version.ComponentVersionPrimaryKey, component_version.ComponentVersion).add(
            component_version_entity
        )
        uow.commit()

    message_bus.publish(
        component_version_creation_started.ComponentVersionCreationStarted(
            component_id=command.componentId.value,
            component_version_id=component_version_entity.componentVersionId,
            component_version_description=command.componentVersionDescription.value,
            component_version_name=new_component_version_name,
            component_version_yaml_definition=command.componentVersionYamlDefinition.value,
            component_version_dependencies=command.componentVersionDependencies.value,
        )
    )
