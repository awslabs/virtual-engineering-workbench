"""Tests for AwsPublishedAmiResolver (product-code based, with narrow
no-product-code fallback).

Each test is a self-contained scenario that mocks the two external calls
the resolver depends on:
- ``marketplace-discovery.list_purchase_options``
- ``ec2.describe_images``

The resolver's contract is deliberately narrow, "given a product id, return
the newest AMI id or ids", so the test suite is similarly narrow. Upstream
behaviour such as subscription state and pricing model is not this resolver's
concern and is not tested here.
"""

from unittest.mock import MagicMock

import assertpy
import pytest

from app.packaging.adapters.exceptions import adapter_exception
from app.packaging.adapters.services.aws_published_ami_resolver import (
    MARKETPLACE_OWNER_ALIAS,
    NO_PRODUCT_CODE_FALLBACKS,
    PRODUCT_ID_FILTER,
    AwsPublishedAmiResolver,
)

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

RHEL_SAP_PRODUCT = "11111111-1111-1111-1111-111111111111"  # synthetic
RHEL_SAP_CODE = "t0bib47g3tzy3d4o6swrhapg"

PLAIN_RHEL9_PRODUCT = "02bec9ca-1c81-40ac-83a2-aa021e2a0b39"
PLAIN_RHEL9_CODE = "5umtzeg7wt8j6cmc266tbcxl"  # offer exists, image has none

PLAIN_RHEL8_PRODUCT = "cbee603d-70d3-47bf-81f6-6215e6e26c7b"
PLAIN_RHEL8_CODE = "c2mw245pkdbc272mo0z2yvpff"  # offer exists, image has none
PLAIN_RHEL8_ARM_PRODUCT = "6d7a0d79-ee54-43e2-a382-ed10e65a19da"

ROCKY9_PRODUCT = "3f230a17-9877-4b16-aa5e-b1ff34ab206b"
ROCKY9_CODE = "3qk9e6x2ni81uiqnorll45r3f"


def _image(
    ami_id,
    name,
    owner="aws-marketplace",
    arch="x86_64",
    usage_op="RunInstances:0010",
    creation="2026-10-01T00:00:00.000Z",
):
    return {
        "ImageId": ami_id,
        "Name": name,
        "OwnerId": owner,
        "Architecture": arch,
        "PlatformDetails": "Red Hat Enterprise Linux",
        "UsageOperation": usage_op,
        "CreationDate": creation,
        "State": "available",
    }


def _purchase_options(product_code):
    return {"purchaseOptions": [{"purchaseOptionId": product_code}]}


def _session_with(discovery_response, describe_responses):
    """Build a boto3.Session mock whose ``.client`` returns the right stub.

    ``describe_responses`` is a list consumed in order so a test can set up
    the product-code call AND the fallback call to return different images.
    """
    discovery = MagicMock()
    discovery.list_purchase_options.return_value = discovery_response

    ec2 = MagicMock()
    responses = list(describe_responses)
    ec2.describe_images.side_effect = responses

    session = MagicMock()

    def _client(name, region_name=None):
        if name == "marketplace-discovery":
            return discovery
        if name == "ec2":
            return ec2
        raise AssertionError(f"unexpected client {name!r}")

    session.client.side_effect = _client
    return session, discovery, ec2


# ---------------------------------------------------------------------------
# product-coded AMIs (the common path)
# ---------------------------------------------------------------------------


