import assertpy
import pytest
from freezegun import freeze_time

from app.packaging.domain.command_handlers.component import retire_component_version_command_handler
from app.packaging.domain.events.component import component_version_retirement_started
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component_version
from app.packaging.domain.model.shared import component_version_entry, recipe_version_entry
from app.shared.middleware.authorization import VirtualWorkbenchRoles


def test_handle_should_raise_exception_when_component_version_is_not_found(
    get_retire_component_version_command_mock,
    message_bus_mock,
    component_version_query_service_mock,
    mandatory_components_list_query_service_mock,
    uow_mock,
):
    # ARRANGE
    component_version_query_service_mock.get_component_version.return_value = None
    retire_component_version_command_mock = get_retire_component_version_command_mock()

    # ACT
    with pytest.raises(domain_exception.DomainException) as exc_info:
        retire_component_version_command_handler.handle(
            command=retire_component_version_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_query_service=component_version_query_service_mock,
            mandatory_components_list_query_service=mandatory_components_list_query_service_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exc_info.value)).is_equal_to(
        f"Version {retire_component_version_command_mock.componentVersionId.value} of component {retire_component_version_command_mock.componentId.value} does not exist."
    )


def test_handle_should_raise_exception_when_version_name_is_invalid(
    get_retire_component_version_command_mock,
    get_test_component_version_with_specific_version_name_and_status,
    message_bus_mock,
    component_version_query_service_mock,
    mandatory_components_list_query_service_mock,
    uow_mock,
):
    # ARRANGE
    component_version_name = "a.b.c"
    component_version_query_service_mock.get_component_version.return_value = (
        get_test_component_version_with_specific_version_name_and_status(
            version_name=component_version_name,
            status=component_version.ComponentVersionStatus.Released,
        )
    )
    retire_component_version_command_mock = get_retire_component_version_command_mock()

    # ACT
    with pytest.raises(domain_exception.DomainException) as exc_info:
        retire_component_version_command_handler.handle(
            command=retire_component_version_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_query_service=component_version_query_service_mock,
            mandatory_components_list_query_service=mandatory_components_list_query_service_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exc_info.value)).is_equal_to(
        f"Version {component_version_name} is not a valid SemVer string."
    )


@pytest.mark.parametrize(
    "component_version_status",
    (
        component_version.ComponentVersionStatus.Created,
        component_version.ComponentVersionStatus.Creating,
        component_version.ComponentVersionStatus.Retired,
        component_version.ComponentVersionStatus.Testing,
        component_version.ComponentVersionStatus.Updating,
    ),
)
def test_handle_should_raise_exception_when_status_is_invalid(
    get_retire_component_version_command_mock,
    get_test_component_version_with_specific_version_name_and_status,
    message_bus_mock,
    component_version_query_service_mock,
    mandatory_components_list_query_service_mock,
    component_version_status,
    uow_mock,
):
    # ARRANGE
    component_version_query_service_mock.get_component_version.return_value = (
        get_test_component_version_with_specific_version_name_and_status(
            version_name="1.0.0-rc.1",
            status=component_version_status,
        )
    )
    retire_component_version_command_mock = get_retire_component_version_command_mock()

    # ACT
    with pytest.raises(domain_exception.DomainException) as exc_info:
        retire_component_version_command_handler.handle(
            command=retire_component_version_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_query_service=component_version_query_service_mock,
            mandatory_components_list_query_service=mandatory_components_list_query_service_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exc_info.value)).is_equal_to(
        f"Version {retire_component_version_command_mock.componentVersionId.value} of component {retire_component_version_command_mock.componentId.value} "
        f"can't be retired while in {component_version_status} status: "
        f"only {component_version.ComponentVersionStatus.Failed}, "
        f"{component_version.ComponentVersionStatus.Released}, "
        f"and {component_version.ComponentVersionStatus.Validated} states are accepted."
    )


def test_handle_should_raise_exception_when_version_is_released_and_roles_are_not_allowed(
    get_retire_component_version_command_mock,
    get_test_component_version_with_specific_version_name_and_status,
    message_bus_mock,
    component_version_query_service_mock,
    mandatory_components_list_query_service_mock,
    uow_mock,
):
    # ARRANGE
    component_version_name = "1.0.0"
    component_version_query_service_mock.get_component_version.return_value = (
        get_test_component_version_with_specific_version_name_and_status(
            version_name=component_version_name,
            status=component_version.ComponentVersionStatus.Released,
        )
    )
    retire_component_version_command_mock = get_retire_component_version_command_mock()

    # ACT
    with pytest.raises(domain_exception.DomainException) as exc_info:
        retire_component_version_command_handler.handle(
            command=retire_component_version_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_query_service=component_version_query_service_mock,
            mandatory_components_list_query_service=mandatory_components_list_query_service_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exc_info.value)).is_equal_to(
        f"Version {component_version_name} of component {retire_component_version_command_mock.componentId.value} can't be retired by "
        f"{sorted([item.value for item in retire_component_version_command_mock.userRoles])} role{'s' if len(retire_component_version_command_mock.userRoles) > 1 else ''}."
    )


