"""AWS Marketplace AMI products only launch on the instance types their offer lists.

Recipe versions built on such a product keep that list (``parentImageSupportedInstanceTypes``). An empty or
missing list means the restriction is unknown, and every instance type is let through.
"""

import re

from app.packaging.domain.exceptions import domain_exception

# family = letters + generation + options, e.g. m7i, m7i-flex, c7gn, t3a
_FAMILY = re.compile(r"^([a-z]+)(\d+)([a-z0-9-]*)$")
_SHOWN_ALTERNATIVES = 5


def _parse(instance_type: str) -> tuple[str, int, str, str] | None:
    family, _, size = instance_type.partition(".")
    match = _FAMILY.match(family)
    if not match or not size:
        return None
    letters, generation, options = match.groups()
    return letters, int(generation), options, size


def _is_graviton(options: str) -> bool:
    return options.startswith("g")


def is_supported(instance_type: str, supported_instance_types: list[str] | None) -> bool:
    return not supported_instance_types or instance_type in supported_instance_types


def choose_instance_type(preferred: str, supported_instance_types: list[str] | None, product_id: str) -> str:
    """The preferred type if the product allows it, else the closest allowed type: same size and processor
    family, preferably the same instance family and options, newest generation first."""
    if is_supported(preferred, supported_instance_types):
        return preferred
    wanted = _parse(preferred)
    candidates = []
    for candidate in supported_instance_types or []:
        parsed = _parse(candidate)
        if not wanted or not parsed:
            continue
        letters, generation, options, size = parsed
        if size != wanted[3] or _is_graviton(options) != _is_graviton(wanted[2]):
            continue
        candidates.append(((letters != wanted[0], options != wanted[2], -generation, len(options)), candidate))
    if not candidates:
        raise domain_exception.DomainException(
            f"AWS Marketplace product {product_id} does not support instance type {preferred} "
            "or a similar one of the same size."
        )
    return min(candidates)[1]


def check_supported(instance_types: list[str], supported_instance_types: list[str] | None, product_id: str) -> None:
    unsupported = [t for t in instance_types if not is_supported(t, supported_instance_types)]
    if not unsupported:
        return
    alternatives = set()
    for instance_type in unsupported:
        try:
            alternatives.add(choose_instance_type(instance_type, supported_instance_types, product_id))
        except domain_exception.DomainException:
            pass
    hint = f" Supported alternatives: {', '.join(sorted(alternatives)[:_SHOWN_ALTERNATIVES])}." if alternatives else ""
    raise domain_exception.DomainException(
        f"AWS Marketplace product {product_id} does not support instance type(s) {', '.join(unsupported)}.{hint}"
    )
