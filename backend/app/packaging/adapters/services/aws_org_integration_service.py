from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError
from mypy_boto3_organizations.client import OrganizationsClient
from mypy_boto3_ram.client import RAMClient
from mypy_boto3_sts.client import STSClient

from app.packaging.adapters.exceptions import adapter_exception
from app.packaging.domain.ports.org_integration_service import OrgIntegrationService

ORGANIZATIONS = "organizations"
RAM = "ram"
STS = "sts"
LM_RESOURCE_SHARE_NAME_PREFIX = "licenseManagerResourceShare"


class AwsOrgIntegrationService(OrgIntegrationService):
    def __init__(self, region: str, boto_session: Any = None):
        self._region = region
        self._boto_session = boto_session
        self._account_id: Optional[str] = None

    def __get_organizations_client(self) -> OrganizationsClient:
        return (
            self._boto_session.client(ORGANIZATIONS, region_name=self._region)
            if self._boto_session
            else boto3.client(ORGANIZATIONS, region_name=self._region)
        )

    def __get_ram_client(self) -> RAMClient:
        return (
            self._boto_session.client(RAM, region_name=self._region)
            if self._boto_session
            else boto3.client(RAM, region_name=self._region)
        )

    def __get_sts_client(self) -> STSClient:
        return (
            self._boto_session.client(STS, region_name=self._region)
            if self._boto_session
            else boto3.client(STS, region_name=self._region)
        )

    def __resolve_account_id(self) -> str:
        if self._account_id is None:
            try:
                self._account_id = self.__get_sts_client().get_caller_identity()["Account"]
            except ClientError as e:
                raise adapter_exception.AdapterException(f"Failed to resolve caller account id: {e}")
        return self._account_id

    def is_license_manager_org_integration_active(self) -> bool:
        self_account_id = self.__resolve_account_id()
        try:
            org = self.__get_organizations_client().describe_organization()
            management_account_id = org["Organization"]["MasterAccountId"]
        except ClientError as e:
            raise adapter_exception.AdapterException(f"Failed to describe organization: {e}")

        scope = "SELF" if self_account_id == management_account_id else "OTHER-ACCOUNTS"
        # get_resource_shares is paginated. Reading one page meant the License
        # Manager share could sit on a later page and the integration looked absent,
        # which blocks an import that should have been allowed.
        shares: list[dict] = []
        next_token: str | None = None
        try:
            client = self.__get_ram_client()
            while True:
                kwargs = {"nextToken": next_token} if next_token else {}
                response = client.get_resource_shares(resourceOwner=scope, **kwargs)
                shares.extend(response.get("resourceShares", []))
                next_token = response.get("nextToken")
                if not next_token:
                    break
        except ClientError as e:
            raise adapter_exception.AdapterException(f"Failed to list RAM resource shares: {e}")

        return any(
            s.get("owningAccountId") == management_account_id
            and s.get("status") == "ACTIVE"
            and (s.get("name") or "").startswith(LM_RESOURCE_SHARE_NAME_PREFIX)
            for s in shares
        )