@pytest.mark.parametrize(
    "component_version_name,component_version_status,user_roles",
    (
        (
            "1.0.0-rc.1",
            component_version.ComponentVersionStatus.Failed,
            [
                VirtualWorkbenchRoles.BetaUser,
                VirtualWorkbenchRoles.PlatformUser,
                VirtualWorkbenchRoles.ProductContributor,
            ],
        ),
        (
            "1.0.0-rc.1",
            component_version.ComponentVersionStatus.Validated,
            [
                VirtualWorkbenchRoles.BetaUser,
                VirtualWorkbenchRoles.PlatformUser,
                VirtualWorkbenchRoles.ProductContributor,
            ],
        ),
        (
            "1.0.0",
            component_version.ComponentVersionStatus.Failed,
            [
                VirtualWorkbenchRoles.BetaUser,
                VirtualWorkbenchRoles.PlatformUser,
                VirtualWorkbenchRoles.PowerUser,
                VirtualWorkbenchRoles.ProductContributor,
            ],
        ),
        (
            "1.0.0",
            component_version.ComponentVersionStatus.Failed,
            [
                VirtualWorkbenchRoles.BetaUser,
                VirtualWorkbenchRoles.PlatformUser,
                VirtualWorkbenchRoles.PowerUser,
                VirtualWorkbenchRoles.ProductContributor,
                VirtualWorkbenchRoles.ProgramOwner,
            ],
        ),
        (
            "1.0.0",
            component_version.ComponentVersionStatus.Failed,
            [
                VirtualWorkbenchRoles.Admin,
                VirtualWorkbenchRoles.BetaUser,
                VirtualWorkbenchRoles.PlatformUser,
                VirtualWorkbenchRoles.PowerUser,
                VirtualWorkbenchRoles.ProductContributor,
                VirtualWorkbenchRoles.ProgramOwner,
            ],
        ),
        (
            "1.0.0",
            component_version.ComponentVersionStatus.Released,
            [
                VirtualWorkbenchRoles.BetaUser,
                VirtualWorkbenchRoles.PlatformUser,
                VirtualWorkbenchRoles.PowerUser,
                VirtualWorkbenchRoles.ProductContributor,
            ],
        ),
        (
            "1.0.0",
            component_version.ComponentVersionStatus.Released,
            [
                VirtualWorkbenchRoles.BetaUser,
                VirtualWorkbenchRoles.PlatformUser,
                VirtualWorkbenchRoles.PowerUser,
                VirtualWorkbenchRoles.ProductContributor,
                VirtualWorkbenchRoles.ProgramOwner,
            ],
        ),
        (
            "1.0.0",
            component_version.ComponentVersionStatus.Released,
            [
                VirtualWorkbenchRoles.Admin,
                VirtualWorkbenchRoles.BetaUser,
                VirtualWorkbenchRoles.PlatformUser,
                VirtualWorkbenchRoles.PowerUser,
                VirtualWorkbenchRoles.ProductContributor,
                VirtualWorkbenchRoles.ProgramOwner,
            ],
        ),
    ),
)
@freeze_time("2023-10-12")
def test_handle_should_retire_version(
    generic_repo_mock,
    get_retire_component_version_command_mock,
    get_test_component_version_arn,
    get_test_component_version_with_specific_version_name_and_status,
    get_test_mandatory_components_list_with_specific_mandatory_components_versions,
    message_bus_mock,
    component_version_query_service_mock,
    mandatory_components_list_query_service_mock,
    component_version_name,
    component_version_status,
    uow_mock,
    user_roles,
):
    # ARRANGE
    component_version_entity = get_test_component_version_with_specific_version_name_and_status(
        version_name=component_version_name,
        status=component_version_status,
    )
    component_version_query_service_mock.get_component_version.return_value = component_version_entity
    mandatory_components_list_query_service_mock.get_mandatory_components_lists.return_value = [
        get_test_mandatory_components_list_with_specific_mandatory_components_versions()
    ]
    retire_component_version_command_mock = get_retire_component_version_command_mock(user_roles=user_roles)

    # ACT
    retire_component_version_command_handler.handle(
        command=retire_component_version_command_mock,
        uow=uow_mock,
        message_bus=message_bus_mock,
        component_version_query_service=component_version_query_service_mock,
        mandatory_components_list_query_service=mandatory_components_list_query_service_mock,
    )

    # ASSERT
    generic_repo_mock.update_attributes.assert_called_once_with(
        component_version.ComponentVersionPrimaryKey(
            componentId=retire_component_version_command_mock.componentId.value,
            componentVersionId=retire_component_version_command_mock.componentVersionId.value,
        ),
        lastUpdateDate="2023-10-12T00:00:00+00:00",
        lastUpdateBy=retire_component_version_command_mock.lastUpdatedBy.value,
        status=component_version.ComponentVersionStatus.Updating,
    )
    uow_mock.commit.assert_called()
    message_bus_mock.publish.assert_called_once_with(
        component_version_retirement_started.ComponentVersionRetirementStarted(
            componentId=retire_component_version_command_mock.componentId.value,
            componentVersionId=retire_component_version_command_mock.componentVersionId.value,
            componentBuildVersionArn=get_test_component_version_arn(version_name=component_version_name),
            componentVersionDependencies=component_version_entity.componentVersionDependencies,
        )
    )


