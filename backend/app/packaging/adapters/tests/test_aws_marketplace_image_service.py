from unittest import mock

import boto3
import pytest
from botocore.exceptions import ClientError

from app.packaging.adapters.services import aws_marketplace_image_service
from app.packaging.adapters.tests.conftest import GlobalVariables, orig
from app.packaging.domain.read_models import marketplace_image

LINUX_PRODUCT_ID = "prod-linuxproduct1"
WINDOWS_PRODUCT_ID = "prod-windowsproduct1"
PRODUCT_WITHOUT_ALIAS_ID = "prod-noaliasproduct1"
UNSUPPORTED_ARCHITECTURE_PRODUCT_ID = "prod-macproduct1"
UNDESCRIBED_PRODUCT_ID = "prod-undescribedproduct1"
LEGACY_PRODUCT_ID = "804fcc46-63fc-4eb6-85a1-50e66d6c7215"
LINUX_AMI_ID = "ami-0aaaaaaaaaaaaaaaa"
WINDOWS_AMI_ID = "ami-0bbbbbbbbbbbbbbbb"
MAC_AMI_ID = "ami-0cccccccccccccccc"
UNDESCRIBED_AMI_ID = "ami-0dddddddddddddddd"
XVDA_PRODUCT_ID = "prod-xvdaproduct1"
XVDA_AMI_ID = "ami-0eeeeeeeeeeeeeeee"
NO_ROOT_VOLUME_PRODUCT_ID = "prod-norootvolume1"
NO_ROOT_VOLUME_AMI_ID = "ami-0ffffffffffffffff"

LINUX_IMAGE = marketplace_image.MarketplaceImage(
    productId=LINUX_PRODUCT_ID,
    name=f"Name of {LINUX_PRODUCT_ID}",
    amiId=LINUX_AMI_ID,
    platform="Linux",
    architecture="amd64",
    rootVolumeSize=8,
)
WINDOWS_IMAGE = marketplace_image.MarketplaceImage(
    productId=WINDOWS_PRODUCT_ID,
    name=f"Name of {WINDOWS_PRODUCT_ID}",
    amiId=WINDOWS_AMI_ID,
    platform="Windows",
    architecture="arm64",
    rootVolumeSize=30,
)

UNDESCRIBED_IMAGE = marketplace_image.MarketplaceImage(
    productId=UNDESCRIBED_PRODUCT_ID,
    name=UNDESCRIBED_PRODUCT_ID,
    amiId=UNDESCRIBED_AMI_ID,
    platform="Linux",
    architecture="amd64",
    rootVolumeSize=8,
)


def _agreement(product_id, status="ACTIVE", resource_type="AmiProduct"):
    return {"status": status, "proposalSummary": {"resources": [{"id": product_id, "type": resource_type}]}}


@pytest.fixture()
def marketplace_image_srv():
    return aws_marketplace_image_service.AWSMarketplaceImageService(
        admin_role=GlobalVariables.TEST_ADMIN_ROLE.value,
        ami_factory_aws_account_id=GlobalVariables.AWS_ACCOUNT_ID.value,
        region=GlobalVariables.TEST_REGION.value,
    )


