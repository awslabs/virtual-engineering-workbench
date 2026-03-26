from app.packaging.domain.model.component import component, component_version_test_execution
from app.packaging.domain.model.recipe import recipe, recipe_version, recipe_version_test_execution


def test_uow_should_be_able_to_commit_with_valid_component_entity_config(
    uow_mock, backend_app_table, get_test_component
):
    # ARRANGE & ACT & ASSERT
    with uow_mock:
        uow_mock.get_repository(repo_key=component.ComponentPrimaryKey, repo_type=component.Component).add(
            get_test_component()
        )
        uow_mock.commit()


def test_uow_should_be_able_to_commit_with_valid_component_project_association_entity_config(
    uow_mock, backend_app_table, get_component_project_association
):
    # ARRANGE & ACT & ASSERT
    with uow_mock:
        uow_mock.get_repository(repo_key=component.ComponentPrimaryKey, repo_type=component.Component).add(
            get_component_project_association()
        )
        uow_mock.commit()


def test_uow_should_be_able_to_commit_with_valid_component_version_entity_config(
    uow_mock, backend_app_table, get_mock_component_version
):
    # ARRANGE & ACT & ASSERT
    with uow_mock:
        uow_mock.get_repository(repo_key=component.ComponentPrimaryKey, repo_type=component.Component).add(
            get_mock_component_version()
        )
        uow_mock.commit()


def test_uow_should_be_able_to_commit_with_valid_component_version_test_execution_entity_config(
    uow_mock, backend_app_table, get_mock_component_version_test_execution
):
    # ARRANGE & ACT & ASSERT
    with uow_mock:
        uow_mock.get_repository(
            repo_key=component_version_test_execution.ComponentVersionTestExecutionPrimaryKey,
            repo_type=component_version_test_execution.ComponentVersionTestExecution,
        ).add(get_mock_component_version_test_execution())
        uow_mock.commit()


def test_uow_should_be_able_to_commit_with_valid_recipe_entity_config(uow_mock, backend_app_table, get_mock_recipe):
    # ARRANGE & ACT & ASSERT
    with uow_mock:
        uow_mock.get_repository(repo_key=recipe.RecipePrimaryKey, repo_type=recipe.Recipe).add(get_mock_recipe())
    uow_mock.commit()


def test_uow_should_be_able_to_commit_with_valid_recipe_version_entity_config(
    uow_mock, backend_app_table, get_mock_recipe_version
):
    # ARRANGE & ACT & ASSERT
    with uow_mock:
        uow_mock.get_repository(
            repo_key=recipe_version.RecipeVersionPrimaryKey, repo_type=recipe_version.RecipeVersion
        ).add(get_mock_recipe_version())
        uow_mock.commit()


def test_uow_should_be_able_to_commit_with_valid_recipe_version_test_execution_entity_config(
    uow_mock,
    backend_app_table,
    get_mock_recipe_version_test_execution,
):
    # ARRANGE & ACT & ASSERT
    with uow_mock:
        uow_mock.get_repository(
            repo_key=recipe_version_test_execution.RecipeVersionTestExecutionPrimaryKey,
            repo_type=recipe_version_test_execution.RecipeVersionTestExecution,
        ).add(get_mock_recipe_version_test_execution())
        uow_mock.commit()
