import typing

from botocore.exceptions import ClientError
from mypy_boto3_ec2 import client

from app.provisioning.adapters.exceptions import adapter_exception
from app.provisioning.domain.exceptions import insufficient_capacity_exception
from app.provisioning.domain.model import (
    block_device_mappings,
    instance_details,
    network_interface,
    network_route_table,
    network_subnet,
)
from app.provisioning.domain.ports import instance_management_service


class EC2InstanceManagementService(instance_management_service.InstanceManagementService):
    def __init__(
        self,
        ec2_boto_client_provider: typing.Callable[[str, str, str], client.EC2Client],
    ):
        self._ec2_boto_client_provider = ec2_boto_client_provider

    def get_instance_state_reason(self, user_id: str, aws_account_id: str, region: str, instance_id: str) -> str | None:
        """Returns the change status reason for the EC2 instance.

        Args:
            instance_id (str): EC2 instance id
            user_id (str): User ID
            aws_account_id (str): AWS Account ID
            region (str): AWS region
        """
        ec2_client = self._ec2_boto_client_provider(aws_account_id, region, user_id)

        response = ec2_client.describe_instances(InstanceIds=[instance_id])
        status_reason = response["Reservations"][0]["Instances"][0].get("StateReason")
        status_reason_message = None
        if status_reason:
            status_reason_message = status_reason.get("Message")

        return status_reason_message

    def get_instance_state(self, user_id: str, aws_account_id: str, region: str, instance_id: str) -> str | None:
        """Returns the status of an EC2 instance.

        Args:
            instance_id (str): EC2 instance id
            user_id (str): User ID
            aws_account_id (str): AWS Account ID
            region (str): AWS region

        Returns:
            instance_status (str): Current status of the EC2 instance
        """
        ec2_client = self._ec2_boto_client_provider(aws_account_id, region, user_id)

        query_kwargs = {"IncludeAllInstances": True, "InstanceIds": [instance_id]}

        instance_statuses = []
        while "NextToken" in (response := ec2_client.describe_instance_status(**query_kwargs)):
            query_kwargs["NextToken"] = response.get("NextToken")
            instance_statuses.extend(response.get("InstanceStatuses"))

        instance_statuses.extend(response.get("InstanceStatuses"))

        instance_status = next((i.get("InstanceState").get("Name") for i in instance_statuses), None)

        return instance_status

    def get_instance_platform(self, user_id: str, aws_account_id: str, region: str, instance_id: str) -> str | None:
        """Returns the platform of an EC2 instance.

        Args:
            instance_id (str): EC2 instance id
            user_id (str): User ID
            aws_account_id (str): AWS Account ID
            region (str): AWS region

        Returns:
            platform (str): Platform/Operating System of the EC2 instance
        """
        ec2_client = self._ec2_boto_client_provider(aws_account_id, region, user_id)

        response = ec2_client.describe_instances(InstanceIds=[instance_id])
        ami_id = response["Reservations"][0]["Instances"][0]["ImageId"]
        ami_response = ec2_client.describe_images(ImageIds=[ami_id])
        platform_details = ami_response["Images"][0].get("PlatformDetails", None)

        return platform_details

    def get_instance_details(
        self, user_id: str, aws_account_id: str, region: str, instance_id: str
    ) -> instance_details.InstanceDetails | None:
        """Returns the details of an EC2 instance.

        Args:
            instance_id (str): EC2 instance id
            user_id (str): User ID
            aws_account_id (str): AWS Account ID
            region (str): AWS region

        Returns:
            instance_details (InstanceDetails): Details of EC2 instance
        """

        ec2_client = self._ec2_boto_client_provider(aws_account_id, region, user_id)

        response = ec2_client.describe_instances(InstanceIds=[instance_id])

        if not (reservations := response.get("Reservations", None)):
            return None

        if not (instances := reservations[0].get("Instances", None)):
            return None

        return instance_details.InstanceDetails.parse_obj(instances[0])

    def start_instance(self, user_id: str, aws_account_id: str, region: str, instance_id: str) -> str:
        """Starts the given EC2 instance by calling the EC2 API.

        Args:
            instance_id (str): EC2 instance id
            user_id (str): User ID
            aws_account_id (str): AWS Account ID
            region (str): AWS region

        Returns:
            current_state (str): Current state of the EC2 instance after starting
        """
        ec2_client = self._ec2_boto_client_provider(aws_account_id, region, user_id)

        try:
            response = ec2_client.start_instances(InstanceIds=[instance_id])
        except ClientError as error:
            error_code = error.response["Error"]["Code"]
            if error_code == "InsufficientInstanceCapacity":
                raise insufficient_capacity_exception.InsufficientCapacityException(
                    "Insufficient instance capacity error"
                )
        except Exception:
            raise adapter_exception.AdapterException("Unable to start the instance")

        current_state = response.get("StartingInstances")[0].get("CurrentState").get("Name")
        return current_state

    def stop_instance(self, user_id: str, aws_account_id: str, region: str, instance_id: str) -> str:
        """Stops the given EC2 instance by calling the EC2 API.

        Args:
            instance_id (str): EC2 instance id
            user_id (str): User ID
            aws_account_id (str): AWS Account ID
            region (str): AWS region

        Returns:
            current_state (str): Current state of the EC2 instance after stopping
        """

        ec2_client = self._ec2_boto_client_provider(aws_account_id, region, user_id)
        response = ec2_client.stop_instances(InstanceIds=[instance_id])
        current_state = response.get("StoppingInstances")[0].get("CurrentState").get("Name")

        return current_state

    def get_user_security_group_id(self, user_id: str, aws_account_id: str, region: str, vpc_id: str) -> str | None:
        """Returns the user security group id if created, otherwise returns None.

        Args:
            user_id (str): User ID
            aws_account_id (str): AWS Account ID
            region (str): AWS region
            vpc_id (str): VPC ID

        Returns:
            security_group_id (str): User security group ID
        """
        ec2_client = self._ec2_boto_client_provider(aws_account_id, region, user_id)
        response = ec2_client.describe_security_groups(
            Filters=[
                {"Name": "vpc-id", "Values": [vpc_id]},
                {
                    "Name": "group-name",
                    "Values": [
                        self.__get_user_security_group_name(user_id, aws_account_id),
                    ],
                },
            ],
        )
        if response and response.get("SecurityGroups"):
            return response["SecurityGroups"][0]["GroupId"]
        return None

    def get_block_device_mappings(
        self, user_id: str, aws_account_id: str, region: str, instance_id: str
    ) -> block_device_mappings.BlockDeviceMappings:
        ec2_client = self._ec2_boto_client_provider(aws_account_id, region, user_id)
        response = ec2_client.describe_instances(InstanceIds=[instance_id])

        instance = response.get("Reservations")[0].get("Instances")[0]
        root_volume = instance["RootDeviceName"]

        return block_device_mappings.BlockDeviceMappings(
            rootDeviceName=root_volume,
            mappings=[
                block_device_mappings.BlockDevice(deviceName=device["DeviceName"], volumeId=device["Ebs"]["VolumeId"])
                for device in instance["BlockDeviceMappings"]
            ],
        )

    def create_user_security_group(self, user_id: str, aws_account_id: str, region: str, vpc_id: str) -> str:
        """Creates the user security group and returns its id.

        Args:
            user_id (str): User ID
            aws_account_id (str): AWS Account ID
            region (str): AWS region
            vpc_id (str): VPC ID

        Returns:
            security_group_id (str): User security group ID
        """
        ec2_client = self._ec2_boto_client_provider(aws_account_id, region, user_id)
        response = ec2_client.create_security_group(
            GroupName=self.__get_user_security_group_name(user_id, aws_account_id),
            VpcId=vpc_id,
            Description="User based security group for workbenches and virtual targets",
            TagSpecifications=[
                {"ResourceType": "security-group", "Tags": [{"Key": "vew:securityGroup:ownerId", "Value": user_id}]}
            ],
        )
        if not response or not response.get("GroupId"):
            raise adapter_exception.AdapterException(
                f"Unable to create user security group for user {user_id} in aws account {aws_account_id}"
            )
        return response["GroupId"]

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
    ) -> None:
        """Authorizes the user current IP address to access a specified port range and protocol.

        Args:
            user_id (str): User ID
            aws_account_id (str): AWS Account ID
            region (str): AWS region
            connection_option (str): The connection option this rule is for
            ip_address (str): User IP address
            port (int): The from-port authorized in this rule
            to_port (int): The to-port authorized in this rule
            protocol (str): The protocol authorized in this rule
            user_sg_id (str): User security group ID
        """

        ec2_client = self._ec2_boto_client_provider(aws_account_id, region, user_id)
        name = self.__get_user_security_group_rule_name(
            connection_option=connection_option, port=port, to_port=to_port, protocol=protocol
        )

        try:
            ec2_client.authorize_security_group_ingress(
                CidrIp=ip_address,
                FromPort=port,
                GroupId=user_sg_id,
                IpProtocol=protocol,
                ToPort=to_port,
                TagSpecifications=[
                    {
                        "ResourceType": "security-group-rule",
                        "Tags": [
                            {
                                "Key": "GroupId",
                                "Value": user_sg_id,
                            },
                            {
                                "Key": "Name",
                                "Value": name,
                            },
                        ],
                    }
                ],
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "InvalidPermission.Duplicate":
                return
            raise

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
    ) -> str | None:
        """Returns the ID of a specific user IP address rule based on its name.

        Args:
            user_id (str): User ID
            aws_account_id (str): AWS Account ID
            region (str): AWS region
            connection_option (str): The connection option included in the rule name
            port (int): The from-port included in the rule name
            to_port (int): The to-port included in the rule name
            protocol (str): The protocol included in the rule name
            user_sg_id (str): User security group ID

        Returns:
            security_group_rule_id (str): User security group rule ID
        """

        ec2_client = self._ec2_boto_client_provider(aws_account_id, region, user_id)
        name = self.__get_user_security_group_rule_name(
            connection_option=connection_option, port=port, to_port=to_port, protocol=protocol
        )
        response = ec2_client.describe_security_group_rules(
            Filters=[
                {
                    "Name": "tag:GroupId",
                    "Values": [user_sg_id],
                },
                {
                    "Name": "tag:Name",
                    "Values": [name],
                },
            ],
        )
        sg_rules = response.get("SecurityGroupRules")

        if len(sg_rules):
            return sg_rules[0].get("SecurityGroupRuleId")
        return None

    def revoke_user_ip_address(
        self,
        user_id: str,
        aws_account_id: str,
        region: str,
        sg_rule_id: str,
        user_sg_id: str,
    ) -> None:
        """Revokes access for the user stale IP address to a specified port and protocol.

        Args:
            user_id (str): User ID
            aws_account_id (str): AWS Account ID
            region (str): AWS region
            sg_rule_id (str): Security group rule ID
            user_sg_id (str): User security group ID
        """

        ec2_client = self._ec2_boto_client_provider(aws_account_id, region, user_id)

        ec2_client.revoke_security_group_ingress(
            GroupId=user_sg_id,
            SecurityGroupRuleIds=[sg_rule_id],
        )

    def __get_user_security_group_name(self, user_id: str, aws_account_id: str) -> str:
        return f"user-sg-{aws_account_id}-{user_id}"

    def __get_user_security_group_rule_name(
        self, connection_option: str, port: int, to_port: int, protocol: str
    ) -> str:
        if port == to_port:
            return f"{connection_option} - {protocol.upper()} {port}"
        return f"{connection_option} - {protocol.upper()} {port}-{to_port}"

    def describe_vpc_route_tables(
        self, user_id: str, aws_account_id: str, region: str, vpc_id: str
    ) -> list[network_route_table.NetworkRouteTable]:
        ec2_client = self._ec2_boto_client_provider(aws_account_id, region, user_id)

        query_kwargs = {
            "Filters": [
                {"Name": "vpc-id", "Values": [vpc_id]},
            ],
        }

        route_tables = []
        while "NextToken" in (response := ec2_client.describe_route_tables(**query_kwargs)):
            query_kwargs["NextToken"] = response.get("NextToken")
            route_tables.extend(response.get("RouteTables"))

        route_tables.extend(response.get("RouteTables"))

        return [network_route_table.NetworkRouteTable.parse_obj(rt) for rt in route_tables]

    def describe_vpc_subnets(
        self, user_id: str, aws_account_id: str, region: str, vpc_id: str
    ) -> list[network_subnet.NetworkSubnet]:
        ec2_client = self._ec2_boto_client_provider(aws_account_id, region, user_id)

        query_kwargs = {
            "Filters": [
                {"Name": "vpc-id", "Values": [vpc_id]},
            ],
        }

        subnets = []
        while "NextToken" in (response := ec2_client.describe_subnets(**query_kwargs)):
            query_kwargs["NextToken"] = response.get("NextToken")
            subnets.extend(response.get("Subnets"))

        subnets.extend(response.get("Subnets"))

        return [network_subnet.NetworkSubnet.parse_obj(s) for s in subnets]

    def detach_instance_volume(
        self, user_id: str, aws_account_id: str, region: str, instance_id: str, volume_id: str
    ) -> None:
        ec2_client = self._ec2_boto_client_provider(aws_account_id, region, user_id)

        ec2_client.detach_volume(InstanceId=instance_id, VolumeId=volume_id)

    def attach_instance_volume(
        self, user_id: str, aws_account_id: str, region: str, instance_id: str, volume_id: str, device_name: str
    ) -> None:
        ec2_client = self._ec2_boto_client_provider(aws_account_id, region, user_id)
        ec2_client.attach_volume(Device=device_name, InstanceId=instance_id, VolumeId=volume_id)

    def describe_subnet_interfaces(
        self, user_id: str, aws_account_id: str, region: str, subnet_id: str
    ) -> list[network_interface.NetworkInterface]:
        ec2_client = self._ec2_boto_client_provider(aws_account_id, region, user_id)
        return [
            network_interface.NetworkInterface.parse_obj(r)
            for r in ec2_client.describe_network_interfaces(Filters=[{"Name": "subnet-id", "Values": [subnet_id]}]).get(
                "NetworkInterfaces", []
            )
        ]

    def describe_subnet(
        self, user_id: str, aws_account_id: str, region: str, subnet_id: str
    ) -> network_subnet.NetworkSubnet | None:
        ec2_client = self._ec2_boto_client_provider(aws_account_id, region, user_id)
        sub = ec2_client.describe_subnets(SubnetIds=[subnet_id]).get("Subnets")
        return network_subnet.NetworkSubnet.parse_obj(sub[0]) if sub else None
