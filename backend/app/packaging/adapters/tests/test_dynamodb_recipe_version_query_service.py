import assertpy
import pytest

from app.packaging.adapters.repository import dynamo_entity_config
from app.packaging.adapters.tests.conftest import GlobalVariables
from app.packaging.domain.model.recipe import recipe_version, recipe_version_summary


def fill_db_with_versions(backend_app_table, recipe_versions: list[recipe_version.RecipeVersion]):
    for version in recipe_versions:
        backend_app_table.put_item(
            Item={
                "PK": f"{dynamo_entity_config.DBPrefix.Recipe}#{version.recipeId}",
                "SK": f"{dynamo_entity_config.DBPrefix.Version}#{version.recipeVersionId}",
                **version.model_dump(),
            }
        )


@pytest.mark.parametrize(
    "recipe_version_names, expected_recipe_version_name",
    [
        pytest.param(
            [
                "1.0.0-rc.1",
                "1.0.0-rc.2",
                "1.0.0-rc.3",
            ],
            "1.0.0-rc.3",
        ),
        pytest.param(
            [
                "1.0.0-rc.1",
                "1.0.5-rc.1",
                "1.0.13-rc.1",
            ],
            "1.0.13-rc.1",
        ),
        pytest.param(
            [
                "1.3.0-rc.1",
                "1.38.0-rc.1",
                "1.112.0-rc.1",
            ],
            "1.112.0-rc.1",
        ),
        pytest.param(
            [
                "1.0.0-rc.1",
                "1.1.0-rc.1",
                "2.0.1-rc.1",
            ],
            "2.0.1-rc.1",
        ),
        pytest.param(
            [
                "1.0.0",
                "1.0.1-rc.7",
                "1.1.0-rc.2",
            ],
            "1.1.0-rc.2",
        ),
        pytest.param(
            [
                "1.0.0",
                "1.5.8",
                "2.3.7",
            ],
            "2.3.7",
        ),
        pytest.param(
            [
                "1.2.0",
                "2.2.0",
                "3.2.0",
            ],
            "3.2.0",
        ),
    ],
)
def test_get_latest_recipe_version_name_return_latest_recipe_version_name(
    recipe_version_names,
    expected_recipe_version_name,
    mock_dynamodb,
    get_mock_recipe_version,
    backend_app_table,
    get_dynamodb_recipe_version_query_service,
):
    # ARRANGE
    query_service = get_dynamodb_recipe_version_query_service

    recipe_versions = [
        get_mock_recipe_version(
            recipe_version_name=recipe_version,
        )
        for recipe_version in recipe_version_names
    ]

    fill_db_with_versions(backend_app_table, recipe_versions)

    # ACT
    latest_version = query_service.get_latest_recipe_version_name(recipe_id=GlobalVariables.TEST_RECIPE_ID.value)

    # ASSERT
    assertpy.assert_that(latest_version).is_not_none()
    assertpy.assert_that(latest_version).is_equal_to(expected_recipe_version_name)


def test_get_latest_version_name_returns_none_when_no_version_found(
    mock_dynamodb, get_mock_recipe_version, get_dynamodb_recipe_version_query_service, backend_app_table
):
    # ARRANGE
    query_service = get_dynamodb_recipe_version_query_service

    # ACT
    latest_version = query_service.get_latest_recipe_version_name(recipe_id=GlobalVariables.TEST_RECIPE_ID.value)

    # ASSERT
    assertpy.assert_that(latest_version).is_none()


def test_get_recipe_versions(
    mock_dynamodb, get_mock_recipe_version, get_dynamodb_recipe_version_query_service, backend_app_table
):
    # ARRANGE
    query_service = get_dynamodb_recipe_version_query_service
    fill_db_with_versions(
        backend_app_table,
        [
            get_mock_recipe_version(),
            get_mock_recipe_version(recipe_id="reci-2"),
            get_mock_recipe_version(recipe_id="reci-2", recipe_version_id="version-2"),
            get_mock_recipe_version(recipe_version_id="version-2"),
        ],
    )

    # ACT
    recipe_versions_1 = query_service.get_recipe_versions(recipe_id=GlobalVariables.TEST_RECIPE_ID.value)
    recipe_versions_2 = query_service.get_recipe_versions(recipe_id="reci-2")
    recipe_versions_3 = query_service.get_recipe_versions(recipe_id="reci-3")

    # ASSERT
    assertpy.assert_that(recipe_versions_1).is_not_none()
    assertpy.assert_that(recipe_versions_2).is_not_none()
    assertpy.assert_that(recipe_versions_3).is_not_none()
    assertpy.assert_that(len(recipe_versions_1)).is_equal_to(2)
    assertpy.assert_that(len(recipe_versions_2)).is_equal_to(2)
    assertpy.assert_that(len(recipe_versions_3)).is_equal_to(0)


def test_get_recipe_version(
    mock_dynamodb,
    get_mock_recipe_version,
    get_dynamodb_recipe_version_query_service,
    backend_app_table,
):
    # ARRANGE
    query_service = get_dynamodb_recipe_version_query_service
    fill_db_with_versions(backend_app_table, [get_mock_recipe_version()])

    # ACT
    component = query_service.get_recipe_version(
        recipe_id=GlobalVariables.TEST_RECIPE_ID.value, version_id=GlobalVariables.TEST_RECIPE_VERSION_ID.value
    )

    # ASSERT
    assertpy.assert_that(component).is_not_none()
    assertpy.assert_that(component).is_equal_to(get_mock_recipe_version())


