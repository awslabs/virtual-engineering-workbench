from unittest import mock

import assertpy
import boto3
import pytest

from app.provisioning.adapters.services import ec2_instance_management_service
from app.provisioning.domain.exceptions import insufficient_capacity_exception
from app.provisioning.domain.model import (
    block_device_mappings,
    instance_details,
    network_route_table,
    network_subnet,
    product_status,
)


def test_ec2_instance_management_service_should_return_instance_state(mock_ec2_instance):
    # ARRANGE
    client_provider = mock.MagicMock(return_value=boto3.client("ec2", region_name="us-east-1"))
    service = ec2_instance_management_service.EC2InstanceManagementService(
        ec2_boto_client_provider=client_provider,
    )

    # ACT
    status = service.get_instance_state(
        user_id="T0011AA",
        aws_account_id="001234567890",
        region="us-east-1",
        instance_id=mock_ec2_instance["InstanceId"],
    )

    # ASSERT
    assertpy.assert_that(status).is_equal_to("running")


def test_ec2_instance_management_service_should_return_instance_details(mock_ec2_instance):
    # ARRANGE
    client_provider = mock.MagicMock(return_value=boto3.client("ec2", region_name="us-east-1"))
    service = ec2_instance_management_service.EC2InstanceManagementService(
        ec2_boto_client_provider=client_provider,
    )

    # ACT
    inst_dtl = service.get_instance_details(
        user_id="T0011AA",
        aws_account_id="001234567890",
        region="us-east-1",
        instance_id=mock_ec2_instance["InstanceId"],
    )

    assertpy.assert_that(inst_dtl.dict(by_alias=True)).is_equal_to(
        instance_details.InstanceDetails.construct(
            PrivateIpAddress=mock.ANY,
            PublicIpAddress=mock.ANY,
            Tags=[
                instance_details.InstanceTag(Key="Name", Value="instanceName"),
                instance_details.InstanceTag(Key="Environment", Value="DEV"),
            ],
            State=instance_details.InstanceState(Name="running"),
        ).dict(by_alias=True)
    )


def test_ec2_instance_management_service_should_stop_running_instance(mock_ec2_instance, mock_ec2_client):
    # ARRANGE
    client_provider = mock.MagicMock(return_value=boto3.client("ec2", region_name="us-east-1"))
    service = ec2_instance_management_service.EC2InstanceManagementService(
        ec2_boto_client_provider=client_provider,
    )
    mocked_instance_id = mock_ec2_instance["InstanceId"]
    previous_response = mock_ec2_client.describe_instances(InstanceIds=[mocked_instance_id])
    previous_state = previous_response.get("Reservations")[0].get("Instances")[0]["State"]["Name"]

    # ACT
    current_state = service.stop_instance(
        user_id="T0011AA",
        aws_account_id="001234567890",
        region="us-east-1",
        instance_id=mocked_instance_id,
    )

    after_response = mock_ec2_client.describe_instances(InstanceIds=[mocked_instance_id])
    after_state = after_response.get("Reservations")[0].get("Instances")[0]["State"]["Name"]

    # ASSERT
    assertpy.assert_that(previous_state).is_equal_to(product_status.EC2InstanceState.Running)
    assertpy.assert_that(current_state).is_equal_to(product_status.EC2InstanceState.Stopping)
    assertpy.assert_that(after_state).is_equal_to(product_status.EC2InstanceState.Stopped)


