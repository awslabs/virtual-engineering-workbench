from app.shared.ddd import value_object


class ProvisionedCompoundProductIdValueObject(value_object.ValueObject):
    """Value object for provisioned compound product identifiers"""

    value: str | None


def from_string(value: str | None) -> ProvisionedCompoundProductIdValueObject:
    """Create from an existing string value"""
    if value is not None and not isinstance(value, str):
        raise ValueError("ProvisionedCompoundProductId must be a non-empty string")
    elif value is not None and not value.strip():
        raise ValueError("ProvisionedCompoundProductId must be a non-empty string")

    return ProvisionedCompoundProductIdValueObject(value=value)


def no_id() -> ProvisionedCompoundProductIdValueObject:
    """Create a ProvisionedCompoundProductIdValueObject with no value"""
    return ProvisionedCompoundProductIdValueObject(value=None)