@pytest.mark.parametrize(
    "component_version_associations_list",
    (
        [
            component_version_entry.ComponentVersionEntry(
                componentId="comp-00000000",
                componentName="test-component-0000000",
                componentVersionId="vers-00000000",
                componentVersionName="1.0.0",
            )
        ],
        [
            component_version_entry.ComponentVersionEntry(
                componentId="comp-00000000",
                componentName="test-component-0000000",
                componentVersionId="vers-00000000",
                componentVersionName="1.0.0",
            ),
            component_version_entry.ComponentVersionEntry(
                componentId="comp-00000001",
                componentName="test-component-0000001",
                componentVersionId="vers-00000001",
                componentVersionName="1.0.0-rc.1",
            ),
        ],
        [
            component_version_entry.ComponentVersionEntry(
                componentId="comp-00000000",
                componentName="test-component-0000000",
                componentVersionId="vers-00000000",
                componentVersionName="1.0.0",
            ),
            component_version_entry.ComponentVersionEntry(
                componentId="comp-00000001",
                componentName="test-component-0000001",
                componentVersionId="vers-00000001",
                componentVersionName="1.0.0-rc.1",
            ),
            component_version_entry.ComponentVersionEntry(
                componentId="comp-00000002",
                componentName="test-component-0000002",
                componentVersionId="vers-00000002",
                componentVersionName="1.0.0-rc.1",
            ),
        ],
    ),
)
def test_validate_component_version_associations_list_should_raise_exception_when_component_version_has_associations(
    component_version_associations_list,
    get_test_component_version,
):
    # ARRANGE
    component_version_entity: component_version.ComponentVersion = get_test_component_version
    component_version_entity.associatedComponentsVersions = component_version_associations_list

    # ACT
    with pytest.raises(domain_exception.DomainException) as exc_info:
        retire_component_version_command_handler.__validate_associated_components_versions_list(
            component_version_entity=component_version_entity,
        )

    # ASSERT
    assertpy.assert_that(str(exc_info.value)).is_equal_to(
        f"Version {component_version_entity.componentVersionId} of component "
        f"{component_version_entity.componentId} can't be retired if it has associated components versions."
    )


@pytest.mark.parametrize(
    "component_version_associations_list",
    (
        [],
        [
            component_version_entry.ComponentVersionEntry(
                componentId="comp-00000000",
                componentName="test-component-0000000",
                componentVersionId="vers-00000000",
                componentVersionName="1.0.0-rc.1",
            ),
        ],
        [
            component_version_entry.ComponentVersionEntry(
                componentId="comp-00000000",
                componentName="test-component-0000000",
                componentVersionId="vers-00000000",
                componentVersionName="1.0.0-rc.1",
            ),
            component_version_entry.ComponentVersionEntry(
                componentId="comp-00000001",
                componentName="test-component-0000001",
                componentVersionId="vers-00000001",
                componentVersionName="1.0.0-rc.1",
            ),
        ],
    ),
)
def test_validate_component_version_associations_list_should_succeed(
    component_version_associations_list,
    get_test_component_version,
):
    # ARRANGE
    component_version_entity: component_version.ComponentVersion = get_test_component_version
    component_version_entity.associatedComponentsVersions = component_version_associations_list

    # ACT
    retire_component_version_command_handler.__validate_associated_components_versions_list(
        component_version_entity=component_version_entity,
    )


