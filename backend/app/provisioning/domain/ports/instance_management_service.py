from abc import ABC, abstractmethod

from app.provisioning.domain.model import (
    block_device_mappings,
    instance_details,
    network_interface,
    network_route_table,
    network_subnet,
)


class InstanceManagementService(ABC):
    @abstractmethod
    def get_instance_state(self, user_id: str, aws_account_id: str, region: str, instance_id: str) -> str | None: ...

    @abstractmethod
    def get_instance_platform(self, user_id: str, aws_account_id: str, region: str, instance_id: str) -> str | None: ...

    @abstractmethod
    def get_instance_details(
        self, user_id: str, aws_account_id: str, region: str, instance_id: str
    ) -> instance_details.InstanceDetails | None: ...

    @abstractmethod
    def get_block_device_mappings(
        self,
        user_id: str,
        aws_account_id: str,
        region: str,
        instance_id: str,
    ) -> block_device_mappings.BlockDeviceMappings: ...

    @abstractmethod
    def start_instance(self, user_id: str, aws_account_id: str, region: str, instance_id: str) -> str: ...

    @abstractmethod
    def stop_instance(self, user_id: str, aws_account_id: str, region: str, instance_id: str) -> str: ...

    @abstractmethod
    def get_user_security_group_id(self, user_id: str, aws_account_id: str, region: str, vpc_id: str) -> str | None: ...

    @abstractmethod
    def create_user_security_group(self, user_id: str, aws_account_id: str, region: str, vpc_id: str) -> str: ...

    @abstractmethod
    def describe_vpc_route_tables(
        self, user_id: str, aws_account_id: str, region: str, vpc_id: str
    ) -> list[network_route_table.NetworkRouteTable]: ...

    @abstractmethod
    def describe_vpc_subnets(
        self, user_id: str, aws_account_id: str, region: str, vpc_id: str
    ) -> list[network_subnet.NetworkSubnet]: ...

    @abstractmethod
    def authorize_user_ip_address(
        self,
        user_id: str,
        aws_account_id: str,
        region: str,
        connection_option: str,
        ip_address: str,
        port: int,
        to_port: int,
        protocol: str,
        user_sg_id: str,
    ) -> None: ...

    @abstractmethod
    def get_user_ip_address_rule_id(
        self,
        user_id: str,
        aws_account_id: str,
        region: str,
        connection_option: str,
        port: int,
        to_port: int,
        protocol: str,
        user_sg_id: str,
    ) -> str | None: ...

    @abstractmethod
    def revoke_user_ip_address(
        self, user_id: str, aws_account_id: str, region: str, sg_rule_id: str, user_sg_id: str
    ) -> None: ...

    @abstractmethod
    def detach_instance_volume(
        self, user_id: str, aws_account_id: str, region: str, instance_id: str, volume_id: str
    ) -> None: ...

    @abstractmethod
    def attach_instance_volume(
        self, user_id: str, aws_account_id: str, region: str, instance_id: str, volume_id: str, device_name: str
    ) -> None: ...

    @abstractmethod
    def get_instance_state_reason(
        self, user_id: str, aws_account_id: str, region: str, instance_id: str
    ) -> str | None: ...

    @abstractmethod
    def describe_subnet_interfaces(
        self, user_id: str, aws_account_id: str, region: str, subnet_id: str
    ) -> list[network_interface.NetworkInterface]: ...

    @abstractmethod
    def describe_subnet(
        self, user_id: str, aws_account_id: str, region: str, subnet_id: str
    ) -> network_subnet.NetworkSubnet | None: ...
