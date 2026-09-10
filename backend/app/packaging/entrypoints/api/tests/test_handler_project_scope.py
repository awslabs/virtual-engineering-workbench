"""Project scoping of the packaging routes that address a component or a recipe by id."""

import ast
import dataclasses
import pathlib

import assertpy
import pytest
from aws_lambda_powertools.event_handler.exceptions import NotFoundError

from app.packaging.entrypoints.api.model import api_model
from app.packaging.entrypoints.api.tests.conftest import GlobalVariables

HANDLER_PATH = pathlib.Path(__file__).resolve().parents[1] / "handler.py"
DOMAIN_PATH = pathlib.Path(__file__).resolve().parents[3] / "domain"
RECIPE_COMMAND_HANDLERS_PATH = DOMAIN_PATH / "command_handlers" / "recipe"
HTTP_METHODS = frozenset({"get", "post", "put", "delete", "patch"})
RESOLVER_NAME = "app"
COMPONENT_GUARD = "require_component_in_project"
COMPONENT_VERSION_GUARD = "require_component_version_in_component"
RECIPE_GUARD = "require_recipe_in_project"
RECIPE_VERSION_GUARD = "require_recipe_version_in_recipe"
PROJECT_ID_KEYWORDS = frozenset({"project_id", "projectId"})

RECIPE_READ = "get_recipe"
ID_ONLY_READ_PREFIXES = ("get_recipe_version", "get_component_version")
PROJECT_KEYED_RECIPE_READ = "get_recipe keyed by project"
ID_ONLY_RESOURCE_READ = "recipe or component version read keyed by id alone"

# The routes carrying <recipe_id> that have no route guard, each with the module and entry point whose
# read order stands in for the missing guard: a project-keyed recipe read must come first, so a caller
# from another project is refused before any read keyed by a bare recipe or version id can report
# whether that resource exists or what state it is in. The third element says whether the subject
# reads by a bare id at all, so deleting that read is visible too.
READ_ORDER_SUBJECTS = {
    "archive_recipe": (RECIPE_COMMAND_HANDLERS_PATH / "archive_recipe_command_handler.py", "handle", True),
    "create_recipe_version": (
        RECIPE_COMMAND_HANDLERS_PATH / "create_recipe_version_command_handler.py",
        "handle",
        True,
    ),
    "get_recipe": (HANDLER_PATH, "get_recipe", False),
}

FOREIGN_PROJECT_ID = "proj-a1111"
OWNING_PROJECT_ID = "proj-b2222"
FOREIGN_COMPONENT_ID = "comp-b2222"
FOREIGN_RECIPE_ID = "reci-b2222"
FOREIGN_RECIPE_VERSION_ID = "vers-b2222"

# Fixed refusal text for the guard stand-ins. It is deliberately not the production message and not
# derived from the request ids, so an assertion on it pins the propagation of whatever the guard
# raised rather than the test's own interpolation.
COMPONENT_GUARD_REFUSAL_MESSAGE = "Component is not in this project."
RECIPE_GUARD_REFUSAL_MESSAGE = "Recipe is not in this project."
RECIPE_VERSION_GUARD_REFUSAL_MESSAGE = "Recipe version is not in this recipe."


@dataclasses.dataclass(frozen=True)
class Route:
    name: str
    method: str
    path: str
    called_attributes: frozenset


def _route_path(decorator) -> str | None:
    if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
        return None
    if decorator.func.attr not in HTTP_METHODS or not isinstance(decorator.func.value, ast.Name):
        return None
    if decorator.func.value.id != RESOLVER_NAME or not decorator.args:
        return None
    first_argument = decorator.args[0]
    return first_argument.value if isinstance(first_argument, ast.Constant) else None


def _called_attributes(function: ast.FunctionDef) -> frozenset:
    return frozenset(
        node.func.attr
        for node in ast.walk(function)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    )


def _is_project_keyed(call: ast.Call) -> bool:
    if any(keyword.arg in PROJECT_ID_KEYWORDS for keyword in call.keywords):
        return True
    arguments = list(call.args) + [keyword.value for keyword in call.keywords]
    return any(name in ast.unparse(argument) for argument in arguments for name in PROJECT_ID_KEYWORDS)


