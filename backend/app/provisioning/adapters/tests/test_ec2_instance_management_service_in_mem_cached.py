from unittest import mock

import assertpy
import boto3

from app.provisioning.adapters.services import ec2_instance_management_service_in_mem_cached
from app.provisioning.domain.ports import instance_management_service


class DictCtxProvider:

    context: dict

    def __init__(self):
        self.context = {}

    def append_context(self, **additional_context):
        self.context.update(**additional_context)


def test_get_instance_state_should_cache_all_ec2_states_in_account_region():
    # ARRANGE
    us_east_1_client = boto3.client("ec2", region_name="us-east-1")

    us_east_1_instances = us_east_1_client.run_instances(ImageId="ami-12c6146b", MinCount=5, MaxCount=5)

    mocked_instance_mgmt_service = mock.create_autospec(spec=instance_management_service.InstanceManagementService)

    ec2_client_provider = mock.MagicMock(
        side_effect=lambda account, region, user: boto3.client("ec2", region_name=region)
    )

    service = ec2_instance_management_service_in_mem_cached.EC2InstanceManagementServiceCachedInMemory(
        inner=mocked_instance_mgmt_service,
        ec2_boto_client_provider=ec2_client_provider,
        request_context_manager=DictCtxProvider(),
    )

    # ACT
    us_instance_state_1 = service.get_instance_state(
        user_id="test",
        aws_account_id="acct",
        region="us-east-1",
        instance_id=us_east_1_instances.get("Instances")[0].get("InstanceId"),
    )
    us_instance_state_2 = service.get_instance_state(
        user_id="test",
        aws_account_id="acct",
        region="us-east-1",
        instance_id=us_east_1_instances.get("Instances")[4].get("InstanceId"),
    )

    # ASSERT
    assertpy.assert_that(ec2_client_provider.call_count).is_equal_to(1)
    assertpy.assert_that(us_instance_state_1).is_not_none()
    assertpy.assert_that(us_instance_state_2).is_not_none()


def test_get_instance_state_should_extend_cache_when_another_account_region_requested():
    # ARRANGE
    us_east_1_client = boto3.client("ec2", region_name="us-east-1")
    eu_west_3_client = boto3.client("ec2", region_name="eu-west-3")

    us_east_1_instances = us_east_1_client.run_instances(ImageId="ami-12c6146b", MinCount=5, MaxCount=5)
    eu_west_3_instances = eu_west_3_client.run_instances(ImageId="ami-12c6146b", MinCount=5, MaxCount=5)

    mocked_instance_mgmt_service = mock.create_autospec(spec=instance_management_service.InstanceManagementService)

    ec2_client_provider = mock.MagicMock(
        side_effect=lambda account, region, user: boto3.client("ec2", region_name=region)
    )

    service = ec2_instance_management_service_in_mem_cached.EC2InstanceManagementServiceCachedInMemory(
        inner=mocked_instance_mgmt_service,
        ec2_boto_client_provider=ec2_client_provider,
        request_context_manager=DictCtxProvider(),
    )

    # ACT
    us_instance_state_1 = service.get_instance_state(
        user_id="test",
        aws_account_id="acct",
        region="us-east-1",
        instance_id=us_east_1_instances.get("Instances")[0].get("InstanceId"),
    )
    us_instance_state_2 = service.get_instance_state(
        user_id="test",
        aws_account_id="acct",
        region="us-east-1",
        instance_id=us_east_1_instances.get("Instances")[4].get("InstanceId"),
    )

    eu_instance_state_1 = service.get_instance_state(
        user_id="test",
        aws_account_id="acct",
        region="eu-west-3",
        instance_id=eu_west_3_instances.get("Instances")[0].get("InstanceId"),
    )
    eu_instance_state_2 = service.get_instance_state(
        user_id="test",
        aws_account_id="acct",
        region="eu-west-3",
        instance_id=eu_west_3_instances.get("Instances")[4].get("InstanceId"),
    )

    # ASSERT
    assertpy.assert_that(ec2_client_provider.call_count).is_equal_to(2)
    assertpy.assert_that(us_instance_state_1).is_not_none()
    assertpy.assert_that(us_instance_state_2).is_not_none()
    assertpy.assert_that(eu_instance_state_1).is_not_none()
    assertpy.assert_that(eu_instance_state_2).is_not_none()
