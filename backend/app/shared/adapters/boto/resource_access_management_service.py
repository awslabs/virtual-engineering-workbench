from abc import ABC

from app.shared.adapters.boto.boto_provider import BotoProviderOptions


class ResourceAccessManagementService(ABC):

    def associate_resource_share(
        self,
        resource_share_arn: str,
        principals: list[str] | None = None,
        provider_options: BotoProviderOptions | None = None,
    ) -> None: ...

    def get_resource_shares(self, tag_name: str, provider_options: BotoProviderOptions | None = None) -> list[str]: ...