def _recipe_read_label(call: ast.Call) -> str | None:
    if not isinstance(call.func, ast.Attribute):
        return None
    if call.func.attr == RECIPE_READ and _is_project_keyed(call):
        return PROJECT_KEYED_RECIPE_READ
    if call.func.attr.startswith(ID_ONLY_READ_PREFIXES) and not _is_project_keyed(call):
        return ID_ONLY_RESOURCE_READ
    return None


def _calls_in_evaluation_order(node: ast.AST) -> list[ast.Call]:
    """Calls under a node, each preceded by the calls in its own arguments.

    Branches are flattened in source order, so the result is every read one pass through the function
    can reach rather than the reads of a single branch.
    """

    calls: list[ast.Call] = []
    for child in ast.iter_child_nodes(node):
        calls.extend(_calls_in_evaluation_order(child))
    if isinstance(node, ast.Call):
        calls.append(node)
    return calls


def _called_name(call: ast.Call) -> str | None:
    """The name to step into: a plain call, or a method a class calls on itself."""

    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name):
        return call.func.attr if call.func.value.id == "self" else None
    return None


def _reads_of(function: ast.FunctionDef, functions: dict, visited: frozenset, label) -> list[str]:
    reads = []
    for call in _calls_in_evaluation_order(function):
        called_name = _called_name(call)
        if called_name in functions and called_name not in visited:
            reads.extend(_reads_of(functions[called_name], functions, visited | {called_name}, label))
            continue
        read = label(call)
        if read is not None:
            reads.append(read)
    return reads


def _functions_in(module: ast.Module) -> dict:
    """Every function an entry point in this module can step into, by name.

    Class methods are collected as well, so a service method reached as ``self.method(...)`` resolves.
    A module-level function wins a name clash, the way Python resolves the bare call.
    """

    methods = {
        child.name: child
        for node in module.body
        if isinstance(node, ast.ClassDef)
        for child in node.body
        if isinstance(child, ast.FunctionDef)
    }
    return methods | {node.name: node for node in module.body if isinstance(node, ast.FunctionDef)}


def _read_order(module_path: pathlib.Path, entry_point: str, label) -> list[str]:
    """Labelled reads an entry point performs, in order, stepping into the module's own helpers."""

    functions = _functions_in(ast.parse(module_path.read_text()))
    return _reads_of(functions[entry_point], functions, frozenset({entry_point}), label)


def _routes() -> list[Route]:
    tree = ast.parse(HANDLER_PATH.read_text())
    routes = []
    for function in ast.walk(tree):
        if not isinstance(function, ast.FunctionDef):
            continue
        for decorator in function.decorator_list:
            path = _route_path(decorator)
            if path is None:
                continue
            routes.append(
                Route(
                    name=function.name,
                    method=decorator.func.attr,
                    path=path,
                    called_attributes=_called_attributes(function),
                )
            )
    return routes


def _routes_calling(routes: list[Route], guard: str) -> list[str]:
    return sorted(route.name for route in routes if guard in route.called_attributes)


def test_the_handler_declares_the_route_totals_the_coverage_walks_account_for():
    """A route added or removed changes a total here, so it cannot slip past the two coverage walks."""

    # ARRANGE / ACT
    routes = _routes()

    # ASSERT
    assertpy.assert_that(routes).is_length(42)
    assertpy.assert_that([route for route in routes if "<component_id>" in route.path]).is_length(13)
    assertpy.assert_that([route for route in routes if "<recipe_id>" in route.path]).is_length(10)


def test_every_component_id_route_calls_the_component_project_guard():
    # ARRANGE
    routes = _routes()
    component_routes = [route for route in routes if "<component_id>" in route.path]

    # ACT
    guarded = sorted(route.name for route in component_routes if COMPONENT_GUARD in route.called_attributes)
    unguarded = sorted(route.name for route in component_routes if COMPONENT_GUARD not in route.called_attributes)

    # ASSERT
    assertpy.assert_that(component_routes).is_length(13)
    assertpy.assert_that(guarded).is_length(13)
    assertpy.assert_that(unguarded).is_empty()
    assertpy.assert_that(_routes_calling(routes, COMPONENT_GUARD)).is_length(13)
    assertpy.assert_that(_routes_calling(routes, COMPONENT_VERSION_GUARD)).is_length(2)


