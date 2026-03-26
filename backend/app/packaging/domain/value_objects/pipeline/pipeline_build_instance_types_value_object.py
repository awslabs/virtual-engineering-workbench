from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class PipelineBuildInstanceTypesValueObject:
    value: list[str]


def from_list(build_instance_types: list[str]) -> PipelineBuildInstanceTypesValueObject:
    if not (build_instance_types and len(build_instance_types) > 0):
        raise domain_exception.DomainException("Pipeline build instance types cannot be empty.")
    for build_instance_type in build_instance_types:
        if not build_instance_type:
            raise domain_exception.DomainException("Build instance type value cannot be empty.")

    return PipelineBuildInstanceTypesValueObject(value=build_instance_types)