class TestProductCodeResolution:
    def test_rhel_sap_resolves_via_product_code(self):
        """AWS-sold RHEL-SAP: discovery returns the product code, EC2 returns
        the AMI, the resolver reports unambiguous."""
        session, discovery, ec2 = _session_with(
            _purchase_options(RHEL_SAP_CODE),
            [
                {
                    "Images": [
                        _image(
                            "ami-rhelsap1",
                            "RHEL-SAP-9.2.0_HVM-20250917-x86_64-0-Hourly2-GP3",
                            usage_op="RunInstances:0010",
                        )
                    ]
                }
            ],
        )
        r = AwsPublishedAmiResolver(boto_session=session).resolve(RHEL_SAP_PRODUCT, "us-east-1")

        assert r.unambiguous is True
        assert r.candidates[0].amiId == "ami-rhelsap1"
        discovery.list_purchase_options.assert_called_once_with(
            filters=[{"filterType": PRODUCT_ID_FILTER, "filterValues": [RHEL_SAP_PRODUCT]}]
        )

    def test_product_code_lookup_uses_marketplace_owner_alias(self):
        """The EC2 describe is scoped to ``aws-marketplace``, which matches
        every Marketplace AMI regardless of which vendor account holds it.
        Asserting on vendor-account ids would be wrong, because vendors
        rotate them."""
        session, _, ec2 = _session_with(
            _purchase_options(ROCKY9_CODE),
            [{"Images": [_image("ami-r1", "Rocky-9-EC2-Base-9.8", usage_op="RunInstances")]}],
        )
        AwsPublishedAmiResolver(boto_session=session).resolve(ROCKY9_PRODUCT, "us-east-1")

        kwargs = ec2.describe_images.call_args.kwargs
        assert kwargs["Owners"] == [MARKETPLACE_OWNER_ALIAS]
        assert {"Name": "product-code", "Values": [ROCKY9_CODE]} in kwargs["Filters"]

    def test_newest_build_wins_for_an_unambiguous_product(self):
        """Multiple AMIs under the same product code are build variants of
        the same image. The resolver sorts by CreationDate descending."""
        images = [
            _image("ami-old", "RHEL-SAP-9.2-old", creation="2025-01-01T00:00:00.000Z"),
            _image("ami-new", "RHEL-SAP-9.2-new", creation="2026-10-15T00:00:00.000Z"),
            _image("ami-mid", "RHEL-SAP-9.2-mid", creation="2026-05-01T00:00:00.000Z"),
        ]
        session, _, _ = _session_with(_purchase_options(RHEL_SAP_CODE), [{"Images": images}])
        r = AwsPublishedAmiResolver(boto_session=session).resolve(RHEL_SAP_PRODUCT, "us-east-1")

        assert r.candidates[0].amiId == "ami-new"
        assert r.resolved.amiId == "ami-new"

    def test_architecture_signal_is_the_amis_own_architecture(self):
        """The caller takes architecture off the candidate; the resolver
        does not filter by arch at the discovery level because a single
        product id can map to both x86 and arm variants."""
        session, _, _ = _session_with(
            _purchase_options(RHEL_SAP_CODE),
            [
                {
                    "Images": [
                        _image("ami-arm", "RHEL-SAP-9.2-arm64", arch="arm64"),
                        _image("ami-x86", "RHEL-SAP-9.2-x86_64", arch="x86_64"),
                    ]
                }
            ],
        )
        r = AwsPublishedAmiResolver(boto_session=session).resolve(RHEL_SAP_PRODUCT, "us-east-1")
        archs = {c.architecture for c in r.candidates}
        assert archs == {"x86_64", "arm64"}


# ---------------------------------------------------------------------------
# no-product-code fallback (the plain-OS products)
# ---------------------------------------------------------------------------