def test_handle_should_raise_exception_when_version_is_included_in_mandatory_component_list(
    get_retire_component_version_command_mock,
    get_test_component_version_with_specific_version_name_and_status,
    get_test_mandatory_components_list_with_specific_mandatory_components_versions,
    message_bus_mock,
    component_version_query_service_mock,
    mandatory_components_list_query_service_mock,
    uow_mock,
):
    # ARRANGE
    component_version_name = "1.0.0"
    component_version_entity = get_test_component_version_with_specific_version_name_and_status(
        version_name=component_version_name,
        status=component_version.ComponentVersionStatus.Released,
    )
    component_version_query_service_mock.get_component_version.return_value = component_version_entity
    mandatory_components_list_query_service_mock.get_mandatory_components_lists.return_value = [
        get_test_mandatory_components_list_with_specific_mandatory_components_versions(
            mandatory_components_versions=[
                component_version_entry.ComponentVersionEntry(
                    componentId=component_version_entity.componentId,
                    componentName=component_version_entity.componentName,
                    componentVersionId=component_version_entity.componentVersionId,
                    componentVersionName=component_version_entity.componentVersionName,
                    componentVersionType=component_version_entry.ComponentVersionEntryType.Helper.value,
                    order=1,
                ),
            ],
        )
    ]
    retire_component_version_command_mock = get_retire_component_version_command_mock(
        user_roles=[
            VirtualWorkbenchRoles.Admin,
            VirtualWorkbenchRoles.BetaUser,
            VirtualWorkbenchRoles.PlatformUser,
            VirtualWorkbenchRoles.PowerUser,
            VirtualWorkbenchRoles.ProductContributor,
            VirtualWorkbenchRoles.ProgramOwner,
        ]
    )

    # ACT
    with pytest.raises(domain_exception.DomainException) as exc_info:
        retire_component_version_command_handler.handle(
            command=retire_component_version_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_query_service=component_version_query_service_mock,
            mandatory_components_list_query_service=mandatory_components_list_query_service_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exc_info.value)).is_equal_to(
        f"Version {component_version_entity.componentVersionId} of component "
        f"{component_version_entity.componentId} can't be retired if it is included in a mandatory components list."
    )


@pytest.mark.parametrize(
    "recipe_version_associations_list",
    (
        [
            recipe_version_entry.RecipeVersionEntry(
                recipeId="reci-00000000",
                recipeName="test-recipe-0000000",
                recipeVersionId="vers-00000000",
                recipeVersionName="1.0.0",
            ),
        ],
        [
            recipe_version_entry.RecipeVersionEntry(
                recipeId="reci-00000000",
                recipeName="test-recipe-0000000",
                recipeVersionId="vers-00000000",
                recipeVersionName="1.0.0-rc.1",
            ),
            recipe_version_entry.RecipeVersionEntry(
                recipeId="reci-00000001",
                recipeName="test-recipe-0000001",
                recipeVersionId="vers-00000001",
                recipeVersionName="1.0.0",
            ),
        ],
    ),
)
def test_validate_recipe_version_associations_list_should_raise_exception_when_component_version_has_associations(
    recipe_version_associations_list,
    get_test_component_version,
):
    # ARRANGE
    component_version_entity: component_version.ComponentVersion = get_test_component_version
    component_version_entity.associatedRecipesVersions = recipe_version_associations_list

    # ACT
    with pytest.raises(domain_exception.DomainException) as exc_info:
        retire_component_version_command_handler.__validate_associated_recipes_versions_list(
            component_version_entity=component_version_entity,
        )

    # ASSERT
    assertpy.assert_that(str(exc_info.value)).is_equal_to(
        f"Version {component_version_entity.componentVersionId} of component "
        f"{component_version_entity.componentId} can't be retired if it has associated recipes versions."
    )


@pytest.mark.parametrize(
    "recipe_version_associations_list",
    (
        [],
        [
            recipe_version_entry.RecipeVersionEntry(
                recipeId="reci-00000000",
                recipeName="test-recipe-0000000",
                recipeVersionId="vers-00000000",
                recipeVersionName="1.0.0-rc.1",
            ),
        ],
        [
            recipe_version_entry.RecipeVersionEntry(
                recipeId="reci-00000000",
                recipeName="test-recipe-0000000",
                recipeVersionId="vers-00000000",
                recipeVersionName="1.0.0-rc.1",
            ),
            recipe_version_entry.RecipeVersionEntry(
                recipeId="reci-00000001",
                recipeName="test-recipe-0000001",
                recipeVersionId="vers-00000001",
                recipeVersionName="1.0.0-rc.1",
            ),
        ],
    ),
)
def test_validate_recipe_version_associations_list_should_succeed(
    recipe_version_associations_list,
    get_test_component_version,
):
    # ARRANGE
    component_version_entity: component_version.ComponentVersion = get_test_component_version
    component_version_entity.associatedRecipesVersions = recipe_version_associations_list

    # ACT
    retire_component_version_command_handler.__validate_associated_recipes_versions_list(
        component_version_entity=component_version_entity,
    )
