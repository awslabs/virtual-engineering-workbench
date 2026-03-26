import pytest

from app.publishing.domain.value_objects import template_name_value_object


@pytest.mark.parametrize(
    "template_name, expected_file_name",
    [
        ("template/workbench-template.yml", "workbench-template.yml"),
        ("t1/t2/virtual-target-template.yml", "virtual-target-template.yml"),
        ("virtual-target-template.yml", "virtual-target-template.yml"),
    ],
)
def test_get_filename(template_name, expected_file_name):
    # ARRANGE
    template = template_name_value_object.from_str(template_name)
    # ACT
    file_name = template.get_filename()
    # ASSERT
    assert file_name == expected_file_name
