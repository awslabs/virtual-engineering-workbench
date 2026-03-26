from unittest import mock

import assertpy
import pytest

from app.packaging.domain.exceptions.domain_exception import DomainException
from app.packaging.domain.value_objects.shared import version_release_type_value_object


@mock.patch(
    "app.packaging.domain.read_models.version_release_type.VersionReleaseType.list",
    mock.MagicMock(return_value=["MAJOR", "MINOR", "PATCH"]),
)
def test_version_release_type_value_object_should_parse_valid_release_type():
    # ARRANGE
    release_type = "MAJOR"

    # ACT
    value_object = version_release_type_value_object.from_str(release_type)

    # ASSERT
    assertpy.assert_that(value_object.value).is_equal_to(release_type)


@mock.patch(
    "app.packaging.domain.read_models.version_release_type.VersionReleaseType.list",
    mock.MagicMock(return_value=["MAJOR", "MINOR", "PATCH"]),
)
def test_version_release_type_value_object_should_handle_lowercase():
    # ARRANGE
    release_type = "major"

    # ACT
    value_object = version_release_type_value_object.from_str(release_type)

    # ASSERT
    assertpy.assert_that(value_object.value).is_equal_to("MAJOR")


@mock.patch(
    "app.packaging.domain.read_models.version_release_type.VersionReleaseType.list",
    mock.MagicMock(return_value=["MAJOR", "MINOR", "PATCH"]),
)
def test_version_release_type_value_object_should_handle_mixed_case():
    # ARRANGE
    release_type = "MiNoR"

    # ACT
    value_object = version_release_type_value_object.from_str(release_type)

    # ASSERT
    assertpy.assert_that(value_object.value).is_equal_to("MINOR")


@mock.patch(
    "app.packaging.domain.read_models.version_release_type.VersionReleaseType.list",
    mock.MagicMock(return_value=["MAJOR", "MINOR", "PATCH"]),
)
@pytest.mark.parametrize(
    "release_type,expected_exception_message",
    [
        (None, "Version release type cannot be empty."),
        ("", "Version release type cannot be empty."),
        ("   ", "Version release type cannot be empty."),
        ("INVALID", "Version release type should be in ['MAJOR', 'MINOR', 'PATCH']."),
        ("HOTFIX", "Version release type should be in ['MAJOR', 'MINOR', 'PATCH']."),
        (
            "major_release",
            "Version release type should be in ['MAJOR', 'MINOR', 'PATCH'].",
        ),
    ],
)
def test_version_release_type_value_object_should_raise_if_invalid(release_type, expected_exception_message):
    # ACT
    with pytest.raises(DomainException) as e:
        version_release_type_value_object.from_str(release_type)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(expected_exception_message)
