import hashlib
from typing import Any, Literal, Optional

import boto3
from botocore.exceptions import ClientError
from mypy_boto3_ec2.client import EC2Client
from mypy_boto3_license_manager.client import LicenseManagerClient
from mypy_boto3_organizations.client import OrganizationsClient
from mypy_boto3_ram.client import RAMClient
from mypy_boto3_sts.client import STSClient

from app.publishing.adapters.exceptions import adapter_exception
from app.publishing.domain.ports.license_manager_service import LicenseManagerService
from app.publishing.domain.read_models.license_details import LicenseDetails
from app.publishing.domain.read_models.license_grant_result import LicenseGrantResult
from app.shared.api import sts_api

EC2 = "ec2"
LICENSE_MANAGER = "license-manager"
ORGANIZATIONS = "organizations"
RAM = "ram"
STS = "sts"
SESSION_USER = "LicenseGrantManagement"
GRANT_ACTIVE_STATUS = "ACTIVE"
GRANT_DISABLED_STATUS = "DISABLED"
ACTIVATION_OVERRIDE: Literal["ALL_GRANTS_PERMITTED_BY_ISSUER"] = "ALL_GRANTS_PERMITTED_BY_ISSUER"
ALLOWED_OPERATIONS = ["CheckoutLicense", "ListPurchasedLicenses"]


