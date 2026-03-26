import enum
import typing

from app.provisioning.domain.exceptions import domain_exception
from app.provisioning.domain.model import network_route_table, network_subnet

SubnetSelector: typing.TypeAlias = typing.Callable[
    [list[network_route_table.NetworkRouteTable], list[network_subnet.NetworkSubnet]],
    list[network_subnet.NetworkSubnet],
]
AllSubnetsSelector: typing.TypeAlias = typing.Callable[
    [list[network_route_table.NetworkRouteTable], list[network_subnet.NetworkSubnet]],
    list[network_subnet.NetworkSubnet],
]

INTERNET_GATEWAY_ID_PREFIX = "igw-"


class SubnetSelectorType(enum.StrEnum):
    PrivateSubnetWithTransitGateway = "PrivateSubnetWithTransitGateway"
    PublicSubnet = "PublicSubnet"
    TaggedSubnet = "TaggedSubnet"


def get_all_subnets_selector(selector_name: str, **kwargs) -> AllSubnetsSelector:
    if selector_name not in SubnetSelectorType:
        raise domain_exception.DomainException(f"Invalid subnet selector name: {selector_name}")

    selector_type = SubnetSelectorType(selector_name)

    match selector_type:
        case SubnetSelectorType.PrivateSubnetWithTransitGateway:
            return __get_all_private_subnets_with_transit_gateway
        case SubnetSelectorType.PublicSubnet:
            return __get_all_public_subnets
        case SubnetSelectorType.TaggedSubnet:
            if "tag" not in kwargs:
                raise domain_exception.DomainException("tag parameter must be provided for tagges subnet selector")

            tag_key, tag_value = kwargs["tag"].split(":")

            def _get_tagged_subnets(
                route_tables: list[network_route_table.NetworkRouteTable], subnets: list[network_subnet.NetworkSubnet]
            ):
                return __get_all_tagged_subnets(
                    route_tables=route_tables, subnets=subnets, tag_key=tag_key, tag_value=tag_value
                )

            return _get_tagged_subnets
        case _:
            raise domain_exception.DomainException(f"Unsupported subnet selector: {selector_type}")


def get_provisioning_subnet_selector(selector_name: str, **kwargs) -> SubnetSelector:
    all_subnets_selector = get_all_subnets_selector(selector_name=selector_name, **kwargs)

    def __get_ordered_subnets_with_most_ips(
        route_tables: list[network_route_table.NetworkRouteTable], subnets: list[network_subnet.NetworkSubnet]
    ) -> list[network_subnet.NetworkSubnet]:
        all_subnets = all_subnets_selector(route_tables, subnets)

        if not all_subnets:
            raise domain_exception.DomainException("No subnets provided.")

        subnets_by_capacity_desc = sorted(
            all_subnets,
            key=lambda s: s.available_ip_address_count,
            reverse=True,
        )

        return subnets_by_capacity_desc

    return __get_ordered_subnets_with_most_ips


def __get_all_private_subnets_with_transit_gateway(
    route_tables: list[network_route_table.NetworkRouteTable],
    subnets: list[network_subnet.NetworkSubnet],
) -> list[network_subnet.NetworkSubnet]:
    """
    Gets all subnet entities that are private and have transit gateway.

    Only the following subnets are considered:
    * Must not have a route to an internet gateway,
    * Must have a transit gateway attachment.

    Returns a list of subnets.
    """
    private_subnet_ids: set[str] = set()

    for route_table in route_tables:
        # filter out public subnets with gateway attachment
        if next(
            (r for r in route_table.routes if r.gateway_id and r.gateway_id.startswith(INTERNET_GATEWAY_ID_PREFIX)),
            None,
        ):
            continue

        # filter out subnets without transit gateway
        if not next((r for r in route_table.routes if r.transit_gateway_id), None):
            continue

        private_subnet_ids |= {s.subnet_id for s in route_table.associations if s.subnet_id}

    private_subnets = [s for s in subnets if s.subnet_id in private_subnet_ids]

    if not private_subnets:
        raise domain_exception.DomainException("No private subnets found in spoke account VPC.")

    return private_subnets


def __get_all_public_subnets(
    route_tables: list[network_route_table.NetworkRouteTable],
    subnets: list[network_subnet.NetworkSubnet],
) -> list[network_subnet.NetworkSubnet]:
    public_subnet_ids: set[str] = set()

    for route_table in route_tables:
        # filter out subnets without gateway attachment
        if not next(
            (r for r in route_table.routes if r.gateway_id and r.gateway_id.startswith(INTERNET_GATEWAY_ID_PREFIX)),
            None,
        ):
            continue

        public_subnet_ids |= {s.subnet_id for s in route_table.associations if s.subnet_id}

    public_subnets = [s for s in subnets if s.subnet_id in public_subnet_ids]

    if not public_subnets:
        raise domain_exception.DomainException("No public subnets found in spoke account VPC.")

    return public_subnets


def __get_all_tagged_subnets(
    route_tables: list[network_route_table.NetworkRouteTable],
    subnets: list[network_subnet.NetworkSubnet],
    tag_key: str,
    tag_value: str,
) -> list[network_subnet.NetworkSubnet]:
    tagged_subnets: list[network_subnet.NetworkSubnet] = []

    for subnet in subnets:
        if next((t for t in subnet.tags if t.key == tag_key and t.value == tag_value), None):
            tagged_subnets.append(subnet)

    if not tagged_subnets:
        raise domain_exception.DomainException("No tagged subnets found in spoke account VPC.")

    return tagged_subnets
