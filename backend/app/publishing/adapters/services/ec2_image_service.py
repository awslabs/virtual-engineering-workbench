from __future__ import annotations

from typing import TYPE_CHECKING, Any

import boto3
from mypy_boto3_ec2 import client

from app.publishing.adapters.exceptions import adapter_exception
from app.publishing.domain.ports import image_service
from app.shared.api import sts_api

if TYPE_CHECKING:
    from mypy_boto3_kms import client as kms_client

SESSION_USER = "ProductPublishingProcess"


class EC2ImageService(image_service.ImageService):
    def __init__(
        self,
        image_srv_role: str,
        image_srv_aws_account_id: str,
        image_srv_key_name: str,
        image_srv_region: str,
        boto_session: Any = None,
    ):
        self._image_srv_role = image_srv_role
        self._image_srv_aws_account_id = image_srv_aws_account_id
        self._image_srv_key_name = image_srv_key_name
        self._image_srv_region = image_srv_region
        self._boto_session = boto_session

    def _create_ec2_client(
        self, region: str, access_key_id: str, secret_access_key: str, session_token: str
    ) -> client.EC2Client:
        session = self._boto_session or boto3
        return session.client(
            "ec2",
            region_name=region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            aws_session_token=session_token,
        )

    def _create_kms_client(
        self, region: str, access_key_id: str, secret_access_key: str, session_token: str
    ) -> kms_client.KMSClient:
        session = self._boto_session or boto3
        return session.client(
            "kms",
            region_name=region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            aws_session_token=session_token,
        )

    def copy_ami(self, region: str, original_ami_id: str, ami_name: str, ami_description: str) -> str:
        with sts_api.STSAPI(
            self._image_srv_aws_account_id, region, self._image_srv_role, SESSION_USER, self._boto_session
        ) as sts:
            access_key_id, secret_access_key, session_token = sts.get_temp_creds()
            ec2_client = self._create_ec2_client(region, access_key_id, secret_access_key, session_token)

            response = ec2_client.copy_image(
                Name=ami_name,
                SourceImageId=original_ami_id,
                SourceRegion=self._image_srv_region,
                ClientToken=original_ami_id,
                CopyImageTags=True,
                Description=ami_description,
                KmsKeyId=f"alias/{self._image_srv_key_name}",
                Encrypted=True,
            )

        return response["ImageId"]

    def share_ami(self, region: str, copied_ami_id: str, aws_account_id: str) -> None:
        with sts_api.STSAPI(
            self._image_srv_aws_account_id, region, self._image_srv_role, SESSION_USER, self._boto_session
        ) as sts:
            access_key_id, secret_access_key, session_token = sts.get_temp_creds()
            ec2_client = self._create_ec2_client(region, access_key_id, secret_access_key, session_token)

            ec2_client.modify_image_attribute(
                ImageId=copied_ami_id, LaunchPermission={"Add": [{"UserId": aws_account_id}]}
            )

    def grant_kms_access(self, region: str, ami_id: str, aws_account_id: str) -> None:
        """Grants the spoke account decrypt access to KMS keys used to encrypt the AMI's EBS snapshots."""
        with sts_api.STSAPI(
            self._image_srv_aws_account_id, region, self._image_srv_role, SESSION_USER, self._boto_session
        ) as sts:
            access_key_id, secret_access_key, session_token = sts.get_temp_creds()

            ec2 = self._create_ec2_client(region, access_key_id, secret_access_key, session_token)
            kms = self._create_kms_client(region, access_key_id, secret_access_key, session_token)

            response = ec2.describe_images(ImageIds=[ami_id], Owners=["self"])
            if not response["Images"]:
                raise adapter_exception.AdapterException(f"Image {ami_id} not found.")

            kms_key_ids = set()
            for bdm in response["Images"][0].get("BlockDeviceMappings", []):
                ebs = bdm.get("Ebs", {})
                if ebs.get("Encrypted") and ebs.get("KmsKeyId"):
                    kms_key_ids.add(ebs["KmsKeyId"])

            for key_id in kms_key_ids:
                kms.create_grant(
                    KeyId=key_id,
                    GranteePrincipal=f"arn:aws:iam::{aws_account_id}:root",
                    Operations=[
                        "Decrypt",
                        "DescribeKey",
                        "CreateGrant",
                        "GenerateDataKey",
                        "ReEncryptFrom",
                        "ReEncryptTo",
                    ],
                )

    def get_copied_ami_status(self, copied_ami_id: str, region: str) -> str:
        with sts_api.STSAPI(
            self._image_srv_aws_account_id, region, self._image_srv_role, SESSION_USER, self._boto_session
        ) as sts:
            access_key_id, secret_access_key, session_token = sts.get_temp_creds()
            ec2_client = self._create_ec2_client(region, access_key_id, secret_access_key, session_token)

            response = ec2_client.describe_images(ImageIds=[copied_ami_id], Owners=["self"])

            if not response["Images"]:
                raise adapter_exception.AdapterException(f"Image {copied_ami_id} not found.")

            if len(response["Images"]) > 1:
                raise adapter_exception.AdapterException(f"More than 1 image returned. ({response['Images']})")

        return response["Images"][0]["State"]