class TestNoProductCodeFallback:
    def test_plain_rhel9_resolves_via_fallback_when_product_code_has_no_ami(self):
        """Plain RHEL 9 publishes an offer with a product code, but the
        AMI itself has none. The resolver's second step uses the hand-
        verified fallback and matches by owner, name and billing code."""
        session, _, ec2 = _session_with(
            _purchase_options(PLAIN_RHEL9_CODE),
            [
                {"Images": []},  # product-code describe finds nothing
                {
                    "Images": [
                        _image(
                            "ami-rhel9",
                            "RHEL-9.6.0_HVM-20260922-x86_64-0-Hourly2-GP3",
                            owner="309956199498",
                            usage_op="RunInstances:0010",
                        ),
                    ]
                },
            ],
        )
        r = AwsPublishedAmiResolver(boto_session=session).resolve(PLAIN_RHEL9_PRODUCT, "us-east-1")

        assert r.unambiguous is True
        assert r.candidates[0].amiId == "ami-rhel9"
        # Two describe_images calls: product-code first, then fallback owner.
        assert ec2.describe_images.call_count == 2
        second_owners = ec2.describe_images.call_args_list[1].kwargs["Owners"]
        assert second_owners == ["309956199498"]

    def test_fallback_rejects_near_miss_names(self):
        """Owner 309956199498 publishes RHEL_HA-9.* and the BYOL
        RHEL-9.*-Access2 under the same account, and both are different
        licensed products. A prefix match would admit them; the full-name
        regex rejects both."""
        session, _, _ = _session_with(
            _purchase_options(PLAIN_RHEL9_CODE),
            [
                {"Images": []},  # product-code describe
                {
                    "Images": [
                        _image(
                            "ami-ha",
                            "RHEL_HA-9.6.0_HVM-20260922-x86_64-0-Hourly2-GP3",
                            owner="309956199498",
                            usage_op="RunInstances:0010",
                        ),
                        _image(
                            "ami-byol",
                            "RHEL-9.6.0_HVM-20260922-x86_64-0-Access2-GP3",
                            owner="309956199498",
                            usage_op="RunInstances:0010",
                        ),
                    ]
                },
            ],
        )
        r = AwsPublishedAmiResolver(boto_session=session).resolve(PLAIN_RHEL9_PRODUCT, "us-east-1")
        assert r.unambiguous is False, "near-miss names must not resolve"

    def test_fallback_rejects_wrong_billing_code(self):
        """A matching name under the same owner but with the wrong
        UsageOperation is a different licensed product. Some RHEL and
        RHEL-for-SAP builds share the same name shape, and only the billing
        code distinguishes them."""
        session, _, _ = _session_with(
            _purchase_options(PLAIN_RHEL9_CODE),
            [
                {"Images": []},
                {
                    "Images": [
                        _image(
                            "ami-plain",
                            "RHEL-9.6.0_HVM-20260922-x86_64-0-Hourly2-GP3",
                            owner="309956199498",
                            usage_op="RunInstances",
                        ),  # wrong billing code
                    ]
                },
            ],
        )
        r = AwsPublishedAmiResolver(boto_session=session).resolve(PLAIN_RHEL9_PRODUCT, "us-east-1")
        assert r.unambiguous is False

    def test_plain_rhel8_resolves_via_fallback(self):
        """Plain RHEL 8 has the same shape as plain RHEL 9: Red Hat publishes
        the current 8.x AMIs under 309956199498 with UsageOperation
        RunInstances:0010 and no product code on the image, so the listing
        only resolves through the fallback table. The regex anchors on
        ``RHEL-8.`` with a hyphen so the RHEL_HA-8.* family is excluded."""
        session, _, _ = _session_with(
            _purchase_options(PLAIN_RHEL8_CODE),
            [
                {"Images": []},
                {
                    "Images": [
                        _image(
                            "ami-rhel8",
                            "RHEL-8.10.0_HVM-20261013-x86_64-2315-Hourly2-GP3",
                            owner="309956199498",
                            usage_op="RunInstances:0010",
                        ),
                    ]
                },
            ],
        )
        r = AwsPublishedAmiResolver(boto_session=session).resolve(PLAIN_RHEL8_PRODUCT, "us-east-1")
        assert r.unambiguous is True
        assert r.candidates[0].amiId == "ami-rhel8"

    def test_plain_rhel8_rejects_rhel_ha_8_near_miss(self):
        """RHEL_HA-8.10.* is a DIFFERENT product with its own HA licence
        (UsageOperation ``RunInstances:1010``). The anchored name regex
        (``RHEL-`` with a hyphen) and the UsageOperation guard each reject
        it on their own."""
        session, _, _ = _session_with(
            _purchase_options(PLAIN_RHEL8_CODE),
            [
                {"Images": []},
                {
                    "Images": [
                        _image(
                            "ami-ha8",
                            "RHEL_HA-8.10.0_HVM-20261013-x86_64-2302-Hourly2-GP3",
                            owner="309956199498",
                            usage_op="RunInstances:1010",
                        ),
                    ]
                },
            ],
        )
        r = AwsPublishedAmiResolver(boto_session=session).resolve(PLAIN_RHEL8_PRODUCT, "us-east-1")
        assert r.unambiguous is False, "RHEL_HA must not resolve plain RHEL 8"

    def test_plain_rhel8_arm_resolves_separately(self):
        """ARM is a distinct productId with its own name-pattern entry in
        the table, so this pins that the ARM entry is wired independently of
        the x86_64 one."""
        session, _, _ = _session_with(
            _purchase_options(PLAIN_RHEL8_CODE),
            [
                {"Images": []},
                {
                    "Images": [
                        _image(
                            "ami-rhel8-arm",
                            "RHEL-8.10.0_HVM-20261013-arm64-2311-Hourly2-GP3",
                            owner="309956199498",
                            arch="arm64",
                            usage_op="RunInstances:0010",
                        ),
                    ]
                },
            ],
        )
        r = AwsPublishedAmiResolver(boto_session=session).resolve(PLAIN_RHEL8_ARM_PRODUCT, "us-east-1")
        assert r.unambiguous is True
        assert r.candidates[0].amiId == "ami-rhel8-arm"
        assert r.candidates[0].architecture == "arm64"

    def test_amazon_linux_2_resolves_via_fallback(self):
        """Amazon Linux 2 is published by Amazon under 137112412989 with
        UsageOperation ``RunInstances``, no suffix, because plain Linux/UNIX
        carries no per-licence charge. The regex tolerates both ``-gp2`` and
        ``-ebs`` boot-volume suffixes, which both exist in the wild."""
        AMAZON_LINUX2_PRODUCT = "8b955bdf-2a12-455e-9a23-2f5413d383ae"
        session, _, _ = _session_with(
            _purchase_options("some-opaque-code"),
            [
                {"Images": []},
                {
                    "Images": [
                        _image(
                            "ami-al2",
                            "amzn2-ami-hvm-2.0.20261027.0-x86_64-gp2",
                            owner="137112412989",
                            usage_op="RunInstances",
                        ),
                    ]
                },
            ],
        )
        r = AwsPublishedAmiResolver(boto_session=session).resolve(AMAZON_LINUX2_PRODUCT, "us-east-1")
        assert r.unambiguous is True
        assert r.candidates[0].amiId == "ami-al2"

    def test_amazon_linux_2_rejects_minimal_variant(self):
        """``amzn2-ami-minimal-hvm-*`` is a DIFFERENT product id, not a
        timestamp drift. The ``^amzn2-ami-hvm-`` anchor rejects it."""
        AMAZON_LINUX2_PRODUCT = "8b955bdf-2a12-455e-9a23-2f5413d383ae"
        session, _, _ = _session_with(
            _purchase_options("some-opaque-code"),
            [
                {"Images": []},
                {
                    "Images": [
                        _image(
                            "ami-min",
                            "amzn2-ami-minimal-hvm-2.0.20261027.0-x86_64-gp2",
                            owner="137112412989",
                            usage_op="RunInstances",
                        ),
                    ]
                },
            ],
        )
        r = AwsPublishedAmiResolver(boto_session=session).resolve(AMAZON_LINUX2_PRODUCT, "us-east-1")
        assert r.unambiguous is False

    def test_suse_sles_15_resolves_and_rejects_ecs_variant(self):
        """SUSE SLES 15 lives alongside ``-ecs-`` (container-optimised) and
        ``-sapcal-`` variants under the SAME owner, and those are separate
        products. The regex anchors on
        ``^suse-sles-15-sp\\d+-v\\d{8}-hvm-ssd-x86_64$`` so neither
        contaminates the result."""
        SLES15_PRODUCT = "472fae9d-3a9d-469b-8946-2282d6d4ff36"
        session, _, _ = _session_with(
            _purchase_options("some-opaque-code"),
            [
                {"Images": []},
                {
                    "Images": [
                        _image(
                            "ami-plain",
                            "suse-sles-15-sp5-v20261019-hvm-ssd-x86_64",
                            owner="013907871322",
                            usage_op="RunInstances:000g",
                        ),
                        _image(
                            "ami-ecs",
                            "suse-sles-15-sp5-v20261019-ecs-hvm-ssd-x86_64",
                            owner="013907871322",
                            usage_op="RunInstances:000g",
                        ),
                        _image(
                            "ami-sapcal",
                            "suse-sles-15-sp5-sapcal-v20261019-hvm-ssd-x86_64",
                            owner="013907871322",
                            usage_op="RunInstances:000g",
                        ),
                    ]
                },
            ],
        )
        r = AwsPublishedAmiResolver(boto_session=session).resolve(SLES15_PRODUCT, "us-east-1")
        assert r.unambiguous is True
        assert (
            r.candidates[0].amiId == "ami-plain"
        ), "the ECS and SAPCAL variants are different products; anchored regex must exclude them"

    def test_unknown_product_without_fallback_is_unresolved(self):
        """A product id that has no product-coded AMI AND is not in the
        hand-verified fallback must come back unambiguous=False, never a
        guess."""
        session, _, _ = _session_with(
            _purchase_options(PLAIN_RHEL9_CODE),  # has a code
            [{"Images": []}],  # but no AMI matches it
        )
        # Use a product id that is NOT in NO_PRODUCT_CODE_FALLBACKS.
        unknown = "ffffffff-ffff-ffff-ffff-ffffffffffff"
        assert unknown not in NO_PRODUCT_CODE_FALLBACKS
        session, _, _ = _session_with(
            {"purchaseOptions": []},  # no offer at all
            [],
        )
        r = AwsPublishedAmiResolver(boto_session=session).resolve(unknown, "us-east-1")
        assert r.unambiguous is False
        assert r.candidates == []


