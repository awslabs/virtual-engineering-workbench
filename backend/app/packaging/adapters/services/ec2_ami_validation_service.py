from typing import Any

import boto3
from botocore.exceptions import ClientError
from mypy_boto3_ec2.client import EC2Client

from app.packaging.adapters.exceptions import adapter_exception
from app.packaging.domain.ports.ami_validation_service import AmiValidationService
from app.packaging.domain.read_models.ami_description import AmiDescription
from app.shared.api import sts_api

EC2 = "ec2"
SESSION_USER = "AmiImportValidation"


class Ec2AmiValidationService(AmiValidationService):
    def __init__(
        self,
        admin_role: str,
        ami_factory_account_id: str,
        region: str,
        boto_session: Any = None,
    ):
        self._admin_role = admin_role
        self._ami_factory_account_id = ami_factory_account_id
        self._region = region
        self._boto_session = boto_session

    def __get_image_service_ec2_client(self) -> EC2Client:
        with sts_api.STSAPI(
            self._ami_factory_account_id,
            self._region,
            self._admin_role,
            SESSION_USER,
            self._boto_session,
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            return (
                self._boto_session.client(
                    EC2,
                    region_name=self._region,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    aws_session_token=session_token,
                )
                if self._boto_session
                else boto3.client(
                    EC2,
                    region_name=self._region,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    aws_session_token=session_token,
                )
            )

    def __get_local_ec2_client(self) -> EC2Client:
        return (
            self._boto_session.client(EC2, region_name=self._region)
            if self._boto_session
            else boto3.client(EC2, region_name=self._region)
        )

    def __to_ami_description(self, img: dict) -> AmiDescription:
        return AmiDescription(
            amiId=img.get("ImageId"),
            state=img.get("State"),
            platform=img.get("PlatformDetails"),
            architecture=img.get("Architecture"),
            name=img.get("Name"),
            description=img.get("Description"),
            ownerId=img.get("OwnerId"),
            region=self._region,
            blockDeviceMappings=img.get("BlockDeviceMappings", []),
            productCodes=img.get("ProductCodes", []),
        )

    def describe_image(self, ami_id: str) -> AmiDescription:
        try:
            ec2_client: EC2Client = self.__get_image_service_ec2_client()
            response = ec2_client.describe_images(ImageIds=[ami_id])
        except ClientError as e:
            raise adapter_exception.AdapterException(f"Failed to describe AMI {ami_id} in Image Service account: {e}")

        images = response.get("Images", [])
        if not images:
            raise adapter_exception.AdapterException(f"AMI {ami_id} not found in Image Service account.")
        return self.__to_ami_description(images[0])

    def list_available_amis(self) -> list[AmiDescription]:
        try:
            ec2_client: EC2Client = self.__get_image_service_ec2_client()
            response = ec2_client.describe_images(
                Owners=["self"],
                Filters=[{"Name": "state", "Values": ["available"]}],
            )
        except ClientError as e:
            raise adapter_exception.AdapterException(f"Failed to list AMIs in Image Service account: {e}")

        return [self.__to_ami_description(img) for img in response.get("Images", [])]

    def describe_marketplace_image(self, ami_id: str) -> AmiDescription:
        try:
            ec2_client: EC2Client = self.__get_local_ec2_client()
            response = ec2_client.describe_images(ImageIds=[ami_id])
        except ClientError as e:
            raise adapter_exception.AdapterException(f"Failed to describe marketplace AMI {ami_id}: {e}")

        images = response.get("Images", [])
        if not images:
            raise adapter_exception.AdapterException(f"Marketplace AMI {ami_id} not found.")
        return self.__to_ami_description(images[0])

    def validate_marketplace_product_code(self, ami_id: str, expected_product_code: str) -> bool:
        desc = self.describe_marketplace_image(ami_id)
        return any(pc.productCodeId == expected_product_code for pc in desc.productCodes)
