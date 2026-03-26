import assertpy
import pytest
from mypy_boto3_ec2 import client

from app.projects.adapters.exceptions import adapter_exception
from app.projects.adapters.services import ec2_network_service


def test_get_vpc_id_by_tag_raises_when_not_found(mock_provider):
    # ARRANGE
    srv = ec2_network_service.EC2NetworkService(ec2_provider=mock_provider.client("ec2"))

    # ACT & ASSERT
    with pytest.raises(adapter_exception.AdapterException):
        srv.get_vpc_id_by_tag(tag_name="random_tag", tag_value="random_tag")


def test_get_vpc_id_by_tag_returns_vpc_id_when_found(mock_provider, mock_ec2: client.EC2Client):
    # ARRANGE
    srv = ec2_network_service.EC2NetworkService(ec2_provider=mock_provider.client("ec2"))
    vpc_id = mock_ec2.describe_vpcs().get("Vpcs")[0].get("VpcId")
    mock_ec2.create_tags(Resources=[vpc_id], Tags=[{"Key": "test_tag", "Value": "test_vpc"}])

    # ACT
    fetched_vpc_id = srv.get_vpc_id_by_tag(tag_name="test_tag", tag_value="test_vpc")

    # ASSERT
    assertpy.assert_that(fetched_vpc_id).is_not_none()
    assertpy.assert_that(fetched_vpc_id).is_equal_to(vpc_id)


def test_get_vpc_id_by_tag_raises_when_multiple_found(mock_provider, mock_ec2: client.EC2Client):
    # ARRANGE
    srv = ec2_network_service.EC2NetworkService(ec2_provider=mock_provider.client("ec2"))
    vpc_id = mock_ec2.describe_vpcs().get("Vpcs")[0].get("VpcId")
    vpc_id_2 = mock_ec2.create_vpc(CidrBlock="10.0.0.0/16").get("Vpc").get("VpcId")
    mock_ec2.create_tags(Resources=[vpc_id, vpc_id_2], Tags=[{"Key": "test_tag", "Value": "test_vpc"}])

    # ACT & ASSERT
    with pytest.raises(adapter_exception.AdapterException):
        srv.get_vpc_id_by_tag(tag_name="test_tag", tag_value="test_vpc")


def test_get_vpcs_ids_returns_vpcs_ids_when_found(mock_provider, mock_ec2: client.EC2Client):
    # ARRANGE
    srv = ec2_network_service.EC2NetworkService(ec2_provider=mock_provider.client("ec2"))
    vpc_id = mock_ec2.describe_vpcs().get("Vpcs")[0].get("VpcId")
    vpc_id_2 = mock_ec2.create_vpc(CidrBlock="10.0.0.0/16").get("Vpc").get("VpcId")

    # ACT
    fetched_vpcs_ids = srv.get_vpcs_ids()

    # ASSERT
    assertpy.assert_that(fetched_vpcs_ids).is_not_none()
    assertpy.assert_that(fetched_vpcs_ids).is_equal_to([vpc_id, vpc_id_2])


def test_get_vpcs_ids_returns_empty_vpcs_ids_when_not_found(mock_provider, mock_ec2: client.EC2Client):
    # ARRANGE
    srv = ec2_network_service.EC2NetworkService(ec2_provider=mock_provider.client("ec2"))
    vpc_id = mock_ec2.describe_vpcs().get("Vpcs")[0].get("VpcId")

    mock_ec2.delete_vpc(VpcId=vpc_id)

    # ACT
    fetched_vpcs_ids = srv.get_vpcs_ids()

    # ASSERT
    assertpy.assert_that(fetched_vpcs_ids).is_not_none()
    assertpy.assert_that(fetched_vpcs_ids).is_equal_to([])