# ---------------------------------------------------------------------------
# fail-visibly cases
# ---------------------------------------------------------------------------


class TestFailsVisibly:
    def test_discovery_error_raises(self):
        """A discovery API failure is an adapter exception, not a silent
        empty resolution."""
        from botocore.exceptions import ClientError

        discovery = MagicMock()
        discovery.list_purchase_options.side_effect = ClientError(
            {"Error": {"Code": "InternalFailure", "Message": "boom"}}, "ListPurchaseOptions"
        )
        session = MagicMock()
        session.client.return_value = discovery

        with pytest.raises(adapter_exception.AdapterException):
            AwsPublishedAmiResolver(boto_session=session).resolve("prod-abc", "us-east-1")

    def test_describe_images_error_raises(self):
        """An EC2 describe failure during the product-code step is an
        adapter exception, not silent."""
        from botocore.exceptions import ClientError

        session, _, ec2 = _session_with(_purchase_options(RHEL_SAP_CODE), [])
        ec2.describe_images.side_effect = ClientError(
            {"Error": {"Code": "InternalFailure", "Message": "boom"}}, "DescribeImages"
        )
        with pytest.raises(adapter_exception.AdapterException):
            AwsPublishedAmiResolver(boto_session=session).resolve(RHEL_SAP_PRODUCT, "us-east-1")


