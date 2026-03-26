import pytest
from assertpy import assertpy
from freezegun import freeze_time

from app.packaging.domain.command_handlers.component import share_component_command_handler
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component.component_project_association import ComponentProjectAssociation
from app.shared.middleware.authorization import VirtualWorkbenchRoles


@pytest.mark.parametrize(
    "user_roles",
    (
        [
            VirtualWorkbenchRoles.BetaUser,
            VirtualWorkbenchRoles.PlatformUser,
            VirtualWorkbenchRoles.ProductContributor,
        ],
        [
            VirtualWorkbenchRoles.BetaUser,
            VirtualWorkbenchRoles.PlatformUser,
            VirtualWorkbenchRoles.PowerUser,
            VirtualWorkbenchRoles.ProductContributor,
        ],
        [
            VirtualWorkbenchRoles.BetaUser,
            VirtualWorkbenchRoles.PlatformUser,
            VirtualWorkbenchRoles.PowerUser,
            VirtualWorkbenchRoles.ProductContributor,
            VirtualWorkbenchRoles.ProgramOwner,
        ],
        [
            VirtualWorkbenchRoles.Admin,
            VirtualWorkbenchRoles.BetaUser,
            VirtualWorkbenchRoles.PlatformUser,
            VirtualWorkbenchRoles.PowerUser,
            VirtualWorkbenchRoles.ProductContributor,
            VirtualWorkbenchRoles.ProgramOwner,
        ],
    ),
)
@freeze_time("2023-10-12")
def test_handle_should_share_component_with_project(
    generic_repo_mock,
    component_query_service_mock,
    get_test_component,
    get_test_component_id,
    get_share_component_command_mock,
    uow_mock,
    user_roles,
    get_test_project_ids,
):
    # ARRANGE
    component_query_service_mock.get_component.return_value = get_test_component
    share_component_command_mock = get_share_component_command_mock(user_roles=user_roles)
    # ACT
    try:
        share_component_command_handler.handle(
            command=share_component_command_mock, component_qry_srv=component_query_service_mock, uow=uow_mock
        )
        for project_id in get_test_project_ids:
            generic_repo_mock.add.assert_any_call(
                ComponentProjectAssociation(componentId=get_test_component_id, projectId=project_id)
            )
            uow_mock.commit.assert_called()
    # ASSERT
    except domain_exception.DomainException as err:
        assertpy.assert_that(str(err)).is_equal_to(
            f"User role is not allowed to share component {get_test_component_id} with project"
            f"{'s' if len(get_test_project_ids) > 1 else ''} {sorted([item for item in get_test_project_ids])}."
        )


def test_handle_should_raise_if_component_not_found(
    component_query_service_mock,
    get_test_component_id,
    get_share_component_command_mock,
    uow_mock,
):
    # ARRANGE
    user_roles = [
        VirtualWorkbenchRoles.Admin,
        VirtualWorkbenchRoles.PlatformUser,
        VirtualWorkbenchRoles.ProductContributor,
    ]
    component_query_service_mock.get_component.return_value = None
    share_component_command_mock = get_share_component_command_mock(user_roles=user_roles)
    # ACT

    # ARRANGE & ACT
    with pytest.raises(domain_exception.DomainException) as err:
        share_component_command_handler.handle(
            command=share_component_command_mock, component_qry_srv=component_query_service_mock, uow=uow_mock
        )

    # ASSERT
    assertpy.assert_that(str(err.value)).is_equal_to(f"Component {get_test_component_id} does not exist.")
