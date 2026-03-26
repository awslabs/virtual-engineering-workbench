from typing import Optional

from mypy_boto3_route53 import client

from app.projects.adapters.exceptions import adapter_exception
from app.projects.domain.ports import dns_service
from app.shared.adapters.boto.boto_provider import BotoProviderOptions, ProviderType


class AWSDNSService(dns_service.DNSService):
    def __init__(
        self,
        route53_provider: ProviderType[client.Route53Client],
    ):
        self._provider = route53_provider

    def associate_vpc_with_zone(
        self,
        vpc_id: str,
        vpc_region: str,
        zone_id: str,
        provider_options: Optional[BotoProviderOptions] = None,
    ) -> None:
        route53_client = self._provider(provider_options)

        route53_client.associate_vpc_with_hosted_zone(
            HostedZoneId=zone_id, VPC={"VPCRegion": vpc_region, "VPCId": vpc_id}
        )

    def create_dns_record(
        self,
        name: str,
        ttl: int,
        type: str,
        value: str,
        zone_id: str,
        provider_options: Optional[BotoProviderOptions] = None,
    ) -> None:
        route53_client = self._provider(provider_options)

        route53_client.change_resource_record_sets(
            ChangeBatch={
                "Changes": [
                    {
                        "Action": "UPSERT",
                        "ResourceRecordSet": {
                            "Name": name,
                            "ResourceRecords": [{"Value": value}],
                            "Type": type,
                            "TTL": ttl,
                        },
                    },
                ],
            },
            HostedZoneId=zone_id,
        )

    def create_private_zone(
        self,
        comment: str,
        dns_name: str,
        vpc_id: str,
        vpc_region: str,
        provider_options: Optional[BotoProviderOptions] = None,
    ) -> str:
        route53_client = self._provider(provider_options)

        private_zone = route53_client.create_hosted_zone(
            CallerReference=f"{dns_name}-{vpc_id}-{vpc_region}",
            HostedZoneConfig={
                "Comment": comment,
                "PrivateZone": True,
            },
            Name=dns_name,
            VPC={"VPCRegion": vpc_region, "VPCId": vpc_id},
        )

        return private_zone.get("HostedZone").get("Id")

    def get_zone_id(
        self,
        dns_name: str,
        provider_options: Optional[BotoProviderOptions] = None,
    ) -> Optional[str]:
        route53_client = self._provider(provider_options)

        response = route53_client.list_hosted_zones_by_name(DNSName=dns_name)
        zones = response.get("HostedZones")

        if len(zones) > 1:
            raise adapter_exception.AdapterException("Multiple hosted zones found.")

        return zones[0].get("Id") if len(zones) == 1 else None

    def is_vpc_associated_with_zone(
        self,
        dns_name: str,
        vpc_id: str,
        vpc_region: str,
        provider_options: Optional[BotoProviderOptions] = None,
    ) -> bool:
        route53_client = self._provider(provider_options)

        hosted_zones_list = list()
        kwargs = {"VPCId": vpc_id, "VPCRegion": vpc_region}

        while (hosted_zones := route53_client.list_hosted_zones_by_vpc(**kwargs)).get("NextToken", None):
            hosted_zones_list.extend(hosted_zones.get("HostedZoneSummaries"))

            kwargs["NextToken"] = hosted_zones.get("NextToken")

        hosted_zones_list.extend(hosted_zones.get("HostedZoneSummaries"))

        return any(hosted_zone for hosted_zone in hosted_zones_list if hosted_zone.get("Name") == f"{dns_name}.")
