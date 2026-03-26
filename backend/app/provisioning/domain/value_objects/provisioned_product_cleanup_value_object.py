import json
import typing
from json.decoder import JSONDecodeError

from app.provisioning.domain.exceptions import domain_exception
from app.shared.ddd import value_object


class ProvisionedProductCleanupConfigValueObject(value_object.ValueObject):
    value: dict


def from_json_str(value: typing.Optional[str]) -> ProvisionedProductCleanupConfigValueObject:
    if not value:
        raise domain_exception.DomainException(
            "PROVISIONED_PRODUCT_CLEANUP_CONFIG variable not found in OS environment (maybe missing in congig?)"
        )

    try:
        pp_cleanup = json.loads(value)
    except JSONDecodeError as e:
        raise domain_exception.DomainException(
            f"PROVISIONED_PRODUCT_CLEANUP_CONFIG variable ({value}) is not a valid JSON: {e}"
        )
    except TypeError as e:
        raise domain_exception.DomainException(
            f"PROVISIONED_PRODUCT_CLEANUP_CONFIG variable ({value}) is not a valid JSON: {e}"
        )

    return ProvisionedProductCleanupConfigValueObject(value=pp_cleanup)
