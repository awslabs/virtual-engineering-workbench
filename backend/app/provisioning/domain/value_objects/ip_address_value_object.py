import typing

from app.provisioning.domain.exceptions import domain_exception
from app.shared.ddd import value_object


class IpV4Address(value_object.ValueObject):
    value: str


def from_str(value: typing.Optional[str]) -> IpV4Address:
    if not value:
        raise domain_exception.DomainException("IP v4 address cannot be empty.")

    ip_bytes = value.split(".")

    if len(ip_bytes) != 4:
        raise domain_exception.DomainException("Invalid IP v4 address.")

    for ip_byte in ip_bytes:
        if int(ip_byte) < 0 or int(ip_byte) > 255:
            raise domain_exception.DomainException("Invalid IP v4 address.")

    return IpV4Address(value=value)
