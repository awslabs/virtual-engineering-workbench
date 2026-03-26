import assertpy
import pytest
from freezegun import freeze_time

from app.packaging.domain.command_handlers.recipe import release_recipe_version_command_handler
from app.packaging.domain.commands.recipe import release_recipe_version_command
from app.packaging.domain.events.recipe import recipe_version_release_completed
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component_version
from app.packaging.domain.model.recipe import recipe_version
from app.packaging.domain.model.shared import component_version_entry
from app.packaging.domain.value_objects.recipe import recipe_id_value_object
from app.packaging.domain.value_objects.recipe_version import recipe_version_id_value_object
from app.packaging.domain.value_objects.shared import user_id_value_object


@pytest.fixture()
def mock_recipe_version(mock_recipe_object) -> recipe_version.RecipeVersion:
    return recipe_version.RecipeVersion(
        recipeId=mock_recipe_object.recipeId,
        recipeVersionId="vers-12345abc",
        recipeVersionName="Test Version",
        recipeName="Test recipe",
        recipeVersionDescription="Test description",
        recipeComponentsVersions=[
            component_version_entry.ComponentVersionEntry(
                componentId="comp-1234abcd",
                componentName="component-1234abcd",
                componentVersionId="vers-1234abcd",
                componentVersionName="1.0.0",
                order=1,
            )
        ],
        status=recipe_version.RecipeVersionStatus.Validated,
        parentImageUpstreamId="ami-12345",
        recipeVersionVolumeSize="8",
        createDate="2023-09-29T00:00:00+00:00",
        createdBy="T123456",
        lastUpdateDate="2023-09-29T00:00:00+00:00",
        lastUpdatedBy="T123456",
    )


@pytest.fixture()
def mock_recipe_version_with_rc_component(mock_recipe_object) -> recipe_version.RecipeVersion:
    return recipe_version.RecipeVersion(
        recipeId=mock_recipe_object.recipeId,
        recipeVersionId="vers-12345abc",
        recipeVersionName="Test Version",
        recipeName="Test recipe",
        recipeVersionDescription="Test description",
        recipeComponentsVersions=[
            component_version_entry.ComponentVersionEntry(
                componentId="comp-1234abcd",
                componentName="test-component",
                componentVersionId="vers-1234abcd",
                componentVersionName="1.0.0-rc2",
                order=1,
            )
        ],
        status=recipe_version.RecipeVersionStatus.Validated,
        parentImageUpstreamId="ami-12345",
        recipeVersionVolumeSize="8",
        createDate="2023-09-29T00:00:00+00:00",
        createdBy="T123456",
        lastUpdateDate="2023-09-29T00:00:00+00:00",
        lastUpdatedBy="T123456",
    )


@pytest.fixture()
def release_recipe_version_command_mock(
    mock_recipe_version,
) -> release_recipe_version_command.ReleaseRecipeVersionCommand:
    return release_recipe_version_command.ReleaseRecipeVersionCommand(
        recipeId=recipe_id_value_object.from_str(mock_recipe_version.recipeId),
        recipeVersionId=recipe_version_id_value_object.from_str(mock_recipe_version.recipeVersionId),
        lastUpdatedBy=user_id_value_object.from_str("T01267HN"),
    )


