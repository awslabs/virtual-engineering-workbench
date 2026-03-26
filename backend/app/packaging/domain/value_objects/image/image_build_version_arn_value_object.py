import re
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception


@dataclass(frozen=True)
class ImageBuildVersionArnValueObject:
    value: str


def from_str(value: str) -> ImageBuildVersionArnValueObject:
    if not (
        value
        and re.match(
            r"^arn:aws[^:]*:imagebuilder:[^:]+:(?:[0-9]{12}|aws):image/[a-z0-9-_]+/[0-9]+\.[0-9]+\.[0-9]+/[0-9]+$",
            value,
        )
    ):
        raise domain_exception.DomainException(
            "Image build version ARN should match ^arn:aws[^:]*:imagebuilder:[^:]+:(?:[0-9]{12}|aws):image/[a-z0-9-_]+/[0-9]+\.[0-9]+\.[0-9]+/[0-9]+$ pattern."  # noqa: W605
        )

    return ImageBuildVersionArnValueObject(value=value)