def test_every_recipe_id_route_is_scoped_by_project():
    # ARRANGE
    routes = _routes()
    recipe_routes = [route for route in routes if "<recipe_id>" in route.path]

    # ACT
    guarded = sorted(route.name for route in recipe_routes if RECIPE_GUARD in route.called_attributes)
    unguarded = sorted(route.name for route in recipe_routes if RECIPE_GUARD not in route.called_attributes)

    # ASSERT
    assertpy.assert_that(recipe_routes).is_length(10)
    assertpy.assert_that(guarded).is_length(7)
    assertpy.assert_that(unguarded).is_equal_to(sorted(READ_ORDER_SUBJECTS))
    assertpy.assert_that(_routes_calling(routes, RECIPE_GUARD)).is_length(8)
    assertpy.assert_that(_routes_calling(routes, RECIPE_VERSION_GUARD)).is_length(3)


@pytest.mark.parametrize("route_name,read_subject", sorted(READ_ORDER_SUBJECTS.items()))
def test_unguarded_recipe_id_route_reads_the_project_keyed_recipe_before_any_id_only_read(route_name, read_subject):
    # ARRANGE
    module_path, entry_point, reads_by_id_alone = read_subject

    # ACT
    reads = _read_order(module_path, entry_point, _recipe_read_label)

    # ASSERT
    assertpy.assert_that(reads).is_not_empty()
    assertpy.assert_that(reads[0]).is_equal_to(PROJECT_KEYED_RECIPE_READ)
    if reads_by_id_alone:
        assertpy.assert_that(reads).contains(ID_ONLY_RESOURCE_READ)
    else:
        assertpy.assert_that(reads).does_not_contain(ID_ONLY_RESOURCE_READ)


@pytest.fixture()
def component_owned_by_another_project(mocked_component_domain_query_service):
    def _require_component_in_project(project_id, component_id):
        if project_id.value != OWNING_PROJECT_ID:
            raise NotFoundError(COMPONENT_GUARD_REFUSAL_MESSAGE)

    mocked_component_domain_query_service.require_component_in_project.side_effect = _require_component_in_project

    return mocked_component_domain_query_service


@pytest.fixture()
def recipe_owned_by_another_project(mocked_recipe_domain_query_service):
    def _require_recipe_in_project(project_id, recipe_id):
        if project_id.value != OWNING_PROJECT_ID:
            raise NotFoundError(RECIPE_GUARD_REFUSAL_MESSAGE)

    mocked_recipe_domain_query_service.require_recipe_in_project.side_effect = _require_recipe_in_project

    return mocked_recipe_domain_query_service


@pytest.fixture()
def recipe_version_owned_by_another_recipe(mocked_recipe_versions_domain_query_service):
    def _require_recipe_version_in_recipe(recipe_id, version_id):
        if version_id.value == FOREIGN_RECIPE_VERSION_ID:
            raise NotFoundError(RECIPE_VERSION_GUARD_REFUSAL_MESSAGE)

    guard = mocked_recipe_versions_domain_query_service.require_recipe_version_in_recipe
    guard.side_effect = _require_recipe_version_in_recipe

    return mocked_recipe_versions_domain_query_service


COMPONENT_ROUTE_CASES = (
    ("get_component", {}),
    ("get_component_version", {"version_id": GlobalVariables.TEST_COMPONENT_VERSION_ID.value}),
    ("retire_component_version", {"version_id": GlobalVariables.TEST_COMPONENT_VERSION_ID.value}),
    ("share_component", {"project_ids": [OWNING_PROJECT_ID]}),
    (
        "get_component_version_test_execution_logs_url",
        {
            "version_id": GlobalVariables.TEST_COMPONENT_VERSION_ID.value,
            "execution_id": GlobalVariables.TEST_TEST_EXECUTION_ID.value,
            "instance_id": GlobalVariables.TEST_INSTANCE_ID.value,
        },
    ),
)


