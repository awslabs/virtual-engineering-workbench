"""Parallel retirements of a component's dependents on the real DynamoDB unit of work (moto).

Infrastructure as code retires every dependent of a replaced base component at once. Each retirement removes its
entry from the base version's associatedComponentsVersions with a read-modify-write; without a
conditional write the last writer put back the entries the others had removed, and the stale entry
blocked the base version's retirement (DOMAIN_VALIDATION_FAILED).
"""

import logging
from unittest import mock

import assertpy
import pytest

from app.packaging.domain.command_handlers.component import (
    retire_component_version_command_handler,
    update_component_version_associations_command_handler,
)
from app.packaging.domain.commands.component import (
    retire_component_version_command,
    update_component_version_associations_command,
)
from app.packaging.domain.model.component import component_version
from app.packaging.domain.model.shared.component_version_entry import ComponentVersionEntry
from app.packaging.domain.value_objects.component import component_id_value_object
from app.packaging.domain.value_objects.component_version import (
    component_version_id_value_object,
    components_versions_list_value_object,
)
from app.packaging.domain.value_objects.shared import user_id_value_object, user_role_value_object

BASE = ("comp-0000base", "vers-0000base", "base")
DEPENDENTS = [("comp-1111aaaa", "vers-1111aaaa", "go-toolchain"), ("comp-2222bbbb", "vers-2222bbbb", "node-toolchain")]


def _entry(ids: tuple[str, str, str]) -> ComponentVersionEntry:
    component_id, version_id, name = ids
    return ComponentVersionEntry(
        componentId=component_id, componentName=name, componentVersionId=version_id, componentVersionName="1.4.0"
    )


def _version(ids: tuple[str, str, str], status: str, **fields) -> component_version.ComponentVersion:
    component_id, version_id, name = ids
    return component_version.ComponentVersion(
        componentId=component_id,
        componentVersionId=version_id,
        componentVersionName="1.4.0",
        componentName=name,
        componentVersionDescription="Test description",
        componentBuildVersionArn=f"arn:aws:imagebuilder:eu-north-1:123456789012:component/{name}/1.4.0/1",
        componentVersionS3Uri="s3://test/component.yaml",
        componentPlatform="Linux",
        componentSupportedArchitectures=["amd64"],
        componentSupportedOsVersions=["Ubuntu 24"],
        softwareVendor="vector",
        softwareVersion="1.0.0",
        status=status,
        createDate="2026-10-01T00:00:00+00:00",
        createdBy="T000001",
        lastUpdateDate="2026-10-01T00:00:00+00:00",
        lastUpdatedBy="T000001",
        **fields,
    )


def _add(uow, entity: component_version.ComponentVersion) -> None:
    with uow:
        uow.get_repository(component_version.ComponentVersionPrimaryKey, component_version.ComponentVersion).add(entity)
        uow.commit()


def _retirement_associations_command(dependent: tuple[str, str, str]):
    """What the retirement event handler sends: no dependencies now, the base before."""
    return update_component_version_associations_command.UpdateComponentVersionAssociationsCommand(
        componentId=component_id_value_object.from_str(dependent[0]),
        componentVersionId=component_version_id_value_object.from_str(dependent[1]),
        componentsVersionDependencies=components_versions_list_value_object.from_list([]),
        previousComponentsVersionDependencies=components_versions_list_value_object.from_list([_entry(BASE)]),
    )


class InterleavingQueryService:
    """Runs `interleave` right after the first read of the base version, before the reader writes."""

    def __init__(self, inner, interleave):
        self._inner = inner
        self._interleave = interleave

    def get_component_version(self, component_id: str, version_id: str):
        result = self._inner.get_component_version(component_id=component_id, version_id=version_id)
        if version_id == BASE[1] and self._interleave:
            interleave, self._interleave = self._interleave, None
            interleave()
        return result

    def __getattr__(self, name):
        return getattr(self._inner, name)


@pytest.fixture()
def base_with_retired_dependents(backend_app_table, uow_mock):
    _add(uow_mock, _version(BASE, "RELEASED", associatedComponentsVersions=[_entry(d) for d in DEPENDENTS]))
    for dependent in DEPENDENTS:
        _add(uow_mock, _version(dependent, "RETIRED", componentVersionDependencies=[_entry(BASE)]))


