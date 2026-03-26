import assertpy
import pytest
from freezegun import freeze_time

from app.packaging.adapters.tests.conftest import GlobalVariables


def test_get_parameter_value(get_mock_parameter, get_parameter_srv, mock_ssm_client):
    # ARRANGE & ACT
    get_mock_parameter()
    param = get_parameter_srv.get_parameter_value(parameter_name=GlobalVariables.TEST_PARAMETER_NAME.value)
    # ASSERT
    assertpy.assert_that(param).is_not_none()
    assertpy.assert_that(param).is_equal_to(GlobalVariables.TEST_PARAMETER_VALUE.value)


def test_get_parameter_value_not_found(get_parameter_srv, mock_ssm_client):
    # ARRANGE & ACT
    with pytest.raises(mock_ssm_client.exceptions.ParameterNotFound) as excinfo:
        get_parameter_srv.get_parameter_value(parameter_name=GlobalVariables.TEST_PARAMETER_NAME.value)

    # ASSERT
    assertpy.assert_that(str(excinfo.value)).contains("ParameterNotFound")


def test_get_parameter_value_from_path_with_encryption(get_mock_parameter, get_parameter_srv, mock_ssm_client):
    # ARRANGE & ACT
    get_mock_parameter()
    param = get_parameter_srv.get_parameter_value_from_path_with_decryption(
        parameter_path=GlobalVariables.TEST_PARAMETER_NAME.value,
    )
    # ASSERT
    assertpy.assert_that(param).is_not_none()
    assertpy.assert_that(param).is_equal_to(GlobalVariables.TEST_PARAMETER_VALUE.value)


def test_get_parameter_value_from_path_with_encryption_not_found(get_parameter_srv, mock_ssm_client):
    # ARRANGE & ACT
    with pytest.raises(mock_ssm_client.exceptions.ParameterNotFound) as excinfo:
        get_parameter_srv.get_parameter_value_from_path_with_decryption(
            parameter_path=GlobalVariables.TEST_PARAMETER_NAME.value,
        )
    # ASSERT
    assertpy.assert_that(str(excinfo.value)).contains("ParameterNotFound")


@freeze_time("2023-10-13T00:00:00+00:00")
def test_create_parameter(get_mock_parameter, get_parameter_srv, mock_ssm_client):
    # ARRANGE & ACT
    param = get_mock_parameter()
    # ASSERT
    assertpy.assert_that(param).is_not_none()
    assertpy.assert_that(param.get("Version")).is_equal_to(1)


def test_delete_parameter(get_mock_parameter, get_parameter_srv, mock_ssm_client):
    # ARRANGE & ACT
    get_mock_parameter()
    param = get_parameter_srv.delete(
        parameter_name=GlobalVariables.TEST_PARAMETER_NAME.value,
    )
    # ASSERT
    assertpy.assert_that(param).is_none()


def delete_parameter_by_path(get_mock_parameter, get_parameter_srv, mock_ssm_client):
    # ARRANGE
    get_mock_parameter()
    # ACT
    param = get_parameter_srv.delete_by_path(
        parameter_path=GlobalVariables.TEST_PARAMETER_NAME.value,
    )
    # ASSERT
    assertpy.assert_that(param).is_none()
