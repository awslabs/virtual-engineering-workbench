import assertpy

from app.packaging.domain.model.component import component_version
from app.packaging.domain.query_services import component_version_domain_query_service
from app.packaging.domain.value_objects.component import (
    component_platform_value_object,
    component_supported_architecture_value_object,
    component_supported_os_version_value_object,
)
from app.packaging.domain.value_objects.component_version import component_version_status_value_object
from app.packaging.domain.value_objects.shared import project_id_value_object


def test_should_return_all_component_versions(
    component_query_service_mock,
    component_version_definition_service_mock,
    component_version_query_service_mock,
    get_test_architecture,
    get_test_component_id,
    get_test_component_version_with_specific_component_id_version_name_and_status,
    get_test_os_version,
    get_test_platform,
):
    # ARRANGE
    component_version_domain_qry_srv = component_version_domain_query_service.ComponentVersionDomainQueryService(
        component_qry_srv=component_query_service_mock,
        component_version_definition_srv=component_version_definition_service_mock,
        component_version_qry_srv=component_version_query_service_mock,
    )
    test_component_versions_released = [
        get_test_component_version_with_specific_component_id_version_name_and_status(
            component_id=get_test_component_id,
            version_name="1.0.0-rc.1",
            status=component_version.ComponentVersionStatus.Validated,
        ),
        get_test_component_version_with_specific_component_id_version_name_and_status(
            component_id=get_test_component_id,
            version_name="1.0.0",
            status=component_version.ComponentVersionStatus.Released,
        ),
        get_test_component_version_with_specific_component_id_version_name_and_status(
            component_id=get_test_component_id,
            version_name="2.0.0",
            status=component_version.ComponentVersionStatus.Released,
        ),
        get_test_component_version_with_specific_component_id_version_name_and_status(
            component_id="comp-1234defg", version_name="1.0.0", status=component_version.ComponentVersionStatus.Released
        ),
    ]
    test_component_versions_validated = [
        get_test_component_version_with_specific_component_id_version_name_and_status(
            component_id=get_test_component_id,
            version_name="1.0.0-rc.1",
            status=component_version.ComponentVersionStatus.Validated,
        ),
        get_test_component_version_with_specific_component_id_version_name_and_status(
            component_id=get_test_component_id,
            version_name="2.0.0-rc.1",
            status=component_version.ComponentVersionStatus.Validated,
        ),
        get_test_component_version_with_specific_component_id_version_name_and_status(
            component_id="comp-1234defg",
            version_name="1.0.0-rc.1",
            status=component_version.ComponentVersionStatus.Validated,
        ),
    ]
    component_version_query_service_mock.get_all_components_versions.side_effect = [
        test_component_versions_released,
        test_component_versions_validated,
    ]

    # ACT
    component_versions = component_version_domain_qry_srv.get_all_components_versions(
        architecture=component_supported_architecture_value_object.from_str(get_test_architecture),
        os=component_supported_os_version_value_object.from_str(get_test_os_version),
        platform=component_platform_value_object.from_str(get_test_platform),
        statuses=[
            component_version_status_value_object.from_str(component_version.ComponentVersionStatus.Released),
            component_version_status_value_object.from_str(component_version.ComponentVersionStatus.Validated),
        ],
    )

    # ASSERT
    assertpy.assert_that(component_versions).is_equal_to(
        test_component_versions_released + test_component_versions_validated
    )


def test_should_return_project_component_versions(
    component_query_service_mock,
    component_version_definition_service_mock,
    component_version_query_service_mock,
    get_test_architecture,
    get_test_component,
    get_test_component_id,
    get_test_component_version_with_specific_component_id_version_name_and_status,
    get_test_os_version,
    get_test_platform,
    get_test_project_id,
):
    # ARRANGE
    component_version_domain_qry_srv = component_version_domain_query_service.ComponentVersionDomainQueryService(
        component_qry_srv=component_query_service_mock,
        component_version_definition_srv=component_version_definition_service_mock,
        component_version_qry_srv=component_version_query_service_mock,
    )
    test_component_versions = [
        get_test_component_version_with_specific_component_id_version_name_and_status(
            component_id=get_test_component_id,
            version_name="1.0.0",
            status=component_version.ComponentVersionStatus.Released,
        ),
        get_test_component_version_with_specific_component_id_version_name_and_status(
            component_id=get_test_component_id,
            version_name="2.0.0",
            status=component_version.ComponentVersionStatus.Released,
        ),
        get_test_component_version_with_specific_component_id_version_name_and_status(
            component_id="comp-1234defg", version_name="1.0.0", status=component_version.ComponentVersionStatus.Released
        ),
    ]
    component_query_service_mock.get_components.return_value = [get_test_component]
    component_version_query_service_mock.get_all_components_versions.return_value = test_component_versions

    # ACT
    component_versions = component_version_domain_qry_srv.get_all_components_versions(
        architecture=component_supported_architecture_value_object.from_str(get_test_architecture),
        os=component_supported_os_version_value_object.from_str(get_test_os_version),
        platform=component_platform_value_object.from_str(get_test_platform),
        statuses=[component_version_status_value_object.from_str(component_version.ComponentVersionStatus.Released)],
        project_id=project_id_value_object.from_str(get_test_project_id),
    )

    # ASSERT
    assertpy.assert_that(component_versions).is_equal_to(
        [
            get_test_component_version_with_specific_component_id_version_name_and_status(
                component_id=get_test_component_id,
                version_name="1.0.0",
                status=component_version.ComponentVersionStatus.Released,
            ),
            get_test_component_version_with_specific_component_id_version_name_and_status(
                component_id=get_test_component_id,
                version_name="2.0.0",
                status=component_version.ComponentVersionStatus.Released,
            ),
        ]
    )
