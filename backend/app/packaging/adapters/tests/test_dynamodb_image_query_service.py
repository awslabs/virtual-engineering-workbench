import assertpy

from app.packaging.adapters.tests.conftest import GlobalVariables
from app.packaging.domain.model.image import image


def fill_db_with_images(backend_app_table, images: list[image.Image], uow_mock):
    with uow_mock:
        for imag in images:
            uow_mock.get_repository(repo_key=image.ImagePrimaryKey, repo_type=image.Image).add(imag)
        uow_mock.commit()


def test_get_images(mock_dynamodb, get_mock_image, backend_app_table, get_dynamodb_image_query_service, uow_mock):
    # ARRANGE
    query_service = get_dynamodb_image_query_service
    fill_db_with_images(
        backend_app_table,
        [
            get_mock_image(project_id="proj-1", image_id="image-1"),
            get_mock_image(project_id="proj-1", image_id="image-2"),
            get_mock_image(project_id="proj-2", image_id="image-3"),
            get_mock_image(project_id="proj-2", image_id="image-4"),
        ],
        uow_mock,
    )

    # ACT
    images_proj_1 = query_service.get_images(project_id="proj-1")
    images_proj_2 = query_service.get_images(project_id="proj-2")
    images_proj_3 = query_service.get_images(project_id="proj-3")

    # ASSERT
    assertpy.assert_that(images_proj_1).is_not_none()
    assertpy.assert_that(images_proj_2).is_not_none()
    assertpy.assert_that(images_proj_3).is_not_none()
    assertpy.assert_that(len(images_proj_1)).is_equal_to(2)
    assertpy.assert_that(len(images_proj_2)).is_equal_to(2)
    assertpy.assert_that(len(images_proj_3)).is_equal_to(0)


def test_get_images_by_recipe_id_and_version_name(
    mock_dynamodb, get_mock_image, backend_app_table, get_dynamodb_image_query_service, uow_mock
):
    # ARRANGE
    query_service = get_dynamodb_image_query_service
    fill_db_with_images(
        backend_app_table,
        [
            get_mock_image(project_id="proj-1", image_id="image-1", recipe_id="reci-1", recipe_version_name="1.0.0"),
            get_mock_image(project_id="proj-1", image_id="image-2", recipe_id="reci-1", recipe_version_name="1.0.0"),
            get_mock_image(project_id="proj-2", image_id="image-3", recipe_id="reci-2", recipe_version_name="1.0.0"),
            get_mock_image(project_id="proj-2", image_id="image-4", recipe_id="reci-2", recipe_version_name="2.0.0"),
        ],
        uow_mock,
    )

    # ACT
    images_reci_1_vers_1 = query_service.get_images_by_recipe_id_and_version_name(
        recipe_id="reci-1", recipe_version_name="1.0.0"
    )
    images_reci_2_vers_1 = query_service.get_images_by_recipe_id_and_version_name(
        recipe_id="reci-2", recipe_version_name="1.0.0"
    )
    images_reci_2_vers_2 = query_service.get_images_by_recipe_id_and_version_name(
        recipe_id="reci-2", recipe_version_name="2.0.0"
    )
    images_reci_3_vers_1 = query_service.get_images_by_recipe_id_and_version_name(
        recipe_id="reci-3", recipe_version_name="1.0.0"
    )

    # ASSERT
    assertpy.assert_that(images_reci_1_vers_1).is_not_none()
    assertpy.assert_that(images_reci_2_vers_1).is_not_none()
    assertpy.assert_that(images_reci_2_vers_2).is_not_none()
    assertpy.assert_that(images_reci_3_vers_1).is_not_none()
    assertpy.assert_that(len(images_reci_1_vers_1)).is_equal_to(2)
    assertpy.assert_that(len(images_reci_2_vers_1)).is_equal_to(1)
    assertpy.assert_that(len(images_reci_2_vers_2)).is_equal_to(1)
    assertpy.assert_that(len(images_reci_3_vers_1)).is_equal_to(0)


