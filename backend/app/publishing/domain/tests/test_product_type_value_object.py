import pytest

from app.publishing.domain.value_objects import product_type_value_object


@pytest.mark.parametrize(
    "given_product_type, expected_name",
    [
        ("VIRTUAL_TARGET", "virtual target"),
        ("virtual_target", "virtual target"),
        ("WORKBENCH", "workbench"),
        ("workbench", "workbench"),
    ],
)
def test_get_readable_value(given_product_type, expected_name):
    # ARRANGE
    product_type = product_type_value_object.from_str(given_product_type)
    # ACT
    product_type_name = product_type.get_readable_value()
    # ASSERT
    assert product_type_name == expected_name