def test_ec2_instance_management_service_should_start_stopped_instance(mock_stopped_ec2_instance, mock_ec2_client):
    # ARRANGE
    client_provider = mock.MagicMock(return_value=boto3.client("ec2", region_name="us-east-1"))
    service = ec2_instance_management_service.EC2InstanceManagementService(
        ec2_boto_client_provider=client_provider,
    )
    mocked_instance_id = mock_stopped_ec2_instance["InstanceId"]
    previous_response = mock_ec2_client.describe_instances(InstanceIds=[mocked_instance_id])
    previous_state = previous_response.get("Reservations")[0].get("Instances")[0]["State"]["Name"]

    # ACT
    current_state = service.start_instance(
        user_id="T0011AA",
        aws_account_id="001234567890",
        region="us-east-1",
        instance_id=mocked_instance_id,
    )

    after_response = mock_ec2_client.describe_instances(InstanceIds=[mocked_instance_id])
    after_state = after_response.get("Reservations")[0].get("Instances")[0]["State"]["Name"]

    # ASSERT
    assertpy.assert_that(previous_state).is_equal_to(product_status.EC2InstanceState.Stopped)
    assertpy.assert_that(current_state).is_equal_to(product_status.EC2InstanceState.Pending)
    assertpy.assert_that(after_state).is_equal_to(product_status.EC2InstanceState.Running)


def test_ec2_instance_management_service_should_catch_error_when_starting(
    mock_moto_calls, mock_start_ec2_instance_request
):
    # ARRANGE
    client_provider = mock.MagicMock(return_value=boto3.client("ec2", region_name="us-east-1"))

    service = ec2_instance_management_service.EC2InstanceManagementService(
        ec2_boto_client_provider=client_provider,
    )
    mocked_instance_id = "TEST_ID"

    # ACT/ASSERT
    with pytest.raises(insufficient_capacity_exception.InsufficientCapacityException) as ex:
        service.start_instance(
            user_id="T0011AA",
            aws_account_id="001234567890",
            region="us-east-1",
            instance_id=mocked_instance_id,
        )

    assertpy.assert_that(str(ex.value)).is_equal_to("Insufficient instance capacity error")
    mock_start_ec2_instance_request.assert_called_once_with(InstanceIds=[mocked_instance_id])
    client_provider.assert_called_once_with("001234567890", "us-east-1", "T0011AA")


def test_get_user_security_group_id_should_return_none_if_security_group_does_not_exist():
    # ARRANGE
    client_provider = mock.MagicMock(return_value=boto3.client("ec2", region_name="us-east-1"))
    service = ec2_instance_management_service.EC2InstanceManagementService(
        ec2_boto_client_provider=client_provider,
    )

    # ACT
    sg_id = service.get_user_security_group_id(
        user_id="T0011AA", aws_account_id="001234567890", region="us-east-1", vpc_id="vpc-12345"
    )

    # ASSERT
    assertpy.assert_that(sg_id).is_none()


def test_get_block_device_mappings_should_return_value_if_instance_exists(mock_ec2_client):
    # ARRANGE
    client_provider = mock.MagicMock(return_value=boto3.client("ec2", region_name="us-east-1"))
    service = ec2_instance_management_service.EC2InstanceManagementService(
        ec2_boto_client_provider=client_provider,
    )

    result = mock_ec2_client.run_instances(
        ImageId="ami-12c6146b",
        MinCount=1,
        MaxCount=1,
        BlockDeviceMappings=[
            {"DeviceName": "/dev/sda1", "Ebs": {"VolumeSize": 50}},
            {"DeviceName": "/dev/sda2", "Ebs": {"VolumeSize": 50}},
        ],
    )
    instance = result["Instances"][0]
    instance_id = instance["InstanceId"]

    # ACT
    mappings = service.get_block_device_mappings(
        user_id="T0011AA", aws_account_id="001234567890", region="us-east-1", instance_id=instance_id
    )

    # ASSERT
    assertpy.assert_that(mappings.rootDeviceName).is_equal_to("/dev/sda1")
    assertpy.assert_that(mappings.mappings).is_equal_to(
        [
            block_device_mappings.BlockDevice(
                deviceName="/dev/sda1",
                volumeId=instance["BlockDeviceMappings"][0]["Ebs"]["VolumeId"],
            ),
            block_device_mappings.BlockDevice(
                deviceName="/dev/sda2",
                volumeId=instance["BlockDeviceMappings"][1]["Ebs"]["VolumeId"],
            ),
        ]
    )

    # cleanup
    mock_ec2_client.terminate_instances(InstanceIds=[instance_id])