@pytest.mark.parametrize("route_fixture,route_arguments", COMPONENT_ROUTE_CASES)
def test_component_route_returns_404_when_component_belongs_to_another_project(
    request,
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    component_owned_by_another_project,
    route_fixture,
    route_arguments,
):
    # ARRANGE
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    call_route = request.getfixturevalue(route_fixture)

    # ACT
    status_code, body = call_route(
        project_id=FOREIGN_PROJECT_ID,
        component_id=FOREIGN_COMPONENT_ID,
        **route_arguments,
    )

    # ASSERT
    assertpy.assert_that(status_code).is_equal_to(404)
    assertpy.assert_that(body.get("message")).is_equal_to(COMPONENT_GUARD_REFUSAL_MESSAGE)
    guard_calls = component_owned_by_another_project.require_component_in_project.call_args_list
    assertpy.assert_that(guard_calls).is_length(1)
    assertpy.assert_that(guard_calls[0].kwargs["project_id"].value).is_equal_to(FOREIGN_PROJECT_ID)
    assertpy.assert_that(guard_calls[0].kwargs["component_id"].value).is_equal_to(FOREIGN_COMPONENT_ID)


@pytest.mark.parametrize("route_fixture,route_arguments", COMPONENT_ROUTE_CASES)
def test_component_route_does_not_return_404_when_component_belongs_to_the_path_project(
    request,
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    component_owned_by_another_project,
    route_fixture,
    route_arguments,
):
    # ARRANGE
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    call_route = request.getfixturevalue(route_fixture)

    # ACT
    status_code, _ = call_route(
        project_id=OWNING_PROJECT_ID,
        component_id=FOREIGN_COMPONENT_ID,
        **route_arguments,
    )

    # ASSERT
    assertpy.assert_that(status_code).is_not_equal_to(404)


def test_recipe_version_test_execution_logs_url_returns_404_when_recipe_belongs_to_another_project(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    recipe_owned_by_another_project,
    get_recipe_version_test_execution_logs_url,
):
    # ARRANGE
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    # ACT
    status_code, body = get_recipe_version_test_execution_logs_url(
        project_id=FOREIGN_PROJECT_ID,
        recipe_id=FOREIGN_RECIPE_ID,
        version_id=GlobalVariables.TEST_RECIPE_VERSION_ID.value,
        execution_id=GlobalVariables.TEST_RECIPE_VERSION_TEST_EXECUTION_ID.value,
    )

    # ASSERT
    assertpy.assert_that(status_code).is_equal_to(404)
    assertpy.assert_that(body.get("message")).is_equal_to(RECIPE_GUARD_REFUSAL_MESSAGE)
    guard_calls = recipe_owned_by_another_project.require_recipe_in_project.call_args_list
    assertpy.assert_that(guard_calls).is_length(1)
    assertpy.assert_that(guard_calls[0].kwargs["project_id"].value).is_equal_to(FOREIGN_PROJECT_ID)
    assertpy.assert_that(guard_calls[0].kwargs["recipe_id"].value).is_equal_to(FOREIGN_RECIPE_ID)


def test_recipe_version_test_execution_logs_url_does_not_return_404_when_recipe_belongs_to_the_path_project(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    recipe_owned_by_another_project,
    get_recipe_version_test_execution_logs_url,
):
    # ARRANGE
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    # ACT
    status_code, _ = get_recipe_version_test_execution_logs_url(
        project_id=OWNING_PROJECT_ID,
        recipe_id=FOREIGN_RECIPE_ID,
        version_id=GlobalVariables.TEST_RECIPE_VERSION_ID.value,
        execution_id=GlobalVariables.TEST_RECIPE_VERSION_TEST_EXECUTION_ID.value,
    )

    # ASSERT
    assertpy.assert_that(status_code).is_not_equal_to(404)


def test_update_recipe_version_returns_404_when_recipe_belongs_to_another_project(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    recipe_owned_by_another_project,
    update_recipe_version,
):
    # ARRANGE
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    # ACT
    status_code, body = update_recipe_version(
        project_id=FOREIGN_PROJECT_ID,
        recipe_id=FOREIGN_RECIPE_ID,
        recipe_version_id=FOREIGN_RECIPE_VERSION_ID,
        recipe_version_components_versions=[
            api_model.RecipeComponentVersion(
                componentId=GlobalVariables.TEST_COMPONENT_ID.value,
                componentName=GlobalVariables.TEST_COMPONENT_NAME.value,
                componentVersionId=GlobalVariables.TEST_COMPONENT_VERSION_ID.value,
                componentVersionName=GlobalVariables.TEST_COMPONENT_VERSION_NAME.value,
                componentVersionType=GlobalVariables.TEST_COMPONENT_VERSION_TYPE.value,
                order=1,
            )
        ],
    )

    # ASSERT
    assertpy.assert_that(status_code).is_equal_to(404)
    assertpy.assert_that(body.get("message")).is_equal_to(RECIPE_GUARD_REFUSAL_MESSAGE)
    guard_calls = recipe_owned_by_another_project.require_recipe_in_project.call_args_list
    assertpy.assert_that(guard_calls).is_length(1)
    assertpy.assert_that(guard_calls[0].kwargs["project_id"].value).is_equal_to(FOREIGN_PROJECT_ID)
    assertpy.assert_that(guard_calls[0].kwargs["recipe_id"].value).is_equal_to(FOREIGN_RECIPE_ID)