# ---------------------------------------------------------------------------
# invariants of the fallback table
# ---------------------------------------------------------------------------


class TestFallbackTable:
    def test_table_covers_only_the_known_no_product_code_products(self):
        """The table is narrow on purpose, and this count is the tripwire.

        Every entry needs its owner, anchored name regex, architecture and
        billing code checked against the vendor's live AMIs before it goes
        in, so a bulk-add during a refactor is a bug rather than a
        convenience. Change this number only together with a test that pins
        the new entry and the neighbouring families it must not match.
        """
        assert len(NO_PRODUCT_CODE_FALLBACKS) == 33

    def test_table_uses_real_billing_codes(self):
        """The billing code is the licence, so a typo here would resolve a
        product to an image licensed differently, or to nothing at all. These
        are the codes the table is allowed to use:

        - ``RunInstances:0010`` for RHEL (plain and SAP non-HA)
        - ``RunInstances:1010`` for RHEL with High Availability, a distinct
          licence from plain RHEL
        - ``RunInstances:0g00`` for Ubuntu Pro
        - ``RunInstances:0002`` for Windows Server (Full-Base, Core, STIG)
        - ``RunInstances:000g`` for SUSE SLES
        - ``RunInstances`` with no suffix for Amazon Linux, which carries no
          per-licence charge
        """
        allowed = {
            "RunInstances:0010",
            "RunInstances:1010",
            "RunInstances:0g00",
            "RunInstances:0002",
            "RunInstances:000g",
            "RunInstances",
        }
        bad = [p for p in NO_PRODUCT_CODE_FALLBACKS.values() if p.usage_operation not in allowed]
        assert bad == [], f"unexpected billing codes: {bad}"

    def test_table_entries_have_anchored_regex(self):
        """A prefix glob under the same owner admits RHEL_HA-* and the
        -Access2 BYOL images, which are different licensed products. Every
        pattern MUST anchor at both ends."""
        import re as _re

        for pid, p in NO_PRODUCT_CODE_FALLBACKS.items():
            assert p.name_pattern.startswith("^"), f"{pid}: unanchored start"
            assert p.name_pattern.endswith("$"), f"{pid}: unanchored end"
            # And it must actually compile
            _re.compile(p.name_pattern)


def test_every_fallback_owner_is_importable():
    """A product the resolver offers must also pass the import owner check.

    The resolver and the import handler each carry their own notion of which
    accounts publish these images, so a new fallback entry can resolve a
    listing that the import then refuses. This pins the two together.
    """
    # ARRANGE
    from app.packaging.domain.model.image.image_constants import AWS_PUBLISHED_AMI_OWNER_IDS

    # ACT
    owners = {fallback.owner_id for fallback in NO_PRODUCT_CODE_FALLBACKS.values()}

    # ASSERT
    assertpy.assert_that(sorted(owners - AWS_PUBLISHED_AMI_OWNER_IDS)).is_empty()
