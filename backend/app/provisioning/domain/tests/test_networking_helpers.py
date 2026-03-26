import assertpy
import pytest

from app.provisioning.domain.aggregates.internal import networking_helpers
from app.provisioning.domain.exceptions import domain_exception
from app.provisioning.domain.model import network_route_table, network_subnet


def test_get_private_subnets_with_most_ips_should_filter_out_igw(
    mock_private_route_table, mock_public_route_table, mock_subnet
):
    # ARRANGE
    route_tables = [
        mock_public_route_table(),
        mock_private_route_table(),
    ]

    subnets = [
        mock_subnet(subnet_id="s-pub", available_ip_address_count=120),
        mock_subnet(subnet_id="s-prv", available_ip_address_count=100),
    ]
    subnet_selector = networking_helpers.get_provisioning_subnet_selector(
        selector_name="PrivateSubnetWithTransitGateway"
    )

    expected_subnets = [
        mock_subnet(subnet_id="s-prv", available_ip_address_count=100),
    ]

    # ACT
    ordered_subnets = subnet_selector(
        route_tables=route_tables,
        subnets=subnets,
    )
    # ASSERT

    assertpy.assert_that(ordered_subnets).is_equal_to(expected_subnets)


def test_get_private_subnets_with_most_ips_should_ignore_vpce_id(mock_private_route_table_with_vpce, mock_subnet):
    # ARRANGE
    route_tables = [mock_private_route_table_with_vpce()]

    subnets = [
        mock_subnet(subnet_id="s-pub", available_ip_address_count=120),
        mock_subnet(subnet_id="s-prv", available_ip_address_count=100),
    ]

    subnet_selector = networking_helpers.get_provisioning_subnet_selector(
        selector_name="PrivateSubnetWithTransitGateway"
    )

    expected_subnets = [
        mock_subnet(subnet_id="s-prv", available_ip_address_count=100),
    ]

    # ACT
    ordered_subnets = subnet_selector(
        route_tables=route_tables,
        subnets=subnets,
    )
    # ASSERT

    assertpy.assert_that(ordered_subnets).is_equal_to(expected_subnets)


def test_get_private_subnets_with_most_ips_should_return_ordered_subnets_with_most_ips(
    mock_private_route_table, mock_subnet
):
    # ARRANGE
    route_tables = [
        mock_private_route_table(
            associations=[
                network_route_table.NetworkRouteTableAssociation(subnet_id="s-prv-1"),
                network_route_table.NetworkRouteTableAssociation(subnet_id="s-prv-2"),
            ]
        ),
    ]

    subnets = [
        mock_subnet(subnet_id="s-prv-1", available_ip_address_count=100),
        mock_subnet(subnet_id="s-prv-2", available_ip_address_count=120),
    ]
    subnet_selector = networking_helpers.get_provisioning_subnet_selector(
        selector_name="PrivateSubnetWithTransitGateway"
    )

    # ACT

    expected_subnets = [
        mock_subnet(subnet_id="s-prv-2", available_ip_address_count=120),
        mock_subnet(subnet_id="s-prv-1", available_ip_address_count=100),
    ]
    ordered_subnets = subnet_selector(
        route_tables=route_tables,
        subnets=subnets,
    )
    # ASSERT

    assertpy.assert_that(ordered_subnets).is_equal_to(expected_subnets)


def test_get_private_subnets_with_most_ips_should_raise_when_no_private_subnets(mock_public_route_table, mock_subnet):
    # ARRANGE
    route_tables = [
        mock_public_route_table(),
    ]

    subnets = [
        mock_subnet(subnet_id="s-pub", available_ip_address_count=120),
        mock_subnet(subnet_id="s-prv", available_ip_address_count=100),
    ]
    subnet_selector = networking_helpers.get_provisioning_subnet_selector(
        selector_name="PrivateSubnetWithTransitGateway"
    )

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        subnet_selector(
            route_tables=route_tables,
            subnets=subnets,
        )
    # ASSERT

    assertpy.assert_that(str(e.value)).is_equal_to("No private subnets found in spoke account VPC.")


def test_get_public_subnets_with_most_ips_should_filter_out_non_igw_subnets(
    mock_private_route_table, mock_public_route_table, mock_subnet
):
    # ARRANGE
    route_tables = [
        mock_public_route_table(),
        mock_private_route_table(),
    ]

    subnets = [
        mock_subnet(subnet_id="s-pub", available_ip_address_count=100),
        mock_subnet(subnet_id="s-prv", available_ip_address_count=120),
    ]
    subnet_selector = networking_helpers.get_provisioning_subnet_selector(selector_name="PublicSubnet")

    expected_subnets = [
        mock_subnet(subnet_id="s-pub", available_ip_address_count=100),
    ]

    # ACT
    ordered_subnets = subnet_selector(
        route_tables=route_tables,
        subnets=subnets,
    )
    # ASSERT

    assertpy.assert_that(ordered_subnets).is_equal_to(expected_subnets)