def test_parallel_retirements_remove_every_association(
    base_with_retired_dependents, uow_mock, get_dynamodb_component_version_query_service, monkeypatch
):
    # ARRANGE: the second retirement runs completely between the first one's read and its write
    monkeypatch.setattr(update_component_version_associations_command_handler, "WRITE_BACKOFF_SECONDS", 0)
    query_service = get_dynamodb_component_version_query_service
    logger = mock.create_autospec(spec=logging.Logger)

    def second_retirement():
        update_component_version_associations_command_handler.handle(
            command=_retirement_associations_command(DEPENDENTS[1]),
            component_version_qry_srv=query_service,
            logger=logger,
            uow=uow_mock,
        )

    # ACT
    update_component_version_associations_command_handler.handle(
        command=_retirement_associations_command(DEPENDENTS[0]),
        component_version_qry_srv=InterleavingQueryService(query_service, second_retirement),
        logger=logger,
        uow=uow_mock,
    )

    # ASSERT: neither removal is lost
    base = query_service.get_component_version(component_id=BASE[0], version_id=BASE[1])
    assertpy.assert_that(base.associatedComponentsVersions).is_empty()


def test_retire_ignores_a_stale_association_of_a_retired_version(
    backend_app_table, uow_mock, get_dynamodb_component_version_query_service
):
    # ARRANGE: the base still lists a dependent that is retired (left by a lost update)
    _add(
        uow_mock,
        _version(
            BASE, "RELEASED", associatedComponentsVersions=[_entry(DEPENDENTS[0])], componentVersionDependencies=[]
        ),
    )
    _add(uow_mock, _version(DEPENDENTS[0], "RETIRED", componentVersionDependencies=[_entry(BASE)]))
    mandatory_lists = mock.Mock()
    mandatory_lists.get_mandatory_components_lists.return_value = []
    message_bus = mock.Mock()

    # ACT
    retire_component_version_command_handler.handle(
        command=retire_component_version_command.RetireComponentVersionCommand(
            componentId=component_id_value_object.from_str(BASE[0]),
            componentVersionId=component_version_id_value_object.from_str(BASE[1]),
            userRoles=[user_role_value_object.from_str("ADMIN")],
            lastUpdatedBy=user_id_value_object.from_str("T000001"),
        ),
        component_version_query_service=get_dynamodb_component_version_query_service,
        mandatory_components_list_query_service=mandatory_lists,
        message_bus=message_bus,
        uow=uow_mock,
    )

    # ASSERT
    retired = get_dynamodb_component_version_query_service.get_component_version(
        component_id=BASE[0], version_id=BASE[1]
    )
    assertpy.assert_that(retired.status).is_equal_to(component_version.ComponentVersionStatus.Updating)
    message_bus.publish.assert_called_once()


def test_retire_still_refuses_a_live_dependent(
    backend_app_table, uow_mock, get_dynamodb_component_version_query_service
):
    # ARRANGE: a released dependent still uses the base
    _add(
        uow_mock,
        _version(
            BASE, "RELEASED", associatedComponentsVersions=[_entry(DEPENDENTS[0])], componentVersionDependencies=[]
        ),
    )
    _add(uow_mock, _version(DEPENDENTS[0], "RELEASED", componentVersionDependencies=[_entry(BASE)]))
    mandatory_lists = mock.Mock()
    mandatory_lists.get_mandatory_components_lists.return_value = []

    # ACT / ASSERT
    with pytest.raises(Exception, match="associated components versions"):
        retire_component_version_command_handler.handle(
            command=retire_component_version_command.RetireComponentVersionCommand(
                componentId=component_id_value_object.from_str(BASE[0]),
                componentVersionId=component_version_id_value_object.from_str(BASE[1]),
                userRoles=[user_role_value_object.from_str("ADMIN")],
                lastUpdatedBy=user_id_value_object.from_str("T000001"),
            ),
            component_version_query_service=get_dynamodb_component_version_query_service,
            mandatory_components_list_query_service=mandatory_lists,
            message_bus=mock.Mock(),
            uow=uow_mock,
        )