@freeze_time("2023-12-15")
@pytest.mark.parametrize(
    "fetched_release_name,expected_version_name",
    (
        ("2.0.0-rc.1", "2.0.0"),
        ("2.1.0-rc.1", "2.1.0"),
        ("2.0.1-rc.1", "2.0.1"),
    ),
)
def test_handle_should_release_version(
    fetched_release_name,
    expected_version_name,
    release_recipe_version_command_mock,
    component_version_query_service_mock,
    recipe_version_query_service_mock,
    generic_repo_mock,
    uow_mock,
    message_bus_mock,
    get_test_component_version_with_specific_status,
    mock_recipe_version,
):
    # ARRANGE
    mock_recipe_version.recipeVersionName = fetched_release_name
    component_version_query_service_mock.get_component_version.return_value = (
        get_test_component_version_with_specific_status(status=component_version.ComponentVersionStatus.Released)
    )
    recipe_version_entity = mock_recipe_version
    recipe_version_query_service_mock.get_recipe_version.return_value = mock_recipe_version

    # ACT
    result = release_recipe_version_command_handler.handle(
        command=release_recipe_version_command_mock,
        uow=uow_mock,
        message_bus=message_bus_mock,
        component_version_qry_srv=component_version_query_service_mock,
        recipe_version_qry_srv=recipe_version_query_service_mock,
    )

    # ASSERT
    recipe_version_entity.recipeVersionName = expected_version_name
    recipe_version_entity.status = recipe_version.RecipeVersionStatus.Released
    recipe_version_entity.lastUpdatedBy = release_recipe_version_command_mock.lastUpdatedBy.value
    recipe_version_entity.lastUpdateDate = "2023-12-15T00:00:00+00:00"
    generic_repo_mock.update_entity.assert_called_once_with(
        recipe_version.RecipeVersionPrimaryKey(
            recipeId=release_recipe_version_command_mock.recipeId.value,
            recipeVersionId=release_recipe_version_command_mock.recipeVersionId.value,
        ),
        recipe_version_entity,
    )
    uow_mock.commit.assert_called()
    message_bus_mock.publish.assert_called_once_with(
        recipe_version_release_completed.RecipeVersionReleaseCompleted(
            recipe_id=release_recipe_version_command_mock.recipeId.value,
            recipe_version_id=release_recipe_version_command_mock.recipeVersionId.value,
            recipeComponentsVersions=mock_recipe_version.recipeComponentsVersions,
        )
    )
    assertpy.assert_that(result).is_equal_to(
        {"recipeVersionId": release_recipe_version_command_mock.recipeVersionId.value}
    )


def test_handle_should_fail_on_already_released_version(
    release_recipe_version_command_mock,
    component_version_query_service_mock,
    recipe_version_query_service_mock,
    uow_mock,
    message_bus_mock,
    mock_recipe_version,
):
    # ARRANGE
    mock_recipe_version.recipeVersionName = "1.1.0"
    recipe_version_query_service_mock.get_recipe_version.return_value = mock_recipe_version

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        release_recipe_version_command_handler.handle(
            command=release_recipe_version_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_qry_srv=component_version_query_service_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
        )

    # ASSERT
    assert str(e.value) == (
        "Cannot release an already released recipe version "
        f"{mock_recipe_version.recipeVersionName} - Only *rc allowed."
    )


def test_handle_should_fail_on_not_validated_recipes(
    release_recipe_version_command_mock,
    component_version_query_service_mock,
    recipe_version_query_service_mock,
    uow_mock,
    message_bus_mock,
    mock_recipe_version,
):
    # ARRANGE
    mock_recipe_version.recipeVersionName = "1.1.1-rc.1"
    mock_recipe_version.status = recipe_version.RecipeVersionStatus.Updating
    recipe_version_query_service_mock.get_recipe_version.return_value = mock_recipe_version

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        release_recipe_version_command_handler.handle(
            command=release_recipe_version_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_qry_srv=component_version_query_service_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
        )

    # ASSERT
    assert str(e.value) == (
        f"Version {mock_recipe_version.recipeVersionName} of recipe "
        f"{mock_recipe_version.recipeId} has not been validated."
    )


def test_handle_should_fail_on_non_existent_recipe_version(
    component_version_query_service_mock,
    recipe_version_query_service_mock,
    message_bus_mock,
    uow_mock,
):
    # ARRANGE
    recipe_version_query_service_mock.get_recipe_version.return_value = None
    command = release_recipe_version_command.ReleaseRecipeVersionCommand(
        recipeId=recipe_id_value_object.from_str("comp-1234abc"),
        recipeVersionId=recipe_version_id_value_object.from_str("vers-1234abc"),
        lastUpdatedBy=user_id_value_object.from_str("T01267HN"),
    )

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        release_recipe_version_command_handler.handle(
            command=command,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_qry_srv=component_version_query_service_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
        )

    # ASSERT
    assert str(e.value) == f"Version {command.recipeVersionId.value} of recipe {command.recipeId.value} does not exist."


def test_release_recipe_version_command_handler_should_raise_an_exception_if_a_recipe_version_name_is_invalid(
    release_recipe_version_command_mock,
    component_version_query_service_mock,
    recipe_version_query_service_mock,
    uow_mock,
    message_bus_mock,
    mock_recipe_version,
):
    # ARRANGE
    mock_recipe_version.recipeVersionName = "a"
    recipe_version_query_service_mock.get_recipe_version.return_value = mock_recipe_version

    # ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        release_recipe_version_command_handler.handle(
            command=release_recipe_version_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_qry_srv=component_version_query_service_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(
        f"Version {mock_recipe_version.recipeVersionName} is not a valid SemVer string."
    )