def test_get_user_security_group_id_should_return_security_group_id_if_exists(mock_ec2_client):
    # ARRANGE
    client_provider = mock.MagicMock(return_value=boto3.client("ec2", region_name="us-east-1"))
    service = ec2_instance_management_service.EC2InstanceManagementService(
        ec2_boto_client_provider=client_provider,
    )
    create_sg_response = mock_ec2_client.create_security_group(
        GroupName="user-sg-001234567890-T0011AA",
        VpcId="vpc-12345",
        Description="User based security group for workbenches and virtual targets",
        TagSpecifications=[
            {"ResourceType": "security-group", "Tags": [{"Key": "vew:securityGroup:ownerId", "Value": "T0011AA"}]}
        ],
    )
    created_sg_id = create_sg_response["GroupId"]

    # ACT
    sg_id = service.get_user_security_group_id(
        user_id="T0011AA", aws_account_id="001234567890", region="us-east-1", vpc_id="vpc-12345"
    )

    # ASSERT
    assertpy.assert_that(sg_id).is_equal_to(created_sg_id)


def test_create_user_security_group_should_create_user_security_group():
    # ARRANGE
    client_provider = mock.MagicMock(return_value=boto3.client("ec2", region_name="us-east-1"))
    service = ec2_instance_management_service.EC2InstanceManagementService(
        ec2_boto_client_provider=client_provider,
    )

    # ACT
    sg_id = service.create_user_security_group(
        user_id="T0011AA", aws_account_id="001234567890", region="us-east-1", vpc_id="vpc-12345"
    )

    # ASSERT
    assertpy.assert_that(sg_id).is_not_none()


def test_authorize_user_ip_address_should_authorize_security_group_ingress(mock_security_group):
    # ARRANGE
    client_provider = mock.MagicMock(return_value=boto3.client("ec2", region_name="us-east-1"))
    service = ec2_instance_management_service.EC2InstanceManagementService(
        ec2_boto_client_provider=client_provider,
    )

    # ACT
    response = service.authorize_user_ip_address(
        user_id="T0011AA",
        aws_account_id="001234567890",
        region="us-east-1",
        connection_option="RDP",
        ip_address="127.0.0.1/32",
        port=3389,
        to_port=3389,
        protocol="tcp",
        user_sg_id=mock_security_group,
    )

    # ASSERT
    assertpy.assert_that(response).is_none()


def test_get_user_ip_address_rule_id_should_return_none_id_if_not_exists(mock_security_group):
    # ARRANGE
    client_provider = mock.MagicMock(return_value=boto3.client("ec2", region_name="us-east-1"))
    service = ec2_instance_management_service.EC2InstanceManagementService(
        ec2_boto_client_provider=client_provider,
    )

    # ACT
    sg_rule_id = service.get_user_ip_address_rule_id(
        user_id="T0011AA",
        aws_account_id="001234567890",
        region="eu-west-1",
        connection_option="RDP",
        port=3389,
        to_port=3389,
        protocol="tcp",
        user_sg_id=mock_security_group,
    )

    # ASSERT
    assertpy.assert_that(sg_rule_id).is_none()


def test_get_user_ip_address_rule_id_should_return_security_group_id_if_exists(mock_security_group):
    # ARRANGE
    client_provider = mock.MagicMock(return_value=boto3.client("ec2", region_name="us-east-1"))
    service = ec2_instance_management_service.EC2InstanceManagementService(
        ec2_boto_client_provider=client_provider,
    )

    service.authorize_user_ip_address(
        user_id="T0011AA",
        aws_account_id="001234567890",
        region="eu-west-1",
        connection_option="RDP",
        ip_address="127.0.0.1/32",
        port=3389,
        to_port=3389,
        protocol="tcp",
        user_sg_id=mock_security_group,
    )

    # ACT
    sg_rule_id = service.get_user_ip_address_rule_id(
        user_id="T0011AA",
        aws_account_id="001234567890",
        region="eu-west-1",
        connection_option="RDP",
        port=3389,
        to_port=3389,
        protocol="tcp",
        user_sg_id=mock_security_group,
    )

    # ASSERT
    assertpy.assert_that(sg_rule_id).is_not_none()