class AwsLicenseManagerService(LicenseManagerService):
    def __init__(self, spoke_account_role: str, region: str, boto_session: Any = None):
        self._spoke_account_role = spoke_account_role
        self._region = region
        self._boto_session = boto_session
        self._account_id: str | None = None

    def __get_lm_client(self, region: str | None = None) -> LicenseManagerClient:
        _region = region or self._region
        return (
            self._boto_session.client(LICENSE_MANAGER, region_name=_region)
            if self._boto_session
            else boto3.client(LICENSE_MANAGER, region_name=_region)
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

    def __get_spoke_lm_client(self, account_id: str, region: str) -> LicenseManagerClient:
        with sts_api.STSAPI(account_id, region, self._spoke_account_role, SESSION_USER, self._boto_session) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            return (
                self._boto_session.client(
                    LICENSE_MANAGER,
                    region_name=region,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    aws_session_token=session_token,
                )
                if self._boto_session
                else boto3.client(
                    LICENSE_MANAGER,
                    region_name=region,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    aws_session_token=session_token,
                )
            )

    def __get_spoke_ec2_client(self, account_id: str, region: str) -> EC2Client:
        with sts_api.STSAPI(account_id, region, self._spoke_account_role, SESSION_USER, self._boto_session) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            return (
                self._boto_session.client(
                    EC2,
                    region_name=region,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    aws_session_token=session_token,
                )
                if self._boto_session
                else boto3.client(
                    EC2,
                    region_name=region,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    aws_session_token=session_token,
                )
            )

    def create_grant(
        self, license_arn: str, principal_arn: str, grant_name: str, home_region: str
    ) -> LicenseGrantResult:
        # Deterministic ClientToken for idempotent retries: same license + same grant name => same token
        token_seed = f"{license_arn}|{principal_arn}|{grant_name}"
        client_token = hashlib.sha256(token_seed.encode()).hexdigest()
        try:
            client = self.__get_lm_client(home_region)
            response = client.create_grant(
                ClientToken=client_token,
                GrantName=grant_name,
                LicenseArn=license_arn,
                Principals=[principal_arn],
                HomeRegion=home_region,
                AllowedOperations=ALLOWED_OPERATIONS,
            )
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "ValidationException" and "already has a grant" in str(e):
                existing = self._find_existing_grant(client, license_arn, principal_arn)
                if existing:
                    return existing
            raise adapter_exception.AdapterException(f"Failed to create license grant: {e}")

        return LicenseGrantResult(grantArn=response.get("GrantArn"), status=response.get("Status"))

    @staticmethod
    def _paged_grants(operation: Any, **kwargs: Any) -> list[dict]:
        """Every page of a License Manager grants call, following NextToken by hand.

        License Manager publishes no boto3 paginator for either
        ``list_distributed_grants`` or ``list_received_grants``
        (``can_paginate`` is False for both), so ``get_paginator`` raises
        ``OperationNotPageableError`` — and that is not a ``ClientError``, so it
        escapes the handlers around these calls rather than being reported.
        Reading a single page is just as wrong: a grant on a later page is
        invisible, which makes an existing grant look absent and the subsequent
        create fail with "already has a grant".
        """
        grants: list[dict] = []
        next_token: str | None = None
        while True:
            page = operation(**kwargs, **({"NextToken": next_token} if next_token else {}))
            grants.extend(page.get("Grants", []))
            next_token = page.get("NextToken")
            if not next_token:
                return grants

    def _find_existing_grant(
        self, client: LicenseManagerClient, license_arn: str, principal_arn: str
    ) -> Optional[LicenseGrantResult]:
        grants = self._paged_grants(
            client.list_distributed_grants,
            Filters=[{"Name": "LicenseArn", "Values": [license_arn]}],
        )
        for grant in grants:
            if grant.get("GranteePrincipalArn") == principal_arn and grant.get("GrantStatus") != "DELETED":
                return LicenseGrantResult(grantArn=grant["GrantArn"], status=grant["GrantStatus"])
        return None

    def accept_grant(self, grant_arn: str, home_region: str, spoke_account_id: str) -> None:
        try:
            spoke_client = self.__get_spoke_lm_client(spoke_account_id, home_region)
            grants = spoke_client.list_received_grants(GrantArns=[grant_arn]).get("Grants", [])
            # No received grant means there is nothing to accept. Calling
            # accept_grant anyway fails against the API, and previously happened
            # on exactly this path, because a missing grant left current_status
            # as None, which is neither ACTIVE nor DISABLED.
            if not grants:
                raise adapter_exception.AdapterException(
                    f"Cannot accept license grant {grant_arn}: the spoke account has not received it"
                )

            current_status = grants[0].get("GrantStatus")

            if current_status == GRANT_ACTIVE_STATUS:
                return

            if current_status != GRANT_DISABLED_STATUS:
                spoke_client.accept_grant(GrantArn=grant_arn)

            spoke_client.create_grant_version(
                ClientToken=hashlib.sha256(f"activate|{grant_arn}".encode()).hexdigest(),
                GrantArn=grant_arn,
                Status=GRANT_ACTIVE_STATUS,
                Options={"ActivationOverrideBehavior": ACTIVATION_OVERRIDE},
            )
        except ClientError as e:
            raise adapter_exception.AdapterException(f"Failed to accept license grant {grant_arn}: {e}")

    def get_license(self, license_arn: str) -> LicenseDetails:
        try:
            response = self.__get_lm_client().get_license(LicenseArn=license_arn)
        except ClientError as e:
            raise adapter_exception.AdapterException(f"Failed to get license {license_arn}: {e}")

        lic = response.get("License", {})
        return LicenseDetails(
            licenseArn=lic.get("LicenseArn"),
            licenseName=lic.get("LicenseName"),
            productName=lic.get("ProductName"),
            status=lic.get("Status"),
            homeRegion=lic.get("HomeRegion", self._region),
        )

    def verify_image_accessible(self, ami_id: str, region: str, spoke_account_id: str) -> bool:
        try:
            spoke_ec2 = self.__get_spoke_ec2_client(spoke_account_id, region)
            response = spoke_ec2.describe_images(ImageIds=[ami_id])
            return len(response.get("Images", [])) > 0
        except ClientError as e:
            # Only swallow "not found"; re-raise throttling, auth, and other infrastructure errors.
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("InvalidAMIID.NotFound", "InvalidAMIID.Malformed"):
                return False
            raise adapter_exception.AdapterException(f"Failed to verify image {ami_id}: {e}")

    def has_active_received_grant(self, license_arn: str, spoke_account_id: str, home_region: str) -> bool:
        try:
            spoke_client = self.__get_spoke_lm_client(spoke_account_id, home_region)
            grants = self._paged_grants(
                spoke_client.list_received_grants,
                Filters=[
                    {"Name": "LicenseArn", "Values": [license_arn]},
                    {"Name": "GrantStatus", "Values": [GRANT_ACTIVE_STATUS]},
                ],
            )
            return bool(grants)
        except ClientError as e:
            raise adapter_exception.AdapterException(
                f"Failed to list received grants for license {license_arn} in account {spoke_account_id}: {e}"
            )

    def _resolve_account_id(self) -> str:
        if self._account_id is None:
            try:
                self._account_id = self.__get_sts_client().get_caller_identity()["Account"]
            except ClientError as e:
                raise adapter_exception.AdapterException(f"Failed to resolve caller account id: {e}")
        return self._account_id

    def _get_management_account_id(self) -> str | None:
        try:
            organization = self.__get_organizations_client().describe_organization().get("Organization", {})
        except ClientError as e:
            raise adapter_exception.AdapterException(f"Failed to describe organization: {e}")

        # AWS is replacing the legacy MasterAccountId response name with
        # ManagementAccountId. Accept either during the SDK transition.
        return organization.get("ManagementAccountId") or organization.get("MasterAccountId")

    def _list_resource_shares(self, resource_share_arn: str, resource_owner: str) -> list[dict]:
        shares: list[dict] = []
        next_token: str | None = None
        try:
            ram_client = self.__get_ram_client()
            while True:
                kwargs = {"nextToken": next_token} if next_token else {}
                response = ram_client.get_resource_shares(
                    resourceOwner=resource_owner,
                    resourceShareArns=[resource_share_arn],
                    **kwargs,
                )
                shares.extend(response.get("resourceShares", []))
                next_token = response.get("nextToken")
                if not next_token:
                    return shares
        except ClientError as e:
            raise adapter_exception.AdapterException(f"Failed to list License Manager RAM resource share: {e}")

    def can_distribute_license(self) -> bool:
        """Whether this hub can distribute a received licence to an organization account."""
        try:
            settings = self.__get_lm_client().get_service_settings() or {}
        except ClientError as e:
            raise adapter_exception.AdapterException(f"Failed to read License Manager service settings: {e}")

        org_config = settings.get("OrganizationConfiguration") or {}
        resource_share_arn = settings.get("LicenseManagerResourceShareArn")
        if not org_config.get("EnableIntegration") or not resource_share_arn:
            return False

        management_account_id = self._get_management_account_id()
        if not management_account_id:
            return False

        caller_account_id = self._resolve_account_id()
        resource_owner = "SELF" if caller_account_id == management_account_id else "OTHER-ACCOUNTS"
        share_is_active = any(
            share.get("resourceShareArn") == resource_share_arn
            and share.get("status") == "ACTIVE"
            and share.get("owningAccountId") == management_account_id
            for share in self._list_resource_shares(resource_share_arn, resource_owner)
        )
        # License Manager entitlement distribution is a management-account
        # operation. A member can see the shared RAM resource, but cannot re-grant.
        return caller_account_id == management_account_id and share_is_active