@pytest.mark.parametrize(
    "status",
    (
        component_version.ComponentVersionStatus.Created,
        component_version.ComponentVersionStatus.Creating,
        component_version.ComponentVersionStatus.Failed,
        component_version.ComponentVersionStatus.Retired,
        component_version.ComponentVersionStatus.Testing,
        component_version.ComponentVersionStatus.Updating,
        component_version.ComponentVersionStatus.Validated,
    ),
)
def test_release_recipe_version_command_handler_should_raise_an_exception_if_a_component_version_is_not_released(
    component_version_query_service_mock,
    get_test_component_version_with_specific_status,
    mock_recipe_version,
    recipe_version_query_service_mock,
    release_recipe_version_command_mock,
    status,
    uow_mock,
    message_bus_mock,
):
    # ARRANGE
    component_version_entity = get_test_component_version_with_specific_status(status=status)
    component_version_query_service_mock.get_component_version.return_value = component_version_entity
    mock_recipe_version.recipeVersionName = "1.0.0-rc.1"
    recipe_version_query_service_mock.get_recipe_version.return_value = mock_recipe_version

    # ACT
    with pytest.raises(domain_exception.DomainException) as exec_info:
        release_recipe_version_command_handler.handle(
            command=release_recipe_version_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_qry_srv=component_version_query_service_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
        )

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(
        f"Version {component_version_entity.componentVersionId} of component "
        f"{component_version_entity.componentId} has not been released."
    )


def test_release_recipe_version_command_handler_should_update_compnonent_version_name_if_a_component_version_was_released(
    component_version_query_service_mock,
    get_test_component_version_with_specific_version_name_and_status,
    mock_recipe_version_with_rc_component,
    recipe_version_query_service_mock,
    release_recipe_version_command_mock,
    uow_mock,
    message_bus_mock,
    generic_repo_mock,
):
    # ARRANGE
    component_version_entity = get_test_component_version_with_specific_version_name_and_status(
        status=component_version.ComponentVersionStatus.Released, version_name="1.0.0"
    )
    component_version_query_service_mock.get_component_version.return_value = component_version_entity
    recipe_version_entity = mock_recipe_version_with_rc_component
    mock_recipe_version_with_rc_component.recipeVersionName = "1.0.0-rc.1"
    recipe_version_query_service_mock.get_recipe_version.return_value = recipe_version_entity

    # ACT
    release_recipe_version_command_handler.handle(
        command=release_recipe_version_command_mock,
        uow=uow_mock,
        message_bus=message_bus_mock,
        component_version_qry_srv=component_version_query_service_mock,
        recipe_version_qry_srv=recipe_version_query_service_mock,
    )

    # Assert that the component version name is updated
    assert component_version_entity.componentVersionName == "1.0.0"
    # ASSERT
    recipe_version_entity.recipeVersionName = "1.0.0"
    recipe_version_entity.status = recipe_version.RecipeVersionStatus.Released
    recipe_version_entity.lastUpdatedBy = release_recipe_version_command_mock.lastUpdatedBy.value
    recipe_version_entity.lastUpdateDate = "2023-12-15T00:00:00+00:00"
    recipe_version_entity.recipeComponentsVersions = (
        [
            component_version_entry.ComponentVersionEntry(
                componentId=component_version_entity.componentId,
                componentName=component_version_entity.componentName,
                componentVersionId=component_version_entity.componentVersionId,
                componentVersionName=component_version_entity.componentVersionName,
                order=1,
            )
        ],
    )
    generic_repo_mock.update_entity.assert_called_once_with(
        recipe_version.RecipeVersionPrimaryKey(
            recipeId=release_recipe_version_command_mock.recipeId.value,
            recipeVersionId=release_recipe_version_command_mock.recipeVersionId.value,
        ),
        recipe_version_entity,
    )
    uow_mock.commit.assert_called()
    message_bus_mock.publish.assert_called_once_with(
        recipe_version_release_completed.RecipeVersionReleaseCompleted(
            recipe_id=release_recipe_version_command_mock.recipeId.value,
            recipe_version_id=release_recipe_version_command_mock.recipeVersionId.value,
            recipeComponentsVersions=[
                component_version_entry.ComponentVersionEntry(
                    componentId=component_version_entity.componentId,
                    componentName=component_version_entity.componentName,
                    componentVersionId=component_version_entity.componentVersionId,
                    componentVersionName=component_version_entity.componentVersionName,
                    order=1,
                )
            ],
        )
    )
