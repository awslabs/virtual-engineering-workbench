import typing

from mypy_boto3_ec2 import client

from app.provisioning.domain.model import (
    block_device_mappings,
    instance_details,
    network_interface,
    network_route_table,
    network_subnet,
)
from app.provisioning.domain.ports import instance_management_service
from app.shared.adapters.auth import temporary_credential_provider


class EC2InstanceManagementServiceCachedInMemory(instance_management_service.InstanceManagementService):
    def __init__(
        self,
        inner: instance_management_service.InstanceManagementService,
        ec2_boto_client_provider: typing.Callable[[str, str, str], client.EC2Client],
        request_context_manager: temporary_credential_provider.SupportsContextManager,
    ):
        self._inner = inner
        self._ec2_boto_client_provider = ec2_boto_client_provider
        self._request_context_manager = request_context_manager

    def get_instance_state_reason(self, **kwargs) -> str | None:
        return self._inner.get_instance_state_reason(**kwargs)

    def get_instance_state(self, user_id: str, aws_account_id: str, region: str, instance_id: str) -> str | None:
        cache_key = self.__get_cache_key(aws_account_id=aws_account_id, region=region)

        if "cached_ec2_instances" not in self._request_context_manager.context:
            self._request_context_manager.append_context(cached_ec2_instances={})

        if cache_key not in self._request_context_manager.context.get("cached_ec2_instances"):
            ec2_client = self._ec2_boto_client_provider(aws_account_id, region, user_id)

            query_kwargs = {
                "IncludeAllInstances": True,
            }

            instance_states = {}
            while "NextToken" in (response := ec2_client.describe_instance_status(**query_kwargs)):
                query_kwargs["NextToken"] = response.get("NextToken")
                instance_states |= self.__instance_array_to_dict(response)

            instance_states |= self.__instance_array_to_dict(response)

            self._request_context_manager.context.get("cached_ec2_instances")[cache_key] = instance_states

        return self._request_context_manager.context.get("cached_ec2_instances").get(cache_key).get(instance_id, None)

    def get_block_device_mappings(self, **kwargs) -> block_device_mappings.BlockDeviceMappings:
        return self._inner.get_block_device_mappings(**kwargs)

    def get_instance_platform(self, **kwargs) -> str:
        return self._inner.get_instance_platform(**kwargs)

    def get_instance_details(self, **kwargs) -> instance_details.InstanceDetails:
        return self._inner.get_instance_details(**kwargs)

    def start_instance(self, **kwargs) -> str:
        return self._inner.start_instance(**kwargs)

    def stop_instance(self, **kwargs) -> str:
        return self._inner.stop_instance(**kwargs)

    def get_user_security_group_id(self, **kwargs) -> str | None:
        return self._inner.get_user_security_group_id(**kwargs)

    def create_user_security_group(self, **kwargs) -> str:
        return self._inner.create_user_security_group(**kwargs)

    def authorize_user_ip_address(self, **kwargs) -> str:
        return self._inner.authorize_user_ip_address(**kwargs)

    def get_user_ip_address_rule_id(self, **kwargs) -> str:
        return self._inner.get_user_ip_address_rule_id(**kwargs)

    def revoke_user_ip_address(self, **kwargs) -> str:
        return self._inner.revoke_user_ip_address(**kwargs)

    def __instance_array_to_dict(self, response: dict) -> dict:
        return {i.get("InstanceId"): i.get("InstanceState").get("Name") for i in response.get("InstanceStatuses", [])}

    def __get_cache_key(self, aws_account_id: str, region: str) -> str:
        return f"{aws_account_id}#{region}"

    def describe_vpc_route_tables(self, **kwargs) -> list[network_route_table.NetworkRouteTable]:
        return self._inner.describe_vpc_route_tables(**kwargs)

    def describe_vpc_subnets(self, **kwargs) -> list[network_subnet.NetworkSubnet]:
        return self._inner.describe_vpc_subnets(**kwargs)

    def detach_instance_volume(self, **kwargs) -> None:
        return self._inner.detach_instance_volume(**kwargs)

    def attach_instance_volume(self, **kwargs) -> None:
        return self._inner.attach_instance_volume(**kwargs)

    def describe_subnet_interfaces(self, **kwargs) -> list[network_interface.NetworkInterface]:
        return self._inner.describe_subnet_interfaces(**kwargs)

    def describe_subnet(self, **kwargs) -> network_subnet.NetworkSubnet | None:
        return self._inner.describe_subnet(**kwargs)
