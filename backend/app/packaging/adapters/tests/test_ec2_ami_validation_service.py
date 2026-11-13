import assertpy
import pytest

from app.packaging.adapters.exceptions.adapter_exception import AdapterException
from app.packaging.adapters.tests.conftest import GlobalVariables


def test_should_describe_image(mock_moto_calls, get_ami_validation_srv):
    # ARRANGE
    ami_id = GlobalVariables.TEST_AMI_ID.value

    # ACT
    result = get_ami_validation_srv.describe_image(ami_id)

    # ASSERT
    mock_moto_calls["AssumeRole"].assert_called_once()
    mock_moto_calls["DescribeImages"].assert_called_once_with(ImageIds=[ami_id])
    assertpy.assert_that(result.amiId).is_equal_to(ami_id)
    assertpy.assert_that(result.state).is_equal_to("available")
    assertpy.assert_that(result.ownerId).is_equal_to(GlobalVariables.TEST_IMAGE_OWNER_ID.value)


def test_should_raise_when_describe_image_not_found(mock_moto_calls, get_ami_validation_srv):
    # ARRANGE
    mock_moto_calls["DescribeImages"].return_value = {"Images": []}

    # ACT / ASSERT
    with pytest.raises(AdapterException):
        get_ami_validation_srv.describe_image("ami-notfound")


def test_should_describe_marketplace_image(mock_moto_calls, get_ami_validation_srv):
    # ARRANGE
    ami_id = GlobalVariables.TEST_AMI_ID.value

    # ACT
    result = get_ami_validation_srv.describe_marketplace_image(ami_id)

    # ASSERT
    mock_moto_calls["DescribeImages"].assert_called_once_with(ImageIds=[ami_id])
    assertpy.assert_that(result.amiId).is_equal_to(ami_id)


def test_should_raise_when_describe_marketplace_image_not_found(mock_moto_calls, get_ami_validation_srv):
    # ARRANGE
    mock_moto_calls["DescribeImages"].return_value = {"Images": []}

    # ACT / ASSERT
    with pytest.raises(AdapterException):
        get_ami_validation_srv.describe_marketplace_image("ami-notfound")


def test_should_validate_marketplace_product_code_when_match(mock_moto_calls, get_ami_validation_srv):
    # ARRANGE
    ami_id = GlobalVariables.TEST_AMI_ID.value
    product_code = GlobalVariables.TEST_MARKETPLACE_PRODUCT_CODE.value

    # ACT
    result = get_ami_validation_srv.validate_marketplace_product_code(ami_id, product_code)

    # ASSERT
    assertpy.assert_that(result).is_true()


def test_should_validate_marketplace_product_code_when_mismatch(mock_moto_calls, get_ami_validation_srv):
    # ARRANGE
    ami_id = GlobalVariables.TEST_AMI_ID.value

    # ACT
    result = get_ami_validation_srv.validate_marketplace_product_code(ami_id, "differentcode123")

    # ASSERT
    assertpy.assert_that(result).is_false()


def test_should_validate_marketplace_product_code_with_pydantic_parsing(mock_moto_calls, get_ami_validation_srv):
    product_code = GlobalVariables.TEST_MARKETPLACE_PRODUCT_CODE.value
    ami_id = GlobalVariables.TEST_AMI_ID.value
    result = get_ami_validation_srv.validate_marketplace_product_code(ami_id, product_code)
    assertpy.assert_that(result).is_true()
