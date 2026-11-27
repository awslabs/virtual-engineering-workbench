import logging
from unittest import mock

import assertpy
import pytest

from app.packaging.domain.exceptions.domain_exception import DomainException
from app.packaging.domain.model.image import image as image_model
from app.packaging.domain.model.image.image_constants import ImageSource
from app.packaging.domain.ports.ami_validation_service import AmiValidationService
from app.packaging.domain.ports.image_query_service import ImageQueryService
from app.packaging.domain.ports.marketplace_agreement_service import MarketplaceAgreementService
from app.packaging.domain.ports.marketplace_ami_service import MarketplaceAmiService
from app.packaging.domain.ports.marketplace_license_service import MarketplaceLicenseService
from app.packaging.domain.ports.marketplace_offer_service import MarketplaceOfferService
from app.packaging.domain.ports.parameter_service import ParameterDefinitionService
from app.packaging.domain.query_services.marketplace_base_image_domain_query_service import (
    MarketplaceBaseImageDomainQueryService,
)
from app.packaging.domain.read_models.ami_description import AmiDescription
from app.packaging.domain.read_models.marketplace_agreement import MarketplaceAgreement
from app.packaging.domain.read_models.marketplace_ami import MarketplaceAmi
from app.packaging.domain.read_models.received_license import ReceivedLicense

PRODUCT_ID = "prod-ib2w5aw4ynhey"
ALIAS_AMI_ID = "ami-0aaaaaaaaaaaaaaa1"
LICENSE_ARN = "arn:aws:license-manager::111111111111:license:l-0123456789abcdef0123456789abcdef"
PRODUCT_CODE = "abc123def456ghi789jkl0mno"


def _license(**overrides) -> ReceivedLicense:
    values = dict(
        licenseArn=LICENSE_ARN,
        licenseName="Ubuntu",
        productName="Ubuntu 24.04 LTS",
        productSku=PRODUCT_ID,
        issuer="AWS/Marketplace",
        status="AVAILABLE",
        allowedOperations=["CreateGrant", "CheckoutLicense"],
        homeRegion="us-east-1",
    )
    values.update(overrides)
    return ReceivedLicense(**values)


def _ami(ami_id: str = ALIAS_AMI_ID, architecture: str = "x86_64", root_device: str = "/dev/sda1", size=8):
    return AmiDescription(
        amiId=ami_id,
        state="available",
        platform="Linux/UNIX",
        architecture=architecture,
        name="ubuntu-noble-24.04",
        ownerId="679593333241",
        region="us-east-1",
        blockDeviceMappings=[{"DeviceName": root_device, "Ebs": {"VolumeSize": size}}],
        productCodes=[{"ProductCodeId": PRODUCT_CODE, "ProductCodeType": "marketplace"}],
    )


@pytest.fixture
def services():
    s = dict(
        license_service=mock.create_autospec(spec=MarketplaceLicenseService, instance=True),
        agreement_service=mock.create_autospec(spec=MarketplaceAgreementService, instance=True),
        ami_service=mock.create_autospec(spec=MarketplaceAmiService, instance=True),
        parameter_service=mock.create_autospec(spec=ParameterDefinitionService, instance=True),
        ami_validation_service=mock.create_autospec(spec=AmiValidationService, instance=True),
        offer_service=mock.create_autospec(spec=MarketplaceOfferService, instance=True),
    )
    s["license_service"].list_received_licenses.return_value = [_license()]
    s["agreement_service"].list_active_agreements.return_value = [
        MarketplaceAgreement(agreementId="agmt-1", productId=PRODUCT_ID, offerId="offer-1", status="ACTIVE")
    ]
    s["parameter_service"].get_parameter_value.return_value = ALIAS_AMI_ID
    s["ami_validation_service"].describe_image.return_value = _ami()
    s["offer_service"].list_supported_instance_types.return_value = ["m7i.2xlarge", "t3.medium"]
    return s


@pytest.fixture
def query_service(services):
    return MarketplaceBaseImageDomainQueryService(**services, region="us-east-1", logger=logging.getLogger("test"))


