import ipaddress
import typing

from app.projects.domain.exceptions import domain_exception


class AccountHealthCheckIpValueObject:
    def __init__(self, value: ipaddress) -> None:
        self._value = value

    @property
    def value(self) -> ipaddress:
        return self._value


def from_list(values: list[str] | None) -> list[AccountHealthCheckIpValueObject]:
    if not values:
        return []

    return [from_str(v) for v in values]


def from_str(value: typing.Optional[str]) -> AccountHealthCheckIpValueObject:
    if not value:
        raise domain_exception.DomainException("IP address cannot be empty")

    try:
        addr = ipaddress.ip_address(value)
    except:
        raise domain_exception.DomainException(f"Value {value} is not a correct IP address")

    if not addr.is_private:
        raise domain_exception.DomainException(f"IP {value} must be a private IP address")

    return AccountHealthCheckIpValueObject(addr)
