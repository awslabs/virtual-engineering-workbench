from typing import Any

import boto3
from botocore.exceptions import ClientError

from app.packaging.domain.ports import marketplace_image_service
from app.packaging.domain.read_models import marketplace_image
from app.shared.api import sts_api

SESSION_USER = "ProductPackagingProcess"
# The AWS Marketplace Agreement and Discovery APIs are only served from us-east-1.
MARKETPLACE_API_REGION = "us-east-1"
AMI_ALIAS_PARAMETER_NAME = "/aws/service/marketplace/{product_id}/latest"
ARCHITECTURES = {"x86_64": "amd64", "arm64": "arm64"}
# Recipes, recipe testing and the product templates all map the root volume at this device.
ROOT_DEVICE_NAME = "/dev/sda1"


class AWSMarketplaceImageService(marketplace_image_service.MarketplaceImageService):
    def __init__(
        self,
        admin_role: str,
        ami_factory_aws_account_id: str,
        region: str,
        boto_session: Any = None,
    ):
        self._admin_role = admin_role
        self._ami_factory_aws_account_id = ami_factory_aws_account_id
        self._region = region
        self._boto_session = boto_session

    def __get_clients(self, credentials: tuple[str, str, str]) -> dict[str, Any]:
        access_key_id, secret_access_key, session_token = credentials
        regions = {
            "marketplace-agreement": MARKETPLACE_API_REGION,
            "marketplace-discovery": MARKETPLACE_API_REGION,
            "ssm": self._region,
            "ec2": self._region,
        }
        return {
            service_name: (self._boto_session or boto3).client(
                service_name,
                region_name=region,
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                aws_session_token=session_token,
            )
            for service_name, region in regions.items()
        }

    def list_images(self) -> list[marketplace_image.MarketplaceImage]:
        """Lists the AMI products the AMI factory account is subscribed to that have an AMI alias in this region."""
        with sts_api.STSAPI(
            self._ami_factory_aws_account_id, self._region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            clients = self.__get_clients(sts.get_temp_creds())
            images = [
                self.__describe_image(clients, product_id)
                for product_id in self.__get_subscribed_ami_product_ids(clients)
            ]
            return [image for image in images if image]

    def get_image(self, product_id: str) -> marketplace_image.MarketplaceImage | None:
        with sts_api.STSAPI(
            self._ami_factory_aws_account_id, self._region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            clients = self.__get_clients(sts.get_temp_creds())
            if product_id not in self.__get_subscribed_ami_product_ids(clients):
                return None
            return self.__describe_image(clients, product_id)

    @staticmethod
    def __get_subscribed_ami_product_ids(clients: dict[str, Any]) -> list[str]:
        paginator = clients["marketplace-agreement"].get_paginator("search_agreements")
        pages = paginator.paginate(
            catalog="AWSMarketplace",
            filters=[
                {"name": "PartyType", "values": ["Acceptor"]},
                {"name": "AgreementType", "values": ["PurchaseAgreement"]},
                {"name": "ResourceType", "values": ["AmiProduct"]},
            ],
        )
        product_ids = {}
        for page in pages:
            for agreement in page.get("agreementViewSummaries", []):
                if agreement.get("status") != "ACTIVE":
                    continue
                for resource in agreement.get("proposalSummary", {}).get("resources", []):
                    if resource.get("type") == "AmiProduct":
                        product_ids[resource.get("id")] = None
        return list(product_ids)

    @staticmethod
    def __describe_image(clients: dict[str, Any], product_id: str) -> marketplace_image.MarketplaceImage | None:
        """Resolves a product through its AMI alias, or returns None when it cannot be used as a base image here."""
        try:
            ami_id = clients["ssm"].get_parameter(Name=AMI_ALIAS_PARAMETER_NAME.format(product_id=product_id))[
                "Parameter"
            ]["Value"]
            amis = clients["ec2"].describe_images(ImageIds=[ami_id]).get("Images", [])
        except ClientError:
            return None
        if not amis or amis[0].get("Architecture") not in ARCHITECTURES:
            return None
        if amis[0].get("RootDeviceName") != ROOT_DEVICE_NAME:
            return None

        return marketplace_image.MarketplaceImage(
            productId=product_id,
            name=AWSMarketplaceImageService.__get_product_name(clients, product_id),
            amiId=ami_id,
            platform="Windows" if amis[0].get("PlatformDetails", "").startswith("Windows") else "Linux",
            architecture=ARCHITECTURES[amis[0]["Architecture"]],
            rootVolumeSize=next(
                mapping["Ebs"]["VolumeSize"]
                for mapping in amis[0].get("BlockDeviceMappings", [])
                if mapping.get("DeviceName") == ROOT_DEVICE_NAME
            ),
        )

    @staticmethod
    def __get_product_name(clients: dict[str, Any], product_id: str) -> str:
        try:
            return clients["marketplace-discovery"].get_product(productId=product_id).get("productName", product_id)
        except ClientError:
            return product_id
