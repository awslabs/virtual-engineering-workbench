import assertpy
import pytest
from aws_lambda_powertools.event_handler.exceptions import NotFoundError

from app.packaging.domain.query_services import recipe_version_domain_query_service
from app.packaging.domain.value_objects.recipe import recipe_id_value_object
from app.packaging.domain.value_objects.recipe_version import recipe_version_id_value_object


def test_require_recipe_version_in_recipe_should_pass_when_version_belongs_to_recipe(
    recipe_query_service_mock,
    recipe_version_query_service_mock,
    get_test_recipe_id,
    get_test_recipe_version_id,
    mock_recipe_version_object,
):
    # ARRANGE
    recipe_version_domain_qry_srv = recipe_version_domain_query_service.RecipeVersionDomainQueryService(
        recipe_qry_srv=recipe_query_service_mock,
        recipe_version_qry_srv=recipe_version_query_service_mock,
    )
    recipe_version_query_service_mock.get_recipe_version.return_value = mock_recipe_version_object

    # ACT
    result = recipe_version_domain_qry_srv.require_recipe_version_in_recipe(
        recipe_id=recipe_id_value_object.from_str(get_test_recipe_id),
        version_id=recipe_version_id_value_object.from_str(get_test_recipe_version_id),
    )

    # ASSERT
    assertpy.assert_that(result).is_none()
    recipe_version_query_service_mock.get_recipe_version.assert_called_once_with(
        recipe_id=get_test_recipe_id, version_id=get_test_recipe_version_id
    )


def test_require_recipe_version_in_recipe_should_raise_when_version_does_not_belong_to_recipe(
    recipe_query_service_mock,
    recipe_version_query_service_mock,
    get_test_recipe_id,
    get_test_recipe_version_id,
):
    # ARRANGE
    recipe_version_domain_qry_srv = recipe_version_domain_query_service.RecipeVersionDomainQueryService(
        recipe_qry_srv=recipe_query_service_mock,
        recipe_version_qry_srv=recipe_version_query_service_mock,
    )
    recipe_version_query_service_mock.get_recipe_version.return_value = None

    # ACT
    with pytest.raises(NotFoundError) as e:
        recipe_version_domain_qry_srv.require_recipe_version_in_recipe(
            recipe_id=recipe_id_value_object.from_str(get_test_recipe_id),
            version_id=recipe_version_id_value_object.from_str(get_test_recipe_version_id),
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to("Version vers-1234abcd not found for recipe reci-1234abcd.")