def test_get_subnets_by_tag_returns_subnets_when_found(mock_provider, mock_ec2: client.EC2Client):
    # ARRANGE
    srv = ec2_network_service.EC2NetworkService(ec2_provider=mock_provider.client("ec2"))
    vpc = mock_ec2.create_vpc(CidrBlock="172.31.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]
    subnet_1 = mock_ec2.create_subnet(VpcId=vpc_id, CidrBlock="172.31.1.0/24")
    subnet_2 = mock_ec2.create_subnet(VpcId=vpc_id, CidrBlock="172.31.2.0/24")
    mock_ec2.create_tags(Resources=[subnet_1["Subnet"]["SubnetId"]], Tags=[{"Key": "subnet_type", "Value": "frontend"}])
    mock_ec2.create_tags(Resources=[subnet_2["Subnet"]["SubnetId"]], Tags=[{"Key": "subnet_type", "Value": "backend"}])

    # ACT
    fetched_subnets = srv.get_subnets_by_tag(tag_name="subnet_type", tag_value="backend", vpc_id=vpc_id)

    # ASSERT
    assertpy.assert_that(fetched_subnets).is_instance_of(list)  # Check that it's a list
    assertpy.assert_that(fetched_subnets).is_not_empty()  # Check that it's not empty
    assertpy.assert_that(len(fetched_subnets)).is_equal_to(1)  # Expecting one subnet
    assertpy.assert_that(fetched_subnets[0]["SubnetId"]).is_equal_to(subnet_2["Subnet"]["SubnetId"])
    assertpy.assert_that(fetched_subnets[0]["CidrBlock"]).is_equal_to(subnet_2["Subnet"]["CidrBlock"])
    assertpy.assert_that(fetched_subnets).does_not_contain(
        subnet_1["Subnet"]
    )  # Check that subnet_1 is not in the fetched subnets


def test_get_subnets_by_tag_returns_multiple_subnets_when_multiple_found(mock_provider, mock_ec2: client.EC2Client):
    # ARRANGE
    srv = ec2_network_service.EC2NetworkService(ec2_provider=mock_provider.client("ec2"))
    vpc = mock_ec2.create_vpc(CidrBlock="172.31.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]

    subnet_1 = mock_ec2.create_subnet(VpcId=vpc_id, CidrBlock="172.31.1.0/24")
    subnet_2 = mock_ec2.create_subnet(VpcId=vpc_id, CidrBlock="172.31.2.0/24")

    mock_ec2.create_tags(
        Resources=[subnet_1["Subnet"]["SubnetId"], subnet_2["Subnet"]["SubnetId"]],
        Tags=[{"Key": "subnet_type", "Value": "backend"}],
    )

    # ACT
    fetched_subnets = srv.get_subnets_by_tag(tag_name="subnet_type", tag_value="backend")

    # DEBUGGING: Print the fetched subnets to verify their content
    print(f"Fetched Subnets: {fetched_subnets}")

    # ASSERT
    assertpy.assert_that(fetched_subnets).is_instance_of(list)  # Check that it's a list
    assertpy.assert_that(fetched_subnets).is_not_empty()  # Check that it's not empty
    assertpy.assert_that(len(fetched_subnets)).is_equal_to(2)  # Expecting two subnets

    # Check that both subnets are in the fetched results
    assert all(
        any(subnet["SubnetId"] == s["SubnetId"] and subnet["CidrBlock"] == s["CidrBlock"] for s in fetched_subnets)
        for subnet in [subnet_1["Subnet"], subnet_2["Subnet"]]
    )


def test_get_subnets_by_tag_returns_empty_list_when_not_found(mock_provider, mock_ec2: client.EC2Client):
    # ARRANGE
    srv = ec2_network_service.EC2NetworkService(ec2_provider=mock_provider.client("ec2"))
    mock_ec2.create_vpc(CidrBlock="172.31.0.0/16")

    # ACT
    fetched_subnets = srv.get_subnets_by_tag(tag_name="subnet_type", tag_value="backend")

    # ASSERT
    assertpy.assert_that(fetched_subnets).is_empty()


def test_get_subnets_by_tag_with_vpc_id_returns_subnet_when_found(mock_provider, mock_ec2: client.EC2Client):
    # ARRANGE
    srv = ec2_network_service.EC2NetworkService(ec2_provider=mock_provider.client("ec2"))
    vpc = mock_ec2.create_vpc(CidrBlock="172.31.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]
    subnet_1 = mock_ec2.create_subnet(VpcId=vpc_id, CidrBlock="172.31.1.0/24")
    subnet_2 = mock_ec2.create_subnet(VpcId=vpc_id, CidrBlock="172.31.2.0/24")
    mock_ec2.create_tags(Resources=[subnet_1["Subnet"]["SubnetId"]], Tags=[{"Key": "subnet_type", "Value": "frontend"}])
    mock_ec2.create_tags(Resources=[subnet_2["Subnet"]["SubnetId"]], Tags=[{"Key": "subnet_type", "Value": "backend"}])

    # ACT
    fetched_subnets = srv.get_subnets_by_tag(tag_name="subnet_type", tag_value="backend", vpc_id=vpc_id)

    # ASSERT
    assertpy.assert_that(fetched_subnets).is_not_empty()
    assertpy.assert_that(len(fetched_subnets)).is_equal_to(1)  # Expecting one subnet
    assertpy.assert_that(fetched_subnets[0]["SubnetId"]).is_equal_to(subnet_2["Subnet"]["SubnetId"])
    assertpy.assert_that(fetched_subnets[0]["CidrBlock"]).is_equal_to(subnet_2["Subnet"]["CidrBlock"])
    assertpy.assert_that(fetched_subnets).does_not_contain(
        subnet_1["Subnet"]
    )  # Check that subnet_1 is not in the fetched subnets


def test_get_subnets_by_tag_with_vpc_id_returns_empty_list_when_not_found(mock_provider, mock_ec2: client.EC2Client):
    # ARRANGE
    srv = ec2_network_service.EC2NetworkService(ec2_provider=mock_provider.client("ec2"))
    vpc = mock_ec2.create_vpc(CidrBlock="172.31.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]

    # ACT
    fetched_subnets = srv.get_subnets_by_tag(tag_name="subnet_type", tag_value="backend", vpc_id=vpc_id)

    # ASSERT
    assertpy.assert_that(fetched_subnets).is_empty()