def test_get_recipe_version_returns_none_when_not_found(
    mock_dynamodb, backend_app_table, get_dynamodb_recipe_version_query_service
):
    # ARRANGE
    query_service = get_dynamodb_recipe_version_query_service

    # ACT
    recipe_version_entity = query_service.get_recipe_version(
        recipe_id=GlobalVariables.TEST_RECIPE_ID.value, version_id=GlobalVariables.TEST_RECIPE_VERSION_ID.value
    )

    # ASSERT
    assertpy.assert_that(recipe_version_entity).is_equal_to(None)


def test_get_all_recipe_versions(
    backend_app_table, mock_dynamodb, get_dynamodb_recipe_version_query_service, mock_ddb_component_repo
):
    # ARRANGE
    statuses = [
        recipe_version.RecipeVersionStatus.Validated,
        recipe_version.RecipeVersionStatus.Created,
        recipe_version.RecipeVersionStatus.Failed,
        recipe_version.RecipeVersionStatus.Creating,
        recipe_version.RecipeVersionStatus.Validated,
    ]
    for recipe_id in range(10):
        for version_id in range(5):
            with mock_ddb_component_repo:
                mock_ddb_component_repo.get_repository(
                    recipe_version.RecipeVersionPrimaryKey, recipe_version.RecipeVersion
                ).add(
                    recipe_version.RecipeVersion(
                        recipeId=f"reci-{recipe_id}",
                        recipeVersionId=f"vers-{recipe_id}-{version_id}",
                        recipeVersionName=f"1.{version_id}.0",
                        recipeName=GlobalVariables.TEST_RECIPE_NAME.value,
                        recipeVersionDescription=GlobalVariables.TEST_RECIPE_VERSION_DESCRIPTION.value,
                        recipeComponentsVersions=GlobalVariables.TEST_RECIPE_VERSION_COMPONENTS_VERSIONS.value,
                        recipeVersionVolumeSize=GlobalVariables.TEST_RECIPE_VERSION_VOLUME_SIZE.value,
                        status=statuses[version_id],
                        parentImageUpstreamId=GlobalVariables.TEST_IMAGE_UPSTREAM_ID.value,
                        parentImageId=GlobalVariables.TEST_RECIPE_VERSION_PARENT_IMAGE_ID.value,
                        recipeVersionArn=GlobalVariables.TEST_RECIPE_VERSION_ARN.value,
                        createDate=GlobalVariables.TEST_CREATE_DATE.value,
                        lastUpdateDate=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
                        createdBy=GlobalVariables.TEST_CREATED_BY.value,
                        lastUpdatedBy=GlobalVariables.TEST_LAST_UPDATED_BY.value,
                    )
                )
                mock_ddb_component_repo.commit()

    query_service = get_dynamodb_recipe_version_query_service

    # ACT
    all_recipe_versions_validated = query_service.get_all_recipe_versions(
        status=recipe_version.RecipeVersionStatus.Validated
    )
    all_recipe_versions_created = query_service.get_all_recipe_versions(
        status=recipe_version.RecipeVersionStatus.Created
    )
    all_recipe_versions_failed = query_service.get_all_recipe_versions(status=recipe_version.RecipeVersionStatus.Failed)
    all_recipe_versions_creating = query_service.get_all_recipe_versions(
        status=recipe_version.RecipeVersionStatus.Creating
    )

    # ASSERT
    assertpy.assert_that(all_recipe_versions_validated).is_not_none()
    assertpy.assert_that(all_recipe_versions_created).is_not_none()
    assertpy.assert_that(all_recipe_versions_failed).is_not_none()
    assertpy.assert_that(all_recipe_versions_creating).is_not_none()
    assertpy.assert_that(len(all_recipe_versions_validated)).is_equal_to(20)
    assertpy.assert_that(len(all_recipe_versions_created)).is_equal_to(10)
    assertpy.assert_that(len(all_recipe_versions_failed)).is_equal_to(10)
    assertpy.assert_that(len(all_recipe_versions_creating)).is_equal_to(10)
    counter = 0
    for elem in range(10):
        assertpy.assert_that(all_recipe_versions_validated[counter]).is_equal_to(
            recipe_version_summary.RecipeVersionSummary(
                recipeId=f"reci-{elem}",
                recipeVersionId=f"vers-{elem}-0",
                recipeVersionName="1.0.0",
                recipeName=GlobalVariables.TEST_RECIPE_NAME.value,
            )
        )
        counter += 1
        assertpy.assert_that(all_recipe_versions_validated[counter]).is_equal_to(
            recipe_version_summary.RecipeVersionSummary(
                recipeId=f"reci-{elem}",
                recipeVersionId=f"vers-{elem}-4",
                recipeVersionName="1.4.0",
                recipeName=GlobalVariables.TEST_RECIPE_NAME.value,
            )
        )
        counter += 1