def test_revoke_user_ip_address_should_revoke_security_group_ingress(mock_security_group):
    # ARRANGE
    client_provider = mock.MagicMock(return_value=boto3.client("ec2", region_name="us-east-1"))
    service = ec2_instance_management_service.EC2InstanceManagementService(
        ec2_boto_client_provider=client_provider,
    )

    service.authorize_user_ip_address(
        user_id="T0011AA",
        aws_account_id="001234567890",
        region="eu-west-1",
        connection_option="RDP",
        ip_address="127.0.0.1/32",
        port=3389,
        to_port=3389,
        protocol="tcp",
        user_sg_id=mock_security_group,
    )

    sg_rule_id = service.get_user_ip_address_rule_id(
        user_id="T0011AA",
        aws_account_id="001234567890",
        region="eu-west-1",
        connection_option="RDP",
        port=3389,
        to_port=3389,
        protocol="tcp",
        user_sg_id=mock_security_group,
    )

    # ACT
    response = service.revoke_user_ip_address(
        user_id="T0011AA",
        aws_account_id="001234567890",
        region="eu-west-1",
        sg_rule_id=sg_rule_id,
        user_sg_id=mock_security_group,
    )

    # ASSERT
    assertpy.assert_that(response).is_none()


def test_describe_vpc_route_tables_should_return_route_tables(mock_subnet_setup, mock_vpc):
    # ARRANGE
    client_provider = mock.MagicMock(return_value=boto3.client("ec2", region_name="us-east-1"))
    service = ec2_instance_management_service.EC2InstanceManagementService(
        ec2_boto_client_provider=client_provider,
    )

    # ACT
    route_tables = service.describe_vpc_route_tables(
        user_id="T0011AA", aws_account_id="001234567890", region="us-east-1", vpc_id=mock_vpc.get("Vpc").get("VpcId")
    )

    # ASSERT
    assertpy.assert_that(route_tables).is_not_empty()
    assertpy.assert_that(route_tables).is_length(2)
    assertpy.assert_that(route_tables).contains(
        network_route_table.NetworkRouteTable(
            associations=[
                network_route_table.NetworkRouteTableAssociation.construct(subnet_id=mock.ANY),
                network_route_table.NetworkRouteTableAssociation.construct(subnet_id=mock.ANY),
                network_route_table.NetworkRouteTableAssociation.construct(subnet_id=mock.ANY),
            ],
            routes=[
                network_route_table.NetworkRouteTableRoute(gateway_id="local", transit_gateway_id=None),
                network_route_table.NetworkRouteTableRoute.construct(gateway_id=None, transit_gateway_id=mock.ANY),
            ],
        )
    )


def test_describe_vpc_subnets_should_return_subnets(mock_subnet_setup, mock_vpc):
    # ARRANGE
    client_provider = mock.MagicMock(return_value=boto3.client("ec2", region_name="us-east-1"))
    service = ec2_instance_management_service.EC2InstanceManagementService(
        ec2_boto_client_provider=client_provider,
    )

    # ACT
    subnets = service.describe_vpc_subnets(
        user_id="T0011AA", aws_account_id="001234567890", region="us-east-1", vpc_id=mock_vpc.get("Vpc").get("VpcId")
    )

    # ASSERT
    assertpy.assert_that(subnets).is_not_empty()
    assertpy.assert_that(subnets).is_length(6)
    assertpy.assert_that(subnets).contains(
        network_subnet.NetworkSubnet.construct(
            availability_zone=mock.ANY,
            available_ip_address_count=251,
            subnet_id=mock.ANY,
            cidr_block=mock.ANY,
            vpc_id=mock.ANY,
        )
    )


