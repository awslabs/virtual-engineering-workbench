import assertpy

from app.packaging.adapters.repository import dynamo_entity_config
from app.packaging.adapters.tests.conftest import GlobalVariables
from app.packaging.domain.model.component import component, component_project_association


def fill_db_with_components(backend_app_table, components: list[component.Component]):
    for comp in components:
        backend_app_table.put_item(
            Item={
                "PK": f"{dynamo_entity_config.DBPrefix.Component}#{comp.componentId}",
                "SK": f"{dynamo_entity_config.DBPrefix.Component}#{comp.componentId}",
                "entity": dynamo_entity_config.DBPrefix.Component,
                **comp.dict(),
            }
        )


def fill_db_with_project_component_associations(
    fill_db_with_components,
    project_component_associations: list[component_project_association.ComponentProjectAssociation],
):
    for proj_comp_asso in project_component_associations:
        fill_db_with_components.put_item(
            Item={
                "PK": f"{dynamo_entity_config.DBPrefix.Component}#{proj_comp_asso.componentId}",
                "SK": f"{dynamo_entity_config.DBPrefix.Project}#{proj_comp_asso.projectId}",
                **proj_comp_asso.dict(),
            }
        )


def test_get_components(
    get_test_component, get_test_project_component_association, get_dynamodb_component_query_service, backend_app_table
):
    # ARRANGE
    query_service = get_dynamodb_component_query_service
    fill_db_with_components(backend_app_table, [get_test_component(), get_test_component(component_id="comp-2")])
    fill_db_with_project_component_associations(
        backend_app_table,
        [
            get_test_project_component_association(),
            get_test_project_component_association(component_id="comp-2"),
            get_test_project_component_association(component_id="comp-2", project_id="proj-2"),
            get_test_project_component_association(project_id="proj-2"),
        ],
    )

    # ACT
    components_proj_1 = query_service.get_components(project_id=GlobalVariables.TEST_PROJECT_ID.value)
    components_proj_2 = query_service.get_components(project_id="proj-2")
    components_proj_3 = query_service.get_components(project_id="proj-3")

    # ASSERT
    assertpy.assert_that(components_proj_1).is_not_none()
    assertpy.assert_that(components_proj_2).is_not_none()
    assertpy.assert_that(components_proj_3).is_not_none()
    assertpy.assert_that(len(components_proj_1)).is_equal_to(2)
    assertpy.assert_that(len(components_proj_2)).is_equal_to(2)
    assertpy.assert_that(len(components_proj_3)).is_equal_to(0)


def test_get_component(get_test_component, get_dynamodb_component_query_service, backend_app_table):
    # ARRANGE
    query_service = get_dynamodb_component_query_service
    fill_db_with_components(backend_app_table, [get_test_component()])

    # ACT
    result = query_service.get_component(component_id=GlobalVariables.TEST_COMPONENT_ID.value)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result).is_equal_to(get_test_component())


def test_get_component_returns_none_when_not_found(
    mock_dynamodb, get_dynamodb_component_query_service, backend_app_table
):
    # ARRANGE
    query_service = get_dynamodb_component_query_service

    # ACT
    component_entity = query_service.get_component(GlobalVariables.TEST_COMPONENT_ID.value)

    # ASSERT
    assertpy.assert_that(component_entity).is_equal_to(None)


def test_get_component_project_associations(
    get_test_component, get_test_project_component_association, get_dynamodb_component_query_service, backend_app_table
):
    # ARRANGE
    query_service = get_dynamodb_component_query_service
    fill_db_with_project_component_associations(
        backend_app_table,
        [
            get_test_project_component_association(component_id="comp-2"),
            get_test_project_component_association(project_id="proj-2"),
            get_test_project_component_association(project_id="proj-3"),
        ],
    )

    # ACT
    result = query_service.get_component_project_associations(component_id=GlobalVariables.TEST_COMPONENT_ID.value)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result).is_equal_to(
        [
            get_test_project_component_association(project_id="proj-2"),
            get_test_project_component_association(project_id="proj-3"),
        ]
    )


def test_get_component_project_association_empty(
    get_test_component, get_test_project_component_association, get_dynamodb_component_query_service, backend_app_table
):
    # ARRANGE
    query_service = get_dynamodb_component_query_service
    fill_db_with_project_component_associations(
        backend_app_table, [get_test_project_component_association(component_id="comp-2")]
    )

    # ACT
    result = query_service.get_component_project_associations(component_id=GlobalVariables.TEST_COMPONENT_ID.value)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result).is_empty()
