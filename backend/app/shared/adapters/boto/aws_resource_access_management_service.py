from mypy_boto3_ram import client

from app.shared.adapters.boto import resource_access_management_service
from app.shared.adapters.boto.boto_provider import BotoProviderOptions, ProviderType


class AWSResourceAccessManagementService(resource_access_management_service.ResourceAccessManagementService):

    def __init__(
        self,
        ram_provider: ProviderType[client.RAMClient],
    ):
        self._provider = ram_provider

    def associate_resource_share(
        self,
        resource_share_arn: str,
        principals: list[str] | None = None,
        provider_options: BotoProviderOptions | None = None,
    ) -> None:
        ram_client = self._provider(provider_options)

        ram_client.associate_resource_share(
            resourceShareArn=resource_share_arn,
            principals=principals,
        )

    def get_resource_shares(self, tag_name: str, provider_options: BotoProviderOptions | None = None) -> list[str]:
        ram_client = self._provider(provider_options)

        response = ram_client.get_resource_shares(
            resourceOwner="SELF",
            resourceShareStatus="ACTIVE",
            maxResults=500,
            tagFilters=[
                {
                    "tagKey": tag_name,
                    "tagValues": ["true"],
                },
            ],
        )

        return [r.get("resourceShareArn") for r in response.get("resourceShares", [])]
