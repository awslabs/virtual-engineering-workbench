import typing

from app.provisioning.domain.exceptions import domain_exception
from app.shared.ddd import value_object


class IpV4Range(value_object.ValueObject):
    value: str


def from_str(value: typing.Optional[str]) -> IpV4Range:
    if not value:
        raise domain_exception.DomainException("IP v4 range cannot be empty.")

    ip_parts = value.split("/")

    if len(ip_parts) != 2:
        raise domain_exception.DomainException("Invalid IP v4 CIDR.")

    if not ip_parts[1].isdigit() or int(ip_parts[1]) < 0 or int(ip_parts[1]) > 32:
        raise domain_exception.DomainException("Invalid IP v4 CIDR.")

    ip_bytes = ip_parts[0].split(".")

    for ip_byte in ip_bytes:
        if int(ip_byte) < 0 or int(ip_byte) > 255:
            raise domain_exception.DomainException("Invalid IP v4 CIDR.")

    return IpV4Range(value=value)
