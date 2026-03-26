from mypy_boto3_ec2 import client

from app.projects.adapters.exceptions import adapter_exception
from app.projects.domain.ports import network_service
from app.shared.adapters.boto.boto_provider import BotoProviderOptions, ProviderType


class EC2NetworkService(network_service.NetworkService):
    def __init__(self, ec2_provider: ProviderType[client.EC2Client]):
        self.__ec2_provider = ec2_provider

    def get_vpc_id_by_tag(
        self,
        tag_name: str,
        tag_value: str,
        provider_options: BotoProviderOptions | None = None,
    ) -> str:
        ec2_client: client.EC2Client = self.__ec2_provider(provider_options)

        response = ec2_client.describe_vpcs(
            Filters=[
                {
                    "Name": f"tag:{tag_name}",
                    "Values": [tag_value],
                }
            ]
        )

        vpcs = response.get("Vpcs", [])
        if not vpcs:
            raise adapter_exception.AdapterException(f"No VPC found with tag {tag_name} and value {tag_value}")
        if len(vpcs) > 1:
            raise adapter_exception.AdapterException(f"Multiple VPCs found with tag {tag_name} and value {tag_value}")
        vpc_id = response["Vpcs"][0]["VpcId"]
        return vpc_id

    def get_vpcs_ids(
        self,
        provider_options: BotoProviderOptions | None = None,
    ) -> list[str]:
        ec2_client: client.EC2Client = self.__ec2_provider(provider_options)

        response = ec2_client.describe_vpcs()
        vpcs = response.get("Vpcs", [])

        return [vpc.get("VpcId") for vpc in vpcs]

    def get_subnets_by_tag(
        self,
        tag_name: str,
        tag_value: str,
        vpc_id: str | None = None,
        provider_options: BotoProviderOptions | None = None,
    ) -> list[dict]:
        ec2_client: client.EC2Client = self.__ec2_provider(provider_options)

        filters = [{"Name": f"tag:{tag_name}", "Values": [tag_value]}]

        if vpc_id:
            filters.append({"Name": "vpc-id", "Values": [vpc_id]})

        response = ec2_client.describe_subnets(Filters=filters)

        subnets = response.get("Subnets", [])
        return subnets
