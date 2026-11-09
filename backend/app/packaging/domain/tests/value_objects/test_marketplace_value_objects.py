import assertpy
import pytest

from app.packaging.domain.exceptions.domain_exception import DomainException
from app.packaging.domain.model.image.image_constants import ImageSource, SubscriptionOwnership
from app.packaging.domain.value_objects.image.image_name_value_object import from_str as name_from_str
from app.packaging.domain.value_objects.image.image_source_value_object import from_str as source_from_str
from app.packaging.domain.value_objects.image.marketplace_metadata_value_object import from_dict
from app.packaging.domain.value_objects.image.product_code_value_object import from_str as product_code_from_str


def test_image_source_should_have_correct_enum_values():
    # ARRANGE / ACT / ASSERT
    assertpy.assert_that(ImageSource.PIPELINE).is_equal_to("PIPELINE")
    assertpy.assert_that(ImageSource.EXISTING_AMI).is_equal_to("EXISTING_AMI")
    assertpy.assert_that(ImageSource.MARKETPLACE_PRODUCT).is_equal_to("MARKETPLACE_PRODUCT")


def test_subscription_ownership_should_have_correct_enum_values():
    # ARRANGE / ACT / ASSERT
    assertpy.assert_that(SubscriptionOwnership.VEW_MANAGED).is_equal_to("VEW_MANAGED")
    assertpy.assert_that(SubscriptionOwnership.EXTERNALLY_MANAGED).is_equal_to("EXTERNALLY_MANAGED")


def test_from_str_should_create_image_source_when_valid():
    # ARRANGE
    source_str = "EXISTING_AMI"

    # ACT
    vo = source_from_str(source_str)

    # ASSERT
    assertpy.assert_that(vo.value).is_equal_to(ImageSource.EXISTING_AMI)


def test_from_str_should_raise_when_image_source_invalid():
    # ARRANGE
    source_str = "INVALID"

    # ACT / ASSERT
    with pytest.raises(DomainException):
        source_from_str(source_str)


def test_from_str_should_create_image_name_when_valid():
    # ARRANGE
    name = "My AMI"

    # ACT
    vo = name_from_str(name)

    # ASSERT
    assertpy.assert_that(vo.value).is_equal_to("My AMI")


def test_from_str_should_raise_when_image_name_empty():
    # ARRANGE
    name = ""

    # ACT / ASSERT
    with pytest.raises(DomainException):
        name_from_str(name)


def test_from_str_should_raise_when_image_name_too_long():
    # ARRANGE
    name = "x" * 101

    # ACT / ASSERT
    with pytest.raises(DomainException):
        name_from_str(name)


def test_from_str_should_create_product_code_when_valid():
    # ARRANGE
    code = "abc123def456ghi"

    # ACT
    vo = product_code_from_str(code)

    # ASSERT
    assertpy.assert_that(vo.value).is_equal_to("abc123def456ghi")


def test_from_str_should_raise_when_product_code_empty():
    # ARRANGE
    code = ""

    # ACT / ASSERT
    with pytest.raises(DomainException):
        product_code_from_str(code)


def test_from_str_should_raise_when_product_code_invalid_format():
    # ARRANGE
    code = "INVALID-CODE!"

    # ACT
    with pytest.raises(DomainException, match="Invalid product code format") as exc_info:
        product_code_from_str(code)

    # ASSERT
    assertpy.assert_that(str(exc_info.value)).contains("Invalid product code format")


def test_from_str_should_raise_when_product_code_too_short():
    # ARRANGE
    code = "abc"

    # ACT
    with pytest.raises(DomainException, match="Invalid product code format") as exc_info:
        product_code_from_str(code)

    # ASSERT
    assertpy.assert_that(str(exc_info.value)).contains("Invalid product code format")


def test_from_dict_should_create_marketplace_metadata_when_valid(get_valid_marketplace_dict):
    # ARRANGE
    d = get_valid_marketplace_dict()

    # ACT
    meta = from_dict(d)

    # ASSERT
    assertpy.assert_that(meta.productCode).is_equal_to("abc123def456ghi")
    assertpy.assert_that(meta.subscriptionOwnership).is_equal_to("VEW_MANAGED")


def test_from_dict_should_raise_when_missing_product_code(get_valid_marketplace_dict):
    # ARRANGE
    d = get_valid_marketplace_dict()
    d.pop("productCode")

    # ACT / ASSERT
    with pytest.raises(DomainException):
        from_dict(d)


def test_from_dict_should_raise_when_invalid_product_code_format(get_valid_marketplace_dict):
    # ARRANGE
    d = get_valid_marketplace_dict()
    d["productCode"] = "INVALID-CODE!"

    # ACT
    with pytest.raises(DomainException, match="Invalid product code format") as exc_info:
        from_dict(d)

    # ASSERT
    assertpy.assert_that(str(exc_info.value)).contains("Invalid product code format")


def test_from_dict_should_raise_when_invalid_ownership(get_valid_marketplace_dict):
    # ARRANGE
    d = get_valid_marketplace_dict()
    d["subscriptionOwnership"] = "INVALID"

    # ACT / ASSERT
    with pytest.raises(DomainException):
        from_dict(d)


def test_from_dict_should_raise_when_empty_regional_ami_ids(get_valid_marketplace_dict):
    # ARRANGE
    d = get_valid_marketplace_dict()
    d["regionalAmiIds"] = {}

    # ACT / ASSERT
    with pytest.raises(DomainException):
        from_dict(d)


def test_from_dict_should_raise_when_invalid_license_arn_format(get_valid_marketplace_dict):
    # ARRANGE
    d = get_valid_marketplace_dict()
    d["licenseConfigurationArn"] = "not-a-valid-arn"

    # ACT
    with pytest.raises(DomainException, match="Invalid license configuration ARN") as exc_info:
        from_dict(d)

    # ASSERT
    assertpy.assert_that(str(exc_info.value)).contains("Invalid license configuration ARN")


def test_from_dict_should_accept_valid_license_arn(get_valid_marketplace_dict):
    # ARRANGE
    d = get_valid_marketplace_dict()
    d["licenseConfigurationArn"] = "arn:aws:license-manager:us-east-1:123456789012:license:l-abc123"

    # ACT
    meta = from_dict(d)

    # ASSERT
    assertpy.assert_that(meta.licenseConfigurationArn).is_equal_to(
        "arn:aws:license-manager:us-east-1:123456789012:license:l-abc123"
    )