def test_release_recipe_version_returns_404_when_recipe_belongs_to_another_project(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    recipe_owned_by_another_project,
    release_recipe_version,
):
    # ARRANGE
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    # ACT
    status_code, body = release_recipe_version(
        project_id=FOREIGN_PROJECT_ID,
        recipe_id=FOREIGN_RECIPE_ID,
        version_id=FOREIGN_RECIPE_VERSION_ID,
    )

    # ASSERT
    assertpy.assert_that(status_code).is_equal_to(404)
    assertpy.assert_that(body.get("message")).is_equal_to(RECIPE_GUARD_REFUSAL_MESSAGE)
    guard_calls = recipe_owned_by_another_project.require_recipe_in_project.call_args_list
    assertpy.assert_that(guard_calls).is_length(1)
    assertpy.assert_that(guard_calls[0].kwargs["project_id"].value).is_equal_to(FOREIGN_PROJECT_ID)
    assertpy.assert_that(guard_calls[0].kwargs["recipe_id"].value).is_equal_to(FOREIGN_RECIPE_ID)


def test_create_pipeline_returns_404_when_the_body_recipe_belongs_to_another_project(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    recipe_owned_by_another_project,
    recipe_version_owned_by_another_recipe,
    create_pipeline,
):
    # ARRANGE
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    # ACT
    status_code, body = create_pipeline(
        project_id=FOREIGN_PROJECT_ID,
        recipe_id=FOREIGN_RECIPE_ID,
        recipe_version_id=FOREIGN_RECIPE_VERSION_ID,
    )

    # ASSERT
    # The path of this route carries no recipe id, so the guard can only have been handed the
    # recipeId the request body supplied.
    assertpy.assert_that(status_code).is_equal_to(404)
    assertpy.assert_that(body.get("message")).is_equal_to(RECIPE_GUARD_REFUSAL_MESSAGE)
    guard_calls = recipe_owned_by_another_project.require_recipe_in_project.call_args_list
    assertpy.assert_that(guard_calls).is_length(1)
    assertpy.assert_that(guard_calls[0].kwargs["project_id"].value).is_equal_to(FOREIGN_PROJECT_ID)
    assertpy.assert_that(guard_calls[0].kwargs["recipe_id"].value).is_equal_to(FOREIGN_RECIPE_ID)
    version_guard = recipe_version_owned_by_another_recipe.require_recipe_version_in_recipe
    assertpy.assert_that(version_guard.call_args_list).is_empty()


def test_create_pipeline_returns_404_when_the_body_recipe_version_belongs_to_another_recipe(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    recipe_owned_by_another_project,
    recipe_version_owned_by_another_recipe,
    create_pipeline,
):
    # ARRANGE
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    # ACT
    status_code, body = create_pipeline(
        project_id=OWNING_PROJECT_ID,
        recipe_id=FOREIGN_RECIPE_ID,
        recipe_version_id=FOREIGN_RECIPE_VERSION_ID,
    )

    # ASSERT
    # Both identifiers the version guard received came from the request body: this route's path
    # carries neither a recipe id nor a version id.
    assertpy.assert_that(status_code).is_equal_to(404)
    assertpy.assert_that(body.get("message")).is_equal_to(RECIPE_VERSION_GUARD_REFUSAL_MESSAGE)
    guard_calls = recipe_version_owned_by_another_recipe.require_recipe_version_in_recipe.call_args_list
    assertpy.assert_that(guard_calls).is_length(1)
    assertpy.assert_that(guard_calls[0].kwargs["recipe_id"].value).is_equal_to(FOREIGN_RECIPE_ID)
    assertpy.assert_that(guard_calls[0].kwargs["version_id"].value).is_equal_to(FOREIGN_RECIPE_VERSION_ID)
