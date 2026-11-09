import hashlib
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError
from mypy_boto3_ec2.client import EC2Client
from mypy_boto3_license_manager.client import LicenseManagerClient

from app.publishing.adapters.exceptions import adapter_exception
from app.publishing.domain.ports.license_manager_service import LicenseManagerService
from app.publishing.domain.read_models.license_details import LicenseDetails
from app.publishing.domain.read_models.license_grant_result import LicenseGrantResult
from app.shared.api import sts_api

EC2 = "ec2"
LICENSE_MANAGER = "license-manager"
SESSION_USER = "LicenseGrantManagement"
GRANT_ACTIVE_STATUS = "ACTIVE"
GRANT_DISABLED_STATUS = "DISABLED"
ACTIVATION_OVERRIDE = "ALL_GRANTS_PERMITTED_BY_ISSUER"
ALLOWED_OPERATIONS = ["CheckoutLicense", "ListPurchasedLicenses"]


class AwsLicenseManagerService(LicenseManagerService):
    def __init__(self, spoke_account_role: str, region: str, boto_session: Any = None):
        self._spoke_account_role = spoke_account_role
        self._region = region
        self._boto_session = boto_session

    def __get_lm_client(self, region: str | None = None) -> LicenseManagerClient:
        _region = region or self._region
        return (
            self._boto_session.client(LICENSE_MANAGER, region_name=_region)
            if self._boto_session
            else boto3.client(LICENSE_MANAGER, region_name=_region)
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

    def _find_existing_grant(
        self, client: LicenseManagerClient, license_arn: str, principal_arn: str
    ) -> Optional[LicenseGrantResult]:
        response = client.list_distributed_grants(Filters=[{"Name": "LicenseArn", "Values": [license_arn]}])
        for grant in response.get("Grants", []):
            if grant.get("GranteePrincipalArn") == principal_arn and grant.get("GrantStatus") != "DELETED":
                return LicenseGrantResult(grantArn=grant["GrantArn"], status=grant["GrantStatus"])
        return None

    def accept_grant(self, grant_arn: str, home_region: str, spoke_account_id: str) -> None:
        try:
            spoke_client = self.__get_spoke_lm_client(spoke_account_id, home_region)
            grants = spoke_client.list_received_grants(GrantArns=[grant_arn]).get("Grants", [])
            current_status = grants[0].get("GrantStatus") if grants else None

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
            paginator = spoke_client.get_paginator("list_received_grants")
            for page in paginator.paginate(
                Filters=[
                    {"Name": "LicenseArn", "Values": [license_arn]},
                    {"Name": "GrantStatus", "Values": [GRANT_ACTIVE_STATUS]},
                ]
            ):
                if page.get("Grants"):
                    return True
            return False
        except ClientError as e:
            raise adapter_exception.AdapterException(
                f"Failed to list received grants for license {license_arn} in account {spoke_account_id}: {e}"
            )