@pytest.fixture()
def mock_marketplace_calls():
    parameter_not_found = boto3.client(
        "ssm", region_name=GlobalVariables.TEST_REGION.value
    ).exceptions.ParameterNotFound
    aliases = {
        f"/aws/service/marketplace/{product_id}/latest": ami_id
        for product_id, ami_id in [
            (LINUX_PRODUCT_ID, LINUX_AMI_ID),
            (WINDOWS_PRODUCT_ID, WINDOWS_AMI_ID),
            (UNSUPPORTED_ARCHITECTURE_PRODUCT_ID, MAC_AMI_ID),
            (UNDESCRIBED_PRODUCT_ID, UNDESCRIBED_AMI_ID),
            (XVDA_PRODUCT_ID, XVDA_AMI_ID),
            (NO_ROOT_VOLUME_PRODUCT_ID, NO_ROOT_VOLUME_AMI_ID),
        ]
    }

    def _image(architecture, platform_details, volume_size=8, root_device_name="/dev/sda1"):
        return {
            "Architecture": architecture,
            "PlatformDetails": platform_details,
            "RootDeviceName": root_device_name,
            "BlockDeviceMappings": [{"DeviceName": root_device_name, "Ebs": {"VolumeSize": volume_size}}],
        }

    images = {
        LINUX_AMI_ID: _image("x86_64", "Linux/UNIX"),
        WINDOWS_AMI_ID: _image("arm64", "Windows", volume_size=30),
        MAC_AMI_ID: _image("x86_64_mac", "Linux/UNIX"),
        UNDESCRIBED_AMI_ID: _image("x86_64", "Linux/UNIX"),
        XVDA_AMI_ID: _image("x86_64", "Linux/UNIX", root_device_name="/dev/xvda"),
        NO_ROOT_VOLUME_AMI_ID: {**_image("x86_64", "Linux/UNIX"), "BlockDeviceMappings": []},
    }

    def _get_parameter(Name):
        if Name not in aliases:
            raise parameter_not_found({"Error": {"Code": "ParameterNotFound", "Message": ""}}, "GetParameter")
        return {"Parameter": {"Name": Name, "Value": aliases[Name]}}

    def _get_product(productId):
        if productId == UNDESCRIBED_PRODUCT_ID:
            raise ClientError({"Error": {"Code": "ResourceNotFoundException", "Message": ""}}, "GetProduct")
        return {"productName": f"Name of {productId}"}

    invocations = {
        "SearchAgreements": mock.MagicMock(
            side_effect=lambda **kwargs: (
                {
                    "agreementViewSummaries": [
                        _agreement(WINDOWS_PRODUCT_ID),
                        _agreement(LEGACY_PRODUCT_ID),
                        _agreement(UNSUPPORTED_ARCHITECTURE_PRODUCT_ID),
                        _agreement(UNDESCRIBED_PRODUCT_ID),
                        _agreement(XVDA_PRODUCT_ID),
                        _agreement(NO_ROOT_VOLUME_PRODUCT_ID),
                        _agreement(LINUX_PRODUCT_ID),
                    ]
                }
                if kwargs.get("nextToken")
                else {
                    "agreementViewSummaries": [
                        _agreement(LINUX_PRODUCT_ID),
                        _agreement(PRODUCT_WITHOUT_ALIAS_ID),
                        _agreement("prod-expiredproduct1", status="EXPIRED"),
                        _agreement("prod-saasproduct1", resource_type="SaaSProduct"),
                    ],
                    "nextToken": "next",
                }
            )
        ),
        "GetProduct": mock.MagicMock(side_effect=_get_product),
        "GetParameter": mock.MagicMock(side_effect=_get_parameter),
        "DescribeImages": mock.MagicMock(side_effect=lambda ImageIds: {"Images": [images[ImageIds[0]]]}),
    }

    def _interceptor(self, operation_name, kwarg):
        if operation_name in invocations:
            return invocations[operation_name](**kwarg)

        return orig(self, operation_name, kwarg)

    with mock.patch("botocore.client.BaseClient._make_api_call", new=_interceptor):
        yield invocations


def test_list_images_should_return_subscribed_ami_products_usable_as_base_images(
    mock_marketplace_calls, marketplace_image_srv
):
    # ACT
    response = marketplace_image_srv.list_images()

    # ASSERT
    assert response == [LINUX_IMAGE, WINDOWS_IMAGE, UNDESCRIBED_IMAGE]


def test_list_images_should_search_purchase_agreements_across_pages(mock_marketplace_calls, marketplace_image_srv):
    # ACT
    marketplace_image_srv.list_images()

    # ASSERT
    filters = [
        {"name": "PartyType", "values": ["Acceptor"]},
        {"name": "AgreementType", "values": ["PurchaseAgreement"]},
        {"name": "ResourceType", "values": ["AmiProduct"]},
    ]
    assert mock_marketplace_calls["SearchAgreements"].call_args_list == [
        mock.call(catalog="AWSMarketplace", filters=filters),
        mock.call(catalog="AWSMarketplace", filters=filters, nextToken="next"),
    ]


def test_get_image_should_return_the_subscribed_product(mock_marketplace_calls, marketplace_image_srv):
    # ACT
    response = marketplace_image_srv.get_image(LINUX_PRODUCT_ID)

    # ASSERT
    assert response == LINUX_IMAGE
    mock_marketplace_calls["GetParameter"].assert_called_once_with(
        Name=f"/aws/service/marketplace/{LINUX_PRODUCT_ID}/latest"
    )


@pytest.mark.parametrize(
    "product_id",
    [
        "prod-notsubscribed1",
        "prod-expiredproduct1",
        PRODUCT_WITHOUT_ALIAS_ID,
        LEGACY_PRODUCT_ID,
        UNSUPPORTED_ARCHITECTURE_PRODUCT_ID,
        XVDA_PRODUCT_ID,
        NO_ROOT_VOLUME_PRODUCT_ID,
    ],
)
def test_get_image_should_return_none_for_products_that_cannot_be_used_as_base_images(
    mock_marketplace_calls, marketplace_image_srv, product_id
):
    # ACT
    response = marketplace_image_srv.get_image(product_id)

    # ASSERT
    assert response is None
