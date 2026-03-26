import typing
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component


@dataclass(frozen=True)
class ComponentSystemConfigurationValueObject:
    platform: str
    supported_architectures: typing.List[str]
    supported_os_versions: typing.List[str]


def _handle_empty_errors(
    platform: typing.Optional[str],
    supported_architectures: typing.Optional[list[str]],
    supported_os_versions: typing.Optional[list[str]],
):
    if not platform:
        raise domain_exception.DomainException("Component platform cannot be empty.")
    if not supported_architectures:
        raise domain_exception.DomainException("Component supported architectures cannot be empty.")
    if not supported_os_versions:
        raise domain_exception.DomainException("Component supported OS versions cannot be empty.")


def _handle_not_in_a_list_errors(
    platform: typing.Optional[str],
    supported_architectures: typing.Optional[list[str]],
    supported_os_versions: typing.Optional[list[str]],
):
    if platform not in component.ComponentPlatform.list():
        raise domain_exception.DomainException(f"Component platform should be in {component.ComponentPlatform.list()}.")
    for supported_architecture in supported_architectures:
        if supported_architecture not in component.ComponentSupportedArchitectures.list():
            raise domain_exception.DomainException(
                f"Component supported architecture should be in {component.ComponentSupportedArchitectures.list()}."
            )
    for supported_os_version in supported_os_versions:
        if supported_os_version not in component.ComponentSupportedOsVersions.list():
            raise domain_exception.DomainException(
                f"Component supported OS version should be in {component.ComponentSupportedOsVersions.list()}."
            )


def _handle_platform_is_Linux(
    platform: typing.Optional[str],
    supported_os_versions: typing.Optional[list[str]],
):
    if platform == component.ComponentPlatform.Linux.value:
        if {
            component.ComponentSupportedOsVersions.Windows_2025.value,
        } & set(supported_os_versions):
            raise domain_exception.DomainException(
                f"Component platform {component.ComponentPlatform.Linux.value} does "
                f"not support {component.ComponentPlatform.Windows.value} OS versions."
            )


def _handle_platform_is_Windows(
    platform: typing.Optional[str],
    supported_architectures: typing.Optional[list[str]],
    supported_os_versions: typing.Optional[list[str]],
):
    if platform == component.ComponentPlatform.Windows.value:
        if component.ComponentSupportedArchitectures.Arm64.value in supported_architectures:
            raise domain_exception.DomainException(
                f"Component platform {component.ComponentPlatform.Windows.value} does not "
                f"support {component.ComponentSupportedArchitectures.Arm64.value} architecture."
            )
        if {
            component.ComponentSupportedOsVersions.Ubuntu_24.value,
        } & set(supported_os_versions):
            raise domain_exception.DomainException(
                f"Component platform {component.ComponentPlatform.Windows.value} does "
                f"not support {component.ComponentPlatform.Linux.value} OS versions."
            )


def from_attrs(
    platform: typing.Optional[str],
    supported_architectures: typing.Optional[list[str]],
    supported_os_versions: typing.Optional[list[str]],
) -> ComponentSystemConfigurationValueObject:

    _handle_empty_errors(platform, supported_architectures, supported_os_versions)
    _handle_not_in_a_list_errors(platform, supported_architectures, supported_os_versions)
    _handle_platform_is_Linux(platform, supported_os_versions)
    _handle_platform_is_Windows(platform, supported_architectures, supported_os_versions)

    return ComponentSystemConfigurationValueObject(
        platform=platform,
        supported_architectures=supported_architectures,
        supported_os_versions=supported_os_versions,
    )
