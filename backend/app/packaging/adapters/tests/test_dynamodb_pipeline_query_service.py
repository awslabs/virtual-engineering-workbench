import assertpy

from app.packaging.adapters.tests.conftest import GlobalVariables
from app.packaging.domain.model.pipeline import pipeline


def fill_db_with_pipelines(backend_app_table, pipelines: list[pipeline.Pipeline], uow_mock):
    with uow_mock:
        for pipe in pipelines:
            uow_mock.get_repository(repo_key=pipeline.PipelinePrimaryKey, repo_type=pipeline.Pipeline).add(pipe)
        uow_mock.commit()


def test_get_pipelines(
    mock_dynamodb, get_mock_pipeline, backend_app_table, get_dynamodb_pipeline_query_service, uow_mock
):
    # ARRANGE
    query_service = get_dynamodb_pipeline_query_service
    fill_db_with_pipelines(
        backend_app_table,
        [
            get_mock_pipeline(project_id="proj-1", pipeline_id="reci-1"),
            get_mock_pipeline(project_id="proj-1", pipeline_id="reci-2"),
            get_mock_pipeline(project_id="proj-2", pipeline_id="reci-3"),
            get_mock_pipeline(project_id="proj-2", pipeline_id="reci-4"),
        ],
        uow_mock,
    )

    # ACT
    pipelines_proj_1 = query_service.get_pipelines(project_id="proj-1")
    pipelines_proj_2 = query_service.get_pipelines(project_id="proj-2")
    pipelines_proj_3 = query_service.get_pipelines(project_id="proj-3")

    # ASSERT
    assertpy.assert_that(pipelines_proj_1).is_not_none()
    assertpy.assert_that(pipelines_proj_2).is_not_none()
    assertpy.assert_that(pipelines_proj_3).is_not_none()
    assertpy.assert_that(len(pipelines_proj_1)).is_equal_to(2)
    assertpy.assert_that(len(pipelines_proj_2)).is_equal_to(2)
    assertpy.assert_that(len(pipelines_proj_3)).is_equal_to(0)


def test_get_pipeline(
    mock_dynamodb, get_mock_pipeline, backend_app_table, get_dynamodb_pipeline_query_service, uow_mock
):
    # ARRANGE
    query_service = get_dynamodb_pipeline_query_service
    fill_db_with_pipelines(backend_app_table, [get_mock_pipeline()], uow_mock)

    # ACT
    pipeline_entity = query_service.get_pipeline(
        project_id=GlobalVariables.TEST_PROJECT_ID.value, pipeline_id=GlobalVariables.TEST_PIPELINE_ID.value
    )

    # ASSERT
    assertpy.assert_that(pipeline_entity).is_not_none()
    assertpy.assert_that(pipeline_entity).is_equal_to(get_mock_pipeline())


def test_get_pipeline_returns_none_when_not_found(
    mock_dynamodb, backend_app_table, get_dynamodb_pipeline_query_service
):
    # ARRANGE
    query_service = get_dynamodb_pipeline_query_service

    # ACT
    pipeline_entity = query_service.get_pipeline(
        project_id=GlobalVariables.TEST_PROJECT_ID.value, pipeline_id=GlobalVariables.TEST_PIPELINE_ID.value
    )

    # ASSERT
    assertpy.assert_that(pipeline_entity).is_equal_to(None)


def test_get_pipeline_by_pipeline_id(
    mock_dynamodb, get_mock_pipeline, backend_app_table, get_dynamodb_pipeline_query_service, uow_mock
):
    # ARRANGE
    query_service = get_dynamodb_pipeline_query_service
    fill_db_with_pipelines(backend_app_table, [get_mock_pipeline()], uow_mock)

    # ACT
    pipeline_entity = query_service.get_pipeline_by_pipeline_id(pipeline_id=GlobalVariables.TEST_PIPELINE_ID.value)

    # ASSERT
    assertpy.assert_that(pipeline_entity).is_not_none()
    assertpy.assert_that(pipeline_entity).is_equal_to(get_mock_pipeline())


def test_get_pipeline_by_pipeline_id_returns_none_when_not_found(
    mock_dynamodb, backend_app_table, get_dynamodb_pipeline_query_service
):
    # ARRANGE
    query_service = get_dynamodb_pipeline_query_service

    # ACT
    pipeline_entity = query_service.get_pipeline_by_pipeline_id(pipeline_id=GlobalVariables.TEST_PIPELINE_ID.value)

    # ASSERT
    assertpy.assert_that(pipeline_entity).is_equal_to(None)
