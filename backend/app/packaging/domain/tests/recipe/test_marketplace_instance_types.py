import assertpy
import pytest

from app.packaging.domain.exceptions.domain_exception import DomainException
from app.packaging.domain.model.recipe import marketplace_instance_types

PRODUCT_ID = "prod-ib2w5aw4ynhey"
# Excerpt of the live Ubuntu 24.04 offer: no m8i.2xlarge, but m8i.8xlarge and older 2xlarge families.
UBUNTU_OFFER = [
    "c7i.2xlarge",
    "m6i.2xlarge",
    "m7a.2xlarge",
    "m7i-flex.2xlarge",
    "m7i.2xlarge",
    "m8i.8xlarge",
    "t3.2xlarge",
    "m7g.2xlarge",
    "t4g.medium",
]


@pytest.mark.parametrize(
    "preferred,supported,expected",
    (
        ("m8i.2xlarge", None, "m8i.2xlarge"),  # no restriction known
        ("m8i.2xlarge", [], "m8i.2xlarge"),
        ("m8i.8xlarge", UBUNTU_OFFER, "m8i.8xlarge"),  # allowed as is
        ("m8i.2xlarge", UBUNTU_OFFER, "m7i.2xlarge"),  # same family and options, newest generation
        ("m8g.2xlarge", UBUNTU_OFFER, "m7g.2xlarge"),  # Graviton stays Graviton
        ("c8i.2xlarge", ["m7i.2xlarge", "c6i.2xlarge"], "c6i.2xlarge"),  # same family before newer generation
        ("m8i.2xlarge", ["t3.2xlarge", "m7a.2xlarge"], "m7a.2xlarge"),  # same family before same options
    ),
)
def test_choose_instance_type(preferred, supported, expected):
    assertpy.assert_that(marketplace_instance_types.choose_instance_type(preferred, supported, PRODUCT_ID)).is_equal_to(
        expected
    )


def test_choose_instance_type_fails_without_a_same_size_alternative():
    with pytest.raises(DomainException, match="does not support instance type m8i.24xlarge"):
        marketplace_instance_types.choose_instance_type("m8i.24xlarge", UBUNTU_OFFER, PRODUCT_ID)


def test_check_supported_accepts_supported_or_unrestricted_types():
    marketplace_instance_types.check_supported(["m7i.2xlarge", "t3.2xlarge"], UBUNTU_OFFER, PRODUCT_ID)
    marketplace_instance_types.check_supported(["m8i.2xlarge"], None, PRODUCT_ID)


def test_check_supported_names_the_unsupported_types_and_alternatives():
    with pytest.raises(DomainException) as e:
        marketplace_instance_types.check_supported(["m8i.2xlarge", "m7i.2xlarge"], UBUNTU_OFFER, PRODUCT_ID)

    assertpy.assert_that(str(e.value)).contains("does not support instance type(s) m8i.2xlarge.")
    assertpy.assert_that(str(e.value)).contains("Supported alternatives: m7i.2xlarge.")
