from unittest import mock

import assertpy

from app.provisioning.domain.model import network_route_table, network_subnet
from app.provisioning.domain.ports import instance_management_service, parameter_service
from app.provisioning.domain.query_services import provisioning_infrastructure_domain_query_service
from app.provisioning.domain.value_objects import account_id_value_object, region_value_object


def test_get_provisioning_subnets_in_account_should_use_subnet_selector_to_filter():
    # ARRANGE
    ps_mock = mock.create_autospec(spec=parameter_service.ParameterService)
    ps_mock.get_parameter_value.return_value = "vpc-123"
    im_mock = mock.create_autospec(spec=instance_management_service.InstanceManagementService)
    im_mock.describe_vpc_subnets.return_value = [
        network_subnet.NetworkSubnet(
            AvailabilityZone="test-az",
            AvailableIpAddressCount=1,
            SubnetId="test-123",
            Tags=[],
            CidrBlock="192.168.1.0/24",
            VpcId="vpc-123",
        )
    ]
    im_mock.describe_vpc_route_tables.return_value = [network_route_table.NetworkRouteTable(Associations=[], Routes=[])]

    qs = provisioning_infrastructure_domain_query_service.ProvisioningInfrastructureDomainQueryService(
        parameter_srv=ps_mock,
        instance_mgmt_srv=im_mock,
        all_subnets_selector=lambda routes, subnets: [subnets[0]],
        spoke_account_vpc_id_param_name="test-param",
        service_name="test-service",
    )

    # ACT
    subnets = qs.get_provisioning_subnets_in_account(
        account_id=account_id_value_object.from_str("001234567890"), region=region_value_object.from_str("us-east-1")
    )

    # ASSERT
    assertpy.assert_that(subnets).is_length(1)
    im_mock.describe_vpc_subnets.assert_called_once_with(
        aws_account_id="001234567890", region="us-east-1", vpc_id="vpc-123", user_id="test-service"
    )
    im_mock.describe_vpc_route_tables.assert_called_once_with(
        aws_account_id="001234567890", region="us-east-1", vpc_id="vpc-123", user_id="test-service"
    )
