import assertpy
import pytest
from aws_lambda_powertools.event_handler.exceptions import NotFoundError

from app.packaging.domain.query_services import recipe_domain_query_service
from app.packaging.domain.value_objects.recipe import recipe_id_value_object
from app.packaging.domain.value_objects.shared import project_id_value_object


def test_require_recipe_in_project_should_pass_when_recipe_belongs_to_project(
    recipe_query_service_mock,
    get_test_project_id,
    get_test_recipe_id,
    mock_recipe_object,
):
    # ARRANGE
    recipe_domain_qry_srv = recipe_domain_query_service.RecipeDomainQueryService(
        recipe_qry_srv=recipe_query_service_mock,
    )
    recipe_query_service_mock.get_recipe.return_value = mock_recipe_object

    # ACT
    result = recipe_domain_qry_srv.require_recipe_in_project(
        project_id=project_id_value_object.from_str(get_test_project_id),
        recipe_id=recipe_id_value_object.from_str(get_test_recipe_id),
    )

    # ASSERT
    assertpy.assert_that(result).is_none()
    recipe_query_service_mock.get_recipe.assert_called_once_with(
        project_id=get_test_project_id, recipe_id=get_test_recipe_id
    )


def test_require_recipe_in_project_should_raise_when_recipe_does_not_belong_to_project(
    recipe_query_service_mock,
    get_test_project_id,
    get_test_recipe_id,
):
    # ARRANGE
    recipe_domain_qry_srv = recipe_domain_query_service.RecipeDomainQueryService(
        recipe_qry_srv=recipe_query_service_mock,
    )
    recipe_query_service_mock.get_recipe.return_value = None

    # ACT
    with pytest.raises(NotFoundError) as e:
        recipe_domain_qry_srv.require_recipe_in_project(
            project_id=project_id_value_object.from_str(get_test_project_id),
            recipe_id=recipe_id_value_object.from_str(get_test_recipe_id),
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to("Recipe reci-1234abcd not found in project proj-12345.")
