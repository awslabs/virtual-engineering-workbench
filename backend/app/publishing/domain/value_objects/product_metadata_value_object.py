from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.publishing.domain.exceptions import domain_exception


@dataclass(frozen=True)
class ProductMetadataValueObject:
    value: List[Dict[str, Any]]


def from_list(value: Optional[List[Dict[str, Any]]]) -> ProductMetadataValueObject:
    if not value:
        raise domain_exception.DomainException("")

    return ProductMetadataValueObject(value)
