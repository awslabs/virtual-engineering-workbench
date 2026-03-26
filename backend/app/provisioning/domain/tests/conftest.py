import pytest
from freezegun import freeze_time

from app.provisioning.domain.model import network_route_table, network_subnet


@pytest.fixture
def mock_tgw_route():
    return network_route_table.NetworkRouteTableRoute(
        transit_gateway_id="tgw-id",
    )


@pytest.fixture
def mock_local_route():
    return network_route_table.NetworkRouteTableRoute(
        gateway_id="local",
    )


@pytest.fixture
def mock_public_route():
    return network_route_table.NetworkRouteTableRoute(
        gateway_id="igw-id",
    )


@pytest.fixture
def mock_gatewayendpoint_route():
    return network_route_table.NetworkRouteTableRoute(
        gateway_id="vpce-id",
    )


@pytest.fixture
def mock_private_route_table(mock_tgw_route, mock_local_route):
    def _mock_private_route_table(associations=[network_route_table.NetworkRouteTableAssociation(subnet_id="s-prv")]):
        return network_route_table.NetworkRouteTable(
            associations=associations,
            routes=[
                mock_tgw_route,
                mock_local_route,
            ],
        )

    return _mock_private_route_table


@pytest.fixture
def mock_private_route_table_with_vpce(mock_tgw_route, mock_local_route, mock_gatewayendpoint_route):
    def _mock_private_route_table_with_vpce(
        associations=[network_route_table.NetworkRouteTableAssociation(subnet_id="s-prv")],
    ):
        return network_route_table.NetworkRouteTable(
            associations=associations,
            routes=[
                mock_tgw_route,
                mock_local_route,
                mock_gatewayendpoint_route,
            ],
        )

    return _mock_private_route_table_with_vpce


@pytest.fixture
def mock_public_route_table(mock_tgw_route, mock_local_route, mock_public_route):
    def _mock_public_route_table(associations=[network_route_table.NetworkRouteTableAssociation(subnet_id="s-pub")]):
        return network_route_table.NetworkRouteTable(
            associations=associations,
            routes=[
                mock_public_route,
                mock_tgw_route,
                mock_local_route,
            ],
        )

    return _mock_public_route_table


@pytest.fixture
def mock_subnet():
    def _mock_subnet(
        subnet_id: str = "s-pub",
        available_ip_address_count: int = 100,
        availability_zone: str = "az-1",
        tags: list[network_subnet.NetworkSubnetTag] = [],
    ):
        return network_subnet.NetworkSubnet(
            subnet_id=subnet_id,
            available_ip_address_count=available_ip_address_count,
            availability_zone=availability_zone,
            tags=tags,
            cidr_block="192.168.1.0/24",
            vpc_id="vpc-123",
        )

    return _mock_subnet


@pytest.fixture
def mock_subnets():
    def _mock_subnets(
        subnet_id: str = "s-pub",
        available_ip_address_count: int = 100,
        availability_zone: str = "az-1",
        tags: list[network_subnet.NetworkSubnetTag] = [],
    ):
        return [
            network_subnet.NetworkSubnet(
                subnet_id=subnet_id,
                available_ip_address_count=available_ip_address_count,
                availability_zone=availability_zone,
                tags=tags,
                cidr_block="192.168.1.0/24",
                vpc_id="vpc-123",
            ),
            network_subnet.NetworkSubnet(
                subnet_id=subnet_id,
                available_ip_address_count=available_ip_address_count,
                availability_zone="az-2",
                tags=tags,
                cidr_block="192.168.1.0/24",
                vpc_id="vpc-123",
            ),
        ]

    return _mock_subnets


@pytest.fixture
def default_subnet_selector(mock_subnets):
    return lambda **kwargs: mock_subnets()


@pytest.fixture(autouse=True)
def frozen_time():
    with freeze_time("2025-01-01 12:00:00"):
        yield
