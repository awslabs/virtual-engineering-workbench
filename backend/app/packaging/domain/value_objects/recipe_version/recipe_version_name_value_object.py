import typing
from dataclasses import dataclass

import semver

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class RecipeVersionNameValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> RecipeVersionNameValueObject:
    if not value:
        raise domain_exception.DomainException("Recipe version name cannot be empty.")

    try:
        recipe_version_parsed = semver.parse(value)
        pre_release_version = recipe_version_parsed.get("prerelease", None)
        if (
            recipe_version_parsed.get("major") == 0
            and recipe_version_parsed.get("minor") == 0
            and recipe_version_parsed.get("patch") == 0
        ) or (
            pre_release_version and (not pre_release_version.startswith("rc.") or not pre_release_version[3:].isdigit())
        ):
            raise Exception(f"Invalid recipe version name: {value}.")
        return RecipeVersionNameValueObject(value=value)
    except Exception as e:
        raise domain_exception.DomainException(f"Invalid recipe version name: {value}.") from e