def test_detach_instance_volume_should_call_aws_api_to_detach(mock_ec2_instance, mock_ec2_client):
    # ARRANGE

    volume = mock_ec2_client.create_volume(Size=80, AvailabilityZone="us-east-1a")
    mock_ec2_client.attach_volume(
        InstanceId=mock_ec2_instance.get("InstanceId"), VolumeId=volume.get("VolumeId"), Device="/dev/sdb"
    )

    client_provider = mock.MagicMock(return_value=mock_ec2_client)
    service = ec2_instance_management_service.EC2InstanceManagementService(
        ec2_boto_client_provider=client_provider,
    )

    # ACT
    service.detach_instance_volume(
        user_id="XXXXXXX",
        aws_account_id="XXXXXXXXXXXX",
        region="us-east-1",
        instance_id=mock_ec2_instance.get("InstanceId"),
        volume_id=volume.get("VolumeId"),
    )

    # ASSERT
    client_provider.assert_called_once_with("XXXXXXXXXXXX", "us-east-1", "XXXXXXX")
    vol = mock_ec2_client.describe_volumes(VolumeIds=[volume.get("VolumeId")])

    assertpy.assert_that(vol.get("Volumes")[0].get("Attachments")).is_length(0)


def test_attach_instance_volume_should_call_aws_api_to_attach(mock_ec2_instance, mock_ec2_client):
    # ARRANGE

    volume = mock_ec2_client.create_volume(Size=80, AvailabilityZone="us-east-1a")
    client_provider = mock.MagicMock(return_value=mock_ec2_client)
    service = ec2_instance_management_service.EC2InstanceManagementService(
        ec2_boto_client_provider=client_provider,
    )

    # ACT
    service.attach_instance_volume(
        user_id="XXXXXXX",
        aws_account_id="XXXXXXXXXXXX",
        region="us-east-1",
        instance_id=mock_ec2_instance.get("InstanceId"),
        volume_id=volume.get("VolumeId"),
        device_name="/dev/sdf",
    )

    # ASSERT
    client_provider.assert_called_once_with("XXXXXXXXXXXX", "us-east-1", "XXXXXXX")
    vol = mock_ec2_client.describe_volumes(VolumeIds=[volume.get("VolumeId")])

    assertpy.assert_that(vol.get("Volumes")[0].get("Attachments")).is_length(1)


def test_describe_subnet_should_return_subnet(mock_subnets, mock_vpc):
    # ARRANGE
    client_provider = mock.MagicMock(return_value=boto3.client("ec2", region_name="us-east-1"))
    service = ec2_instance_management_service.EC2InstanceManagementService(
        ec2_boto_client_provider=client_provider,
    )
    expected_subnet = mock_subnets[0].get("Subnet")

    # ACT
    subnet = service.describe_subnet(
        user_id="T0011AA", aws_account_id="001234567890", region="us-east-1", subnet_id=expected_subnet.get("SubnetId")
    )

    # ASSERT
    assertpy.assert_that(subnet).is_equal_to(
        network_subnet.NetworkSubnet(
            availability_zone=expected_subnet.get("AvailabilityZone"),
            available_ip_address_count=expected_subnet.get("AvailableIpAddressCount"),
            subnet_id=expected_subnet.get("SubnetId"),
            cidr_block=expected_subnet.get("CidrBlock"),
            vpc_id=expected_subnet.get("VpcId"),
        )
    )


def test_describe_subnet_interfaces_should_return_subnet(mock_vpc, mock_network_interface):
    # ARRANGE
    client_provider = mock.MagicMock(return_value=boto3.client("ec2", region_name="us-east-1"))
    service = ec2_instance_management_service.EC2InstanceManagementService(
        ec2_boto_client_provider=client_provider,
    )
    eni = mock_network_interface.get("NetworkInterface")

    # ACT
    interfaces = service.describe_subnet_interfaces(
        user_id="T0011AA", aws_account_id="001234567890", region="us-east-1", subnet_id=eni.get("SubnetId")
    )

    # ASSERT
    assertpy.assert_that(interfaces).is_length(1)
