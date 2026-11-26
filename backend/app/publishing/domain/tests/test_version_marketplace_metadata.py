"""Product versions keep the Marketplace license of their AMI, for imported AMIs and for pipeline images
built on a Marketplace AMI (imageSource unset), so publishing can grant it to spoke accounts."""

from unittest import mock

import assertpy
import pytest

from app.publishing.domain.command_handlers import create_version_command_handler, update_version_command_handler
from app.publishing.domain.event_handlers import create_automated_version_event_handler
from app.publishing.domain.model import product
from app.publishing.domain.ports import amis_query_service
from app.publishing.domain.read_models import ami

METADATA = {
    "marketplaceProductId": "prod-ib2w5aw4ynhey",
    "productCode": "abc123def456ghi789jkl0mno",
    "licenseConfigurationArn": "arn:aws:license-manager::111111111111:license:l-0123456789abcdef0123456789abcdef",
    "homeRegion": "us-east-1",
    "subscriptionOwnership": "VEW_MANAGED",
}
# The publishing model records licenseGrantAllowed, which a recipe's parent licence does not carry.
STORED_METADATA = {**METADATA, "licenseGrantAllowed": False}


def _ami(image_source, metadata):
    return ami.Ami(
        projectId="proj-12345",
        amiId="ami-023c04780e65e723c",
        amiName="Version 1.0.0 of recipe",
        createDate="2026-11-09T00:00:00+00:00",
        lastUpdateDate="2026-11-09T00:00:00+00:00",
        imageSource=image_source,
        marketplaceMetadata=metadata,
    )


def _workbench_product():
    entity = mock.Mock()
    entity.productType = product.ProductType.Workbench
    return entity


def _command():
    command = mock.Mock()
    command.amiId.value = "ami-023c04780e65e723c"
    return command


@pytest.mark.parametrize(
    "image_source,metadata,expected_source,expected_metadata",
    (
        (None, METADATA, None, STORED_METADATA),  # pipeline image built on a Marketplace AMI
        ("MARKETPLACE_PRODUCT", METADATA, "MARKETPLACE_PRODUCT", STORED_METADATA),  # imported Marketplace AMI
        (None, None, None, None),  # ordinary pipeline image
    ),
)
def test_create_and_update_version_copy_the_marketplace_license(
    image_source, metadata, expected_source, expected_metadata
):
    amis_qry_srv = mock.create_autospec(spec=amis_query_service.AMIsQueryService, instance=True)
    amis_qry_srv.get_ami.return_value = _ami(image_source, metadata)

    created = create_version_command_handler._build_additional_attributes(
        _command(), _workbench_product(), amis_qry_srv
    )
    updated = getattr(update_version_command_handler, "__prepare_additional_attributes")(
        _command(), _workbench_product(), amis_qry_srv
    )

    for attrs in (created, updated):
        assertpy.assert_that(attrs.get("imageSource")).is_equal_to(expected_source)
        stored = attrs.get("marketplaceMetadata")
        stored = stored.model_dump(exclude_none=True) if hasattr(stored, "model_dump") else stored
        if isinstance(stored, dict):
            stored = {k: v for k, v in stored.items() if v is not None}
        assertpy.assert_that(stored).is_equal_to(expected_metadata)


@pytest.mark.parametrize("metadata", (METADATA, None))
def test_automated_version_keeps_the_marketplace_license(metadata):
    attrs = create_automated_version_event_handler._get_additional_attributes(
        _workbench_product(), "ami-023c04780e65e723c", [], "Ubuntu 24", "Linux", "amd64", [], metadata
    )

    if metadata:
        assertpy.assert_that(attrs["marketplaceMetadata"]).is_equal_to(metadata)
    else:
        assertpy.assert_that(attrs).does_not_contain_key("marketplaceMetadata")
    assertpy.assert_that(attrs).does_not_contain_key("imageSource")


def test_update_version_to_a_plain_ami_clears_the_old_marketplace_license():
    # update_attributes only sets the keys it gets: both keys must be there, as None, so a version that
    # moves from a Marketplace-based AMI to a plain one does not keep the old license (and get a grant).
    amis_qry_srv = mock.create_autospec(spec=amis_query_service.AMIsQueryService, instance=True)
    amis_qry_srv.get_ami.return_value = _ami(None, None)

    updated = getattr(update_version_command_handler, "__prepare_additional_attributes")(
        _command(), _workbench_product(), amis_qry_srv
    )

    assertpy.assert_that(updated).contains_entry({"imageSource": None}, {"marketplaceMetadata": None})
