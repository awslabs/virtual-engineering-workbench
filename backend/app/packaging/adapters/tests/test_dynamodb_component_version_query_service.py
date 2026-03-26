import assertpy
import pytest

from app.packaging.adapters.repository import dynamo_entity_config
from app.packaging.adapters.tests.conftest import GlobalVariables
from app.packaging.domain.model.component import (
    component,
    component_version,
    component_version_summary,
)


def fill_db_with_versions(
    backend_app_component_table,
    component_versions: list[component_version.ComponentVersion],
):
    for version in component_versions:
        backend_app_component_table.put_item(
            Item={
                "PK": f"{dynamo_entity_config.DBPrefix.Component}#{version.componentId}",
                "SK": f"{dynamo_entity_config.DBPrefix.Version}#{version.componentVersionId}",
                **version.dict(),
            }
        )


@pytest.mark.parametrize(
    "component_version_names, expected_component_version_name",
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
def test_get_latest_component_version_name_return_latest_component_version_name(
    component_version_names,
    expected_component_version_name,
    mock_dynamodb,
    get_mock_component_version,
    backend_app_table,
    get_dynamodb_component_version_query_service,
):
    # ARRANGE
    query_service = get_dynamodb_component_version_query_service

    component_versions = [
        get_mock_component_version(
            component_version_name=component_version,
        )
        for component_version in component_version_names
    ]

    fill_db_with_versions(backend_app_table, component_versions)

    # ACT
    latest_version = query_service.get_latest_component_version_name(
        component_id=GlobalVariables.TEST_COMPONENT_ID.value
    )

    # ASSERT
    assertpy.assert_that(latest_version).is_not_none()
    assertpy.assert_that(latest_version).is_equal_to(expected_component_version_name)


def test_get_latest_version_name_returns_none_when_no_version_found(
    mock_dynamodb, backend_app_table, get_dynamodb_component_version_query_service
):
    # ARRANGE
    query_service = get_dynamodb_component_version_query_service

    # ACT
    latest_version = query_service.get_latest_component_version_name(
        component_id=GlobalVariables.TEST_COMPONENT_ID.value
    )

    # ASSERT
    assertpy.assert_that(latest_version).is_none()


def test_get_component_versions(
    mock_dynamodb,
    get_mock_component_version,
    backend_app_table,
    get_dynamodb_component_version_query_service,
):
    # ARRANGE
    query_service = get_dynamodb_component_version_query_service
    fill_db_with_versions(
        backend_app_table,
        [
            get_mock_component_version(),
            get_mock_component_version(component_id="comp-2"),
            get_mock_component_version(component_id="comp-2", component_version_id="version-2"),
            get_mock_component_version(component_version_id="version-2"),
        ],
    )

    # ACT
    component_versions_1 = query_service.get_component_versions(component_id="comp-1")
    component_versions_2 = query_service.get_component_versions(component_id="comp-2")
    component_versions_3 = query_service.get_component_versions(component_id="comp-3")

    # ASSERT
    assertpy.assert_that(component_versions_1).is_not_none()
    assertpy.assert_that(component_versions_2).is_not_none()
    assertpy.assert_that(component_versions_3).is_not_none()
    assertpy.assert_that(len(component_versions_1)).is_equal_to(2)
    assertpy.assert_that(len(component_versions_2)).is_equal_to(2)
    assertpy.assert_that(len(component_versions_3)).is_equal_to(0)


def test_get_component_version(
    mock_dynamodb,
    get_mock_component_version,
    backend_app_table,
    get_dynamodb_component_version_query_service,
):
    # ARRANGE
    query_service = get_dynamodb_component_version_query_service
    fill_db_with_versions(backend_app_table, [get_mock_component_version()])

    # ACT
    component = query_service.get_component_version(
        component_id=GlobalVariables.TEST_COMPONENT_ID.value,
        version_id=GlobalVariables.TEST_COMPONENT_VERSION_ID.value,
    )

    # ASSERT
    assertpy.assert_that(component).is_not_none()
    assertpy.assert_that(component).is_equal_to(get_mock_component_version())


def test_get_component_version_returns_none_when_not_found(
    mock_dynamodb, backend_app_table, get_dynamodb_component_version_query_service
):
    # ARRANGE
    query_service = get_dynamodb_component_version_query_service

    # ACT
    component_version_entity = query_service.get_component_version(
        component_id=GlobalVariables.TEST_COMPONENT_ID.value,
        version_id=GlobalVariables.TEST_COMPONENT_VERSION_ID.value,
    )

    # ASSERT
    assertpy.assert_that(component_version_entity).is_equal_to(None)


def test_get_all_component_versions(
    mock_ddb_component_repo,
    mock_dynamodb,
    backend_app_table,
    get_dynamodb_component_version_query_service,
    get_mock_component_version,
):
    # ARRANGE
    for component_id in range(10):
        for version_id in range(5):
            with mock_ddb_component_repo:
                mock_ddb_component_repo.get_repository(
                    component_version.ComponentVersionPrimaryKey,
                    component_version.ComponentVersion,
                ).add(
                    get_mock_component_version(
                        component_id=f"comp-{component_id}",
                        component_version_id=f"vers-{component_id}-{version_id}",
                        component_version_name=f"1.{version_id}.0",
                        component_supported_architectures=[component.ComponentSupportedArchitectures.Amd64.value],
                        component_supported_os_versions=[component.ComponentSupportedOsVersions.Ubuntu_24.value],
                        component_platform=component.ComponentPlatform.Linux.value,
                        status=component_version.ComponentVersionStatus.Released.value,
                    )
                )
                mock_ddb_component_repo.commit()

    query_service = get_dynamodb_component_version_query_service

    # ACT
    all_component_versions = query_service.get_all_components_versions(
        status=component_version.ComponentVersionStatus.Released,
        architecture=component.ComponentSupportedArchitectures.Amd64,
        os=component.ComponentSupportedOsVersions.Ubuntu_24,
        platform=component.ComponentPlatform.Linux,
    )

    # ASSERT
    assertpy.assert_that(all_component_versions).is_not_none()
    assertpy.assert_that(len(all_component_versions)).is_equal_to(50)
    counter = 0
    for elem in range(10):
        for version_id in range(5):
            assertpy.assert_that(all_component_versions[counter]).is_equal_to(
                component_version_summary.ComponentVersionSummary(
                    componentId=f"comp-{elem}",
                    componentVersionId=f"vers-{elem}-{version_id}",
                    componentVersionName=f"1.{version_id}.0",
                    componentName=GlobalVariables.TEST_COMPONENT_NAME.value,
                )
            )
            counter += 1


@pytest.mark.parametrize(
    "status, architecture, os, platform",
    [
        pytest.param(
            component_version.ComponentVersionStatus.Created,
            component.ComponentSupportedArchitectures.Amd64,
            component.ComponentSupportedOsVersions.Ubuntu_24,
            component.ComponentPlatform.Linux,
        ),
        pytest.param(
            component_version.ComponentVersionStatus.Released,
            component.ComponentSupportedArchitectures.Arm64,
            component.ComponentSupportedOsVersions.Ubuntu_24,
            component.ComponentPlatform.Linux,
        ),
        pytest.param(
            component_version.ComponentVersionStatus.Released,
            component.ComponentSupportedArchitectures.Amd64,
            component.ComponentSupportedOsVersions.Ubuntu_24,
            component.ComponentPlatform.Linux,
        ),
        pytest.param(
            component_version.ComponentVersionStatus.Released,
            component.ComponentSupportedArchitectures.Amd64,
            component.ComponentSupportedOsVersions.Ubuntu_24,
            component.ComponentPlatform.Windows,
        ),
    ],
)
def test_get_released_component_versions_should_return_empty_list(
    mock_dynamodb,
    backend_app_table,
    mock_ddb_component_repo,
    get_dynamodb_component_version_query_service,
    status,
    architecture,
    os,
    platform,
    get_mock_component_version,
):
    # ARRANGE
    for component_id in range(10):
        for version_id in range(5):
            with mock_ddb_component_repo:
                mock_ddb_component_repo.get_repository(
                    component_version.ComponentVersionPrimaryKey,
                    component_version.ComponentVersion,
                ).add(
                    get_mock_component_version(
                        component_id=f"comp-{component_id}",
                        component_version_id=f"vers-{component_id}-{version_id}",
                        component_version_name=f"1.{version_id}.0",
                    )
                )
                mock_ddb_component_repo.commit()

    query_service = get_dynamodb_component_version_query_service

    # ACT
    released_component_versions = query_service.get_all_components_versions(
        status=status,
        architecture=architecture,
        os=os,
        platform=platform,
    )

    # ASSERT
    assertpy.assert_that(released_component_versions).is_not_none()
    assertpy.assert_that(len(released_component_versions)).is_equal_to(0)
