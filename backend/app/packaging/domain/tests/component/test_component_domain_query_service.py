import assertpy
import pytest
from aws_lambda_powertools.event_handler.exceptions import NotFoundError

from app.packaging.domain.query_services import component_domain_query_service
from app.packaging.domain.value_objects.component import component_id_value_object
from app.packaging.domain.value_objects.shared import project_id_value_object


def test_require_component_in_project_should_pass_when_component_is_associated(
    component_query_service_mock,
    get_test_component_id,
    get_test_project_id,
):
    # ARRANGE
    component_domain_qry_srv = component_domain_query_service.ComponentDomainQueryService(
        component_qry_srv=component_query_service_mock,
    )
    component_query_service_mock.is_component_in_project.return_value = True

    # ACT
    result = component_domain_qry_srv.require_component_in_project(
        project_id=project_id_value_object.from_str(get_test_project_id),
        component_id=component_id_value_object.from_str(get_test_component_id),
    )

    # ASSERT
    assertpy.assert_that(result).is_none()
    component_query_service_mock.is_component_in_project.assert_called_once_with(
        project_id=get_test_project_id, component_id=get_test_component_id
    )


def test_require_component_in_project_should_raise_when_component_is_not_associated(
    component_query_service_mock,
    get_test_component_id,
    get_test_project_id,
):
    # ARRANGE
    component_domain_qry_srv = component_domain_query_service.ComponentDomainQueryService(
        component_qry_srv=component_query_service_mock,
    )
    component_query_service_mock.is_component_in_project.return_value = False

    # ACT
    with pytest.raises(NotFoundError) as e:
        component_domain_qry_srv.require_component_in_project(
            project_id=project_id_value_object.from_str(get_test_project_id),
            component_id=component_id_value_object.from_str(get_test_component_id),
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to("Component comp-1234abcd not found in project proj-12345.")
