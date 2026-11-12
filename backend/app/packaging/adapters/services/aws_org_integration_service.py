from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError
from mypy_boto3_license_manager.client import LicenseManagerClient
from mypy_boto3_organizations.client import OrganizationsClient
from mypy_boto3_ram.client import RAMClient
from mypy_boto3_sts.client import STSClient

from app.packaging.adapters.exceptions import adapter_exception
from app.packaging.domain.ports.org_integration_service import OrgIntegrationService

LICENSE_MANAGER = "license-manager"
ORGANIZATIONS = "organizations"
RAM = "ram"
STS = "sts"


class AwsOrgIntegrationService(OrgIntegrationService):
    def __init__(self, region: str, boto_session: Any = None):
        self._region = region
        self._boto_session = boto_session
        self._account_id: Optional[str] = None

    def __get_license_manager_client(self) -> LicenseManagerClient:
        return (
            self._boto_session.client(LICENSE_MANAGER, region_name=self._region)
            if self._boto_session
            else boto3.client(LICENSE_MANAGER, region_name=self._region)
        )

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

    def _get_resource_share_arn(self) -> str | None:
        try:
            settings = self.__get_license_manager_client().get_service_settings() or {}
        except ClientError as e:
            raise adapter_exception.AdapterException(f"Failed to read License Manager service settings: {e}")

        org_config = settings.get("OrganizationConfiguration") or {}
        if not org_config.get("EnableIntegration"):
            return None
        return settings.get("LicenseManagerResourceShareArn")

    def _get_management_account_id(self) -> str | None:
        try:
            organization = self.__get_organizations_client().describe_organization().get("Organization", {})
        except ClientError as e:
            raise adapter_exception.AdapterException(f"Failed to describe organization: {e}")
        return organization.get("ManagementAccountId") or organization.get("MasterAccountId")

    def _list_resource_shares(self, resource_share_arn: str, resource_owner: str) -> list[dict]:
        shares: list[dict] = []
        next_token: str | None = None
        try:
            client = self.__get_ram_client()
            while True:
                kwargs = {"nextToken": next_token} if next_token else {}
                response = client.get_resource_shares(
                    resourceOwner=resource_owner,
                    resourceShareArns=[resource_share_arn],
                    **kwargs,
                )
                shares.extend(response.get("resourceShares", []))
                next_token = response.get("nextToken")
                if not next_token:
                    return shares
        except ClientError as e:
            raise adapter_exception.AdapterException(f"Failed to list RAM resource shares: {e}")

    def is_license_manager_org_integration_active(self) -> bool:
        resource_share_arn = self._get_resource_share_arn()
        if not resource_share_arn:
            return False

        management_account_id = self._get_management_account_id()
        if not management_account_id:
            return False

        caller_account_id = self.__resolve_account_id()
        resource_owner = "SELF" if caller_account_id == management_account_id else "OTHER-ACCOUNTS"
        share_is_active = any(
            share.get("resourceShareArn") == resource_share_arn
            and share.get("owningAccountId") == management_account_id
            and share.get("status") == "ACTIVE"
            for share in self._list_resource_shares(resource_share_arn, resource_owner)
        )
        # A member sees the management account's resource share through RAM, but
        # License Manager allows entitlement distribution only from management.
        return caller_account_id == management_account_id and share_is_active