def test_get_image(mock_dynamodb, get_mock_image, backend_app_table, get_dynamodb_image_query_service, uow_mock):
    # ARRANGE
    query_service = get_dynamodb_image_query_service
    fill_db_with_images(backend_app_table, [get_mock_image()], uow_mock)

    # ACT
    image_entity = query_service.get_image(
        project_id=GlobalVariables.TEST_PROJECT_ID.value, image_id=GlobalVariables.TEST_IMAGE_ID.value
    )

    # ASSERT
    assertpy.assert_that(image_entity).is_not_none()
    assertpy.assert_that(image_entity).is_equal_to(get_mock_image())


def test_get_image_returns_none_when_not_found(mock_dynamodb, backend_app_table, get_dynamodb_image_query_service):
    # ARRANGE
    query_service = get_dynamodb_image_query_service

    # ACT

    image_entity = query_service.get_image(
        project_id=GlobalVariables.TEST_PROJECT_ID.value, image_id=GlobalVariables.TEST_IMAGE_ID.value
    )

    # ASSERT
    assertpy.assert_that(image_entity).is_equal_to(None)


def test_get_image_by_image_build_version_arn(
    mock_dynamodb, get_mock_image, backend_app_table, get_dynamodb_image_query_service, uow_mock
):
    # ARRANGE
    query_service = get_dynamodb_image_query_service
    fill_db_with_images(backend_app_table, [get_mock_image()], uow_mock)

    # ACT
    image_entity = query_service.get_image_by_image_build_version_arn(
        image_build_version_arn=GlobalVariables.TEST_IMAGE_BUILD_VERSION_ARN.value
    )

    # ASSERT
    assertpy.assert_that(image_entity).is_not_none()
    assertpy.assert_that(image_entity).is_equal_to(get_mock_image())


def test_get_image_by_image_build_version_arn_returns_none_when_not_found(
    mock_dynamodb, backend_app_table, get_dynamodb_image_query_service
):
    # ARRANGE
    query_service = get_dynamodb_image_query_service

    # ACT

    image_entity = query_service.get_image_by_image_build_version_arn(
        image_build_version_arn=GlobalVariables.TEST_IMAGE_BUILD_VERSION_ARN.value
    )

    # ASSERT
    assertpy.assert_that(image_entity).is_equal_to(None)


def test_get_image_by_image_upstream_id_returns_image_when_exists(
    mock_dynamodb, get_mock_image, backend_app_table, get_dynamodb_image_query_service, uow_mock
):
    # ARRANGE
    query_service = get_dynamodb_image_query_service
    fill_db_with_images(backend_app_table, [get_mock_image()], uow_mock)

    # ACT
    image_entity = query_service.get_image_by_image_upstream_id(
        image_upstream_id=GlobalVariables.TEST_IMAGE_UPSTREAM_ID.value
    )

    # ASSERT
    assertpy.assert_that(image_entity).is_not_none()
    assertpy.assert_that(image_entity).is_equal_to(get_mock_image())


def test_get_image_by_image_upstream_id_returns_none_when_not_found(
    mock_dynamodb, backend_app_table, get_dynamodb_image_query_service
):
    # ARRANGE
    query_service = get_dynamodb_image_query_service

    # ACT

    image_entity = query_service.get_image_by_image_upstream_id(
        image_upstream_id=GlobalVariables.TEST_IMAGE_UPSTREAM_ID.value
    )

    # ASSERT
    assertpy.assert_that(image_entity).is_equal_to(None)


def test_get_images_excludes_given_status(
    mock_dynamodb, get_mock_image, backend_app_table, get_dynamodb_image_query_service, uow_mock
):
    # ARRANGE
    query_service = get_dynamodb_image_query_service
    fill_db_with_images(
        backend_app_table,
        [
            get_mock_image(project_id="proj-1", image_id="image-1"),
            get_mock_image(project_id="proj-1", image_id="image-2"),
            get_mock_image(project_id="proj-1", image_id="image-3", status=image.ImageStatus.Deleted),
            get_mock_image(project_id="proj-1", image_id="image-4", status=image.ImageStatus.Deleted),
        ],
        uow_mock,
    )

    # ACT
    images_proj_1 = query_service.get_images(project_id="proj-1", exclude_status=image.ImageStatus.Deleted)

    # ASSERT
    assertpy.assert_that(images_proj_1).is_length(2)