def test_get_public_subnets_with_most_ips_should_return_subnets_with_most_ips(mock_public_route_table, mock_subnet):
    # ARRANGE
    route_tables = [
        mock_public_route_table(
            associations=[
                network_route_table.NetworkRouteTableAssociation(subnet_id="s-pub-1"),
                network_route_table.NetworkRouteTableAssociation(subnet_id="s-pub-2"),
            ]
        ),
    ]

    subnets = [
        mock_subnet(subnet_id="s-pub-1", available_ip_address_count=100),
        mock_subnet(subnet_id="s-pub-2", available_ip_address_count=120),
    ]
    subnet_selector = networking_helpers.get_provisioning_subnet_selector(selector_name="PublicSubnet")

    expected_subnets = [
        mock_subnet(subnet_id="s-pub-2", available_ip_address_count=120),
        mock_subnet(subnet_id="s-pub-1", available_ip_address_count=100),
    ]
    # ACT
    ordered_subnets = subnet_selector(
        route_tables=route_tables,
        subnets=subnets,
    )
    # ASSERT

    assertpy.assert_that(ordered_subnets).is_equal_to(expected_subnets)


def test_get_public_subnets_with_most_ips_should_raise_when_no_public_subnets(mock_private_route_table, mock_subnet):
    # ARRANGE
    route_tables = [
        mock_private_route_table(),
    ]

    subnets = [
        mock_subnet(subnet_id="s-pub", available_ip_address_count=120),
        mock_subnet(subnet_id="s-prv", available_ip_address_count=100),
    ]
    subnet_selector = networking_helpers.get_provisioning_subnet_selector(selector_name="PublicSubnet")

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        subnet_selector(
            route_tables=route_tables,
            subnets=subnets,
        )
    # ASSERT

    assertpy.assert_that(str(e.value)).is_equal_to("No public subnets found in spoke account VPC.")


def test_get_tagged_subnets_with_most_ips_should_filter_out_non_tagged_subnets(
    mock_private_route_table, mock_public_route_table, mock_subnet
):
    # ARRANGE
    route_tables = [
        mock_public_route_table(),
        mock_private_route_table(),
    ]

    subnets = [
        mock_subnet(subnet_id="s-pub", available_ip_address_count=100),
        mock_subnet(
            subnet_id="s-prv",
            available_ip_address_count=120,
            tags=[network_subnet.NetworkSubnetTag(Key="prov", Value="true")],
        ),
    ]
    subnet_selector = networking_helpers.get_provisioning_subnet_selector(selector_name="TaggedSubnet", tag="prov:true")

    expected_subnets = [
        mock_subnet(
            subnet_id="s-prv",
            available_ip_address_count=120,
            tags=[network_subnet.NetworkSubnetTag(Key="prov", Value="true")],
        ),
    ]
    # ACT
    ordered_subnets = subnet_selector(
        route_tables=route_tables,
        subnets=subnets,
    )
    # ASSERT

    assertpy.assert_that(ordered_subnets).is_equal_to(expected_subnets)


def test_get_tagged_subnets_with_most_ips_should_return_subnets_with_most_ips(mock_public_route_table, mock_subnet):
    # ARRANGE
    route_tables = [
        mock_public_route_table(
            associations=[
                network_route_table.NetworkRouteTableAssociation(subnet_id="s-pub-1"),
                network_route_table.NetworkRouteTableAssociation(subnet_id="s-pub-2"),
            ]
        ),
    ]

    subnets = [
        mock_subnet(
            subnet_id="s-pub-1",
            available_ip_address_count=100,
            tags=[network_subnet.NetworkSubnetTag(Key="prov", Value="true")],
        ),
        mock_subnet(
            subnet_id="s-pub-2",
            available_ip_address_count=120,
            tags=[network_subnet.NetworkSubnetTag(Key="prov", Value="true")],
        ),
    ]
    subnet_selector = networking_helpers.get_provisioning_subnet_selector(selector_name="TaggedSubnet", tag="prov:true")

    expected_subnets = [
        mock_subnet(
            subnet_id="s-pub-2",
            available_ip_address_count=120,
            tags=[network_subnet.NetworkSubnetTag(Key="prov", Value="true")],
        ),
        mock_subnet(
            subnet_id="s-pub-1",
            available_ip_address_count=100,
            tags=[network_subnet.NetworkSubnetTag(Key="prov", Value="true")],
        ),
    ]
    # ACT
    ordered_subnets = subnet_selector(
        route_tables=route_tables,
        subnets=subnets,
    )
    # ASSERT

    assertpy.assert_that(ordered_subnets).is_equal_to(expected_subnets)


def test_get_tagged_subnets_with_most_ips_should_raise_when_no_tagged_subnets(mock_private_route_table, mock_subnet):
    # ARRANGE
    route_tables = [
        mock_private_route_table(),
    ]

    subnets = [
        mock_subnet(subnet_id="s-pub", available_ip_address_count=120),
        mock_subnet(subnet_id="s-prv", available_ip_address_count=100),
    ]
    subnet_selector = networking_helpers.get_provisioning_subnet_selector(selector_name="TaggedSubnet", tag="prov:true")

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        subnet_selector(
            route_tables=route_tables,
            subnets=subnets,
        )
    # ASSERT

    assertpy.assert_that(str(e.value)).is_equal_to("No tagged subnets found in spoke account VPC.")


def test_subnet_selector_when_does_not_exist_should_raise(mock_private_route_table, mock_subnet):
    # ARRANGE

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        networking_helpers.get_provisioning_subnet_selector(selector_name="DoesNotExist")
    # ASSERT

    assertpy.assert_that(str(e.value)).is_equal_to("Invalid subnet selector name: DoesNotExist")
