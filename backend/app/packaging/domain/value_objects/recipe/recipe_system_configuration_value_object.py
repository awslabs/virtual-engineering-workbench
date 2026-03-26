import typing
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.recipe import recipe


@dataclass(frozen=True)
class RecipeSystemConfigurationValueObject:
    platform: str
    architecture: str
    os_version: str


def _handle_empty_errors(
    platform: typing.Optional[str],
    architecture: typing.Optional[str],
    os_version: typing.Optional[str],
):
    if not platform:
        raise domain_exception.DomainException("Recipe platform cannot be empty.")
    if not architecture:
        raise domain_exception.DomainException("Recipe architecture cannot be empty.")
    if not os_version:
        raise domain_exception.DomainException("Recipe OS version cannot be empty.")


def _handle_not_in_a_list_errors(
    platform: typing.Optional[str],
    architecture: typing.Optional[str],
    os_version: typing.Optional[str],
):
    if platform not in recipe.RecipePlatform.list():
        raise domain_exception.DomainException(f"Recipe platform should be in {recipe.RecipePlatform.list()}.")
    if architecture not in recipe.RecipeArchitecture.list():
        raise domain_exception.DomainException(f"Recipe architecture should be in {recipe.RecipeArchitecture.list()}.")
    if os_version not in recipe.RecipeOsVersion.list():
        raise domain_exception.DomainException(f"Recipe OS version should be in {recipe.RecipeOsVersion.list()}.")


def _handle_platform_is_Linux(
    platform: typing.Optional[str],
    os_version: typing.Optional[str],
):
    if platform == recipe.RecipePlatform.Linux.value:
        if os_version in {
            recipe.RecipeOsVersion.Windows_2025.value,
        }:
            raise domain_exception.DomainException(
                f"Recipe platform {recipe.RecipePlatform.Linux.value} does "
                f"not support {recipe.RecipePlatform.Windows.value} OS versions."
            )


def _handle_platform_is_Windows(
    platform: typing.Optional[str],
    architecture: typing.Optional[str],
    os_version: typing.Optional[str],
):
    if platform == recipe.RecipePlatform.Windows.value:
        if recipe.RecipeArchitecture.Arm64.value == architecture:
            raise domain_exception.DomainException(
                f"Recipe platform {recipe.RecipePlatform.Windows.value} does not "
                f"support {recipe.RecipeArchitecture.Arm64.value} architecture."
            )
        if os_version in {
            recipe.RecipeOsVersion.Ubuntu_24.value,
        }:
            raise domain_exception.DomainException(
                f"Recipe platform {recipe.RecipePlatform.Windows.value} does "
                f"not support {recipe.RecipePlatform.Linux.value} OS versions."
            )


def from_attrs(
    platform: typing.Optional[str],
    architecture: typing.Optional[str],
    os_version: typing.Optional[str],
) -> RecipeSystemConfigurationValueObject:

    _handle_empty_errors(platform, architecture, os_version)
    _handle_not_in_a_list_errors(platform, architecture, os_version)
    _handle_platform_is_Linux(platform, os_version)
    _handle_platform_is_Windows(platform, architecture, os_version)

    return RecipeSystemConfigurationValueObject(platform=platform, architecture=architecture, os_version=os_version)