def test_should_resolve_the_product_through_its_ami_alias(query_service, services):
    image = query_service.get_base_image(PRODUCT_ID)

    services["parameter_service"].get_parameter_value.assert_called_once_with(
        f"/aws/service/marketplace/{PRODUCT_ID}/latest"
    )
    services["ami_validation_service"].describe_image.assert_called_once_with(ALIAS_AMI_ID)
    services["ami_service"].list_marketplace_amis_by_product_id.assert_not_called()
    assertpy.assert_that(image.model_dump()).is_equal_to(
        {
            "productId": PRODUCT_ID,
            "imageId": None,
            "productName": "Ubuntu 24.04 LTS",
            "productCode": PRODUCT_CODE,
            "amiId": ALIAS_AMI_ID,
            "platform": "Linux",
            "architecture": "amd64",
            "rootVolumeSize": 8,
            "licenseConfigurationArn": LICENSE_ARN,
            "homeRegion": "us-east-1",
            "subscriptionOwnership": "VEW_MANAGED",
            "licenseGrantAllowed": True,
            "supportedInstanceTypes": ["m7i.2xlarge", "t3.medium"],
        }
    )
    services["offer_service"].list_supported_instance_types.assert_called_once_with(PRODUCT_ID)


def test_should_fall_back_to_the_newest_ami_by_name_when_there_is_no_alias(query_service, services):
    services["parameter_service"].get_parameter_value.side_effect = Exception("ParameterNotFound")
    services["ami_service"].list_marketplace_amis_by_product_id.return_value = [
        MarketplaceAmi(
            amiId="ami-0old",
            productCode=PRODUCT_CODE,
            state="available",
            region="us-east-1",
            creationDate="2026-01-01T00:00:00.000Z",
        ),
        MarketplaceAmi(
            amiId="ami-0new",
            productCode=PRODUCT_CODE,
            state="available",
            region="us-east-1",
            creationDate="2026-10-01T00:00:00.000Z",
        ),
    ]
    services["ami_validation_service"].describe_image.return_value = _ami("ami-0new")

    image = query_service.get_base_image(PRODUCT_ID)

    services["ami_service"].list_marketplace_amis_by_product_id.assert_called_once_with(PRODUCT_ID, "us-east-1")
    services["ami_validation_service"].describe_image.assert_called_once_with("ami-0new")
    assertpy.assert_that(image.amiId).is_equal_to("ami-0new")


def test_should_classify_as_externally_managed_without_an_agreement(query_service, services):
    services["agreement_service"].list_active_agreements.return_value = []

    image = query_service.get_base_image(PRODUCT_ID)

    assertpy.assert_that(image.subscriptionOwnership).is_equal_to("EXTERNALLY_MANAGED")


@pytest.mark.parametrize(
    "licenses",
    (
        [],
        [_license(productSku="prod-someotherproduct")],
        [_license(status="EXPIRED")],
    ),
)
def test_should_reject_a_product_without_an_active_subscription(query_service, services, licenses):
    services["license_service"].list_received_licenses.return_value = licenses

    with pytest.raises(DomainException, match="not an AWS Marketplace product with an active subscription"):
        query_service.get_base_image(PRODUCT_ID)
    services["parameter_service"].get_parameter_value.assert_not_called()


def test_should_reject_a_product_without_any_ami_in_the_region(query_service, services):
    services["parameter_service"].get_parameter_value.side_effect = Exception("ParameterNotFound")
    services["ami_service"].list_marketplace_amis_by_product_id.return_value = []

    with pytest.raises(DomainException, match="has no AMI available in us-east-1"):
        query_service.get_base_image(PRODUCT_ID)


def test_should_reject_an_ami_the_factory_cannot_describe(query_service, services):
    services["ami_validation_service"].describe_image.side_effect = Exception("InvalidAMIID.NotFound")

    with pytest.raises(DomainException, match="is not available to the image factory"):
        query_service.get_base_image(PRODUCT_ID)


@pytest.mark.parametrize(
    "ami,expected_message",
    (
        (_ami(architecture="i386"), "unsupported architecture i386"),
        (_ami(root_device="/dev/xvda"), "does not use /dev/sda1 as its root volume"),
        (_ami(size=None), "does not use /dev/sda1 as its root volume"),
    ),
)
def test_should_reject_an_ami_recipes_cannot_build_on(query_service, services, ami, expected_message):
    services["ami_validation_service"].describe_image.return_value = ami

    with pytest.raises(DomainException, match=expected_message):
        query_service.get_base_image(PRODUCT_ID)


def test_metadata_for_built_images_has_no_regional_ami_ids(query_service):
    metadata = query_service.get_base_image(PRODUCT_ID).to_parent_image_marketplace_metadata()

    assertpy.assert_that(metadata).does_not_contain_key("regionalAmiIds")
    assertpy.assert_that(metadata).is_equal_to(
        {
            "marketplaceProductId": PRODUCT_ID,
            "productCode": PRODUCT_CODE,
            "licenseConfigurationArn": LICENSE_ARN,
            "homeRegion": "us-east-1",
            "subscriptionOwnership": "VEW_MANAGED",
            "licenseGrantAllowed": True,
            "rootVolumeSize": 8,
        }
    )


def test_metadata_records_whether_the_hub_licence_allows_create_grant(query_service, services):
    """Publishing upgrades an Externally Managed parent to a hub grant only when this is set."""
    services["license_service"].list_received_licenses.return_value = [_license(allowedOperations=["CheckoutLicense"])]

    metadata = query_service.get_base_image(PRODUCT_ID).to_parent_image_marketplace_metadata()

    assertpy.assert_that(metadata["licenseGrantAllowed"]).is_false()


def test_without_offer_access_instance_types_are_not_restricted(services):
    services.pop("offer_service")
    query_service = MarketplaceBaseImageDomainQueryService(
        **services, region="us-east-1", logger=logging.getLogger("test")
    )

    assertpy.assert_that(query_service.get_base_image(PRODUCT_ID).supportedInstanceTypes).is_empty()


# ---- imported AWS-published images (AWS_PUBLISHED_AMI) as base image ----

RHEL_AMI_ID = "ami-0b07d2bc8152a1d84"


def _imported(source=ImageSource.AWS_PUBLISHED_AMI, status=image_model.ImageStatus.Created):
    return image_model.Image(
        projectId="proj-1",
        imageId="image-rhel9abc",
        imageUpstreamId=RHEL_AMI_ID,
        imageName="RHEL 9",
        imageSource=source,
        status=status,
        createDate="2026-11-12T00:00:00+00:00",
        lastUpdateDate="2026-11-12T00:00:00+00:00",
    )


@pytest.fixture
def imported_query_service(services):
    image_qry = mock.create_autospec(spec=ImageQueryService, instance=True)
    image_qry.get_image.return_value = _imported()
    services["ami_validation_service"].describe_image.return_value = _ami(RHEL_AMI_ID, size=10)
    return (
        MarketplaceBaseImageDomainQueryService(
            **services, region="us-east-1", logger=logging.getLogger("test"), image_query_service=image_qry
        ),
        image_qry,
    )


def test_should_resolve_an_imported_aws_published_image(imported_query_service, services):
    query_service, image_qry = imported_query_service

    image = query_service.get_imported_base_image("proj-1", "image-rhel9abc")

    image_qry.get_image.assert_called_once_with("proj-1", "image-rhel9abc")
    services["ami_validation_service"].describe_image.assert_called_once_with(RHEL_AMI_ID)
    # No subscription, license or grant: AWS is the seller of record.
    services["license_service"].list_received_licenses.assert_not_called()
    services["offer_service"].list_supported_instance_types.assert_not_called()
    assertpy.assert_that(image.imageId).is_equal_to("image-rhel9abc")
    assertpy.assert_that(image.productId).is_none()
    assertpy.assert_that(image.amiId).is_equal_to(RHEL_AMI_ID)
    assertpy.assert_that(image.rootVolumeSize).is_equal_to(10)
    assertpy.assert_that(image.licenseConfigurationArn).is_none()
    assertpy.assert_that(image.subscriptionOwnership).is_equal_to("AWS_MANAGED")
    assertpy.assert_that(image.supportedInstanceTypes).is_empty()


@pytest.mark.parametrize(
    "found",
    (
        None,
        _imported(source=ImageSource.MARKETPLACE_PRODUCT),
        _imported(source=ImageSource.PIPELINE),
        _imported(status=image_model.ImageStatus.Retired),
    ),
)
def test_should_reject_anything_but_a_created_aws_published_import(imported_query_service, found):
    query_service, image_qry = imported_query_service
    image_qry.get_image.return_value = found

    with pytest.raises(DomainException, match="not an imported AWS-published image"):
        query_service.get_imported_base_image("proj-1", "image-rhel9abc")
