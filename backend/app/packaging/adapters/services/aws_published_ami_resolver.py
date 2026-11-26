"""Resolves a Marketplace product to a launchable AMI id.

The offer's product code is the discriminator. AWS stamps the product code
into the ``ProductCodes`` of the AMIs published for a product, so filtering
``ec2:DescribeImages`` on it returns exactly those images: one product, one
image family. The listing's own metadata is not enough, because
``ListFulfillmentOptions`` reports only the operating-system family, version
and architecture, which leaves plain RHEL, RHEL for SAP, RHEL with SQL Server
and the GPU variant indistinguishable from one another.

Resolution runs in two steps:

1. ``marketplace-discovery.list_purchase_options(PRODUCT_ID=<pid>)``
   returns the single offer attached to a single-product AMI listing. The
   offer's ``purchaseOptionId`` is the same value as the product code
   carried on the AMI.

2. ``ec2.describe_images(Owners=['aws-marketplace'],
                         Filters=[{Name:'product-code', Values:[<code>]}])``
   returns the AMIs stamped with that code. The step is seller-independent:
   it behaves the same for AWS-sold, partner-sold and vendor-direct
   listings.

The plain-OS products AWS publishes itself are the exception. Their AMIs
carry NO product code, because the licence is priced through the EC2 billing
code (``UsageOperation`` ``RunInstances:0010`` for RHEL, ``:0g00`` for Ubuntu
Pro) rather than through a Marketplace agreement, so
``describe_images(product-code=...)`` returns nothing for them even though
their offer has a ``purchaseOptionId``. For those products the resolver falls
back to the ``NO_PRODUCT_CODE_FALLBACKS`` table of hand-verified (owner, name
regex, architecture, billing code) entries. The table is deliberately narrow:
a product that is neither in it nor backed by a product-coded AMI is reported
as unresolved and the caller surfaces an error, rather than importing a
near-miss.

Entitlement is out of scope. Subscription state, pricing model and agreement
creation belong to the procurement wizard. This service answers only "given a
product id and a region, which AMI ids can it be imported from?".
"""

import logging
import re
from typing import Any, NamedTuple, Optional

import boto3
from botocore.exceptions import ClientError

from app.packaging.adapters.exceptions import adapter_exception
from app.packaging.domain.ports import aws_published_ami_resolver_service
from app.packaging.domain.read_models.aws_published_ami import (
    AwsPublishedAmiCandidate,
    AwsPublishedAmiResolution,
)

logger = logging.getLogger(__name__)

# Characters that end the literal prefix of a name regex.
REGEX_METACHARACTERS = frozenset("\\.[](){}*+?|$^")

MARKETPLACE_DISCOVERY = "marketplace-discovery"
# Discovery is a global service exposed only in us-east-1, regardless of
# where the caller sits.
MARKETPLACE_REGION = "us-east-1"

AMI_STATE_AVAILABLE = "available"

# Owner alias EC2 recognises for every Marketplace-published AMI, regardless
# of which account actually holds the image. Narrower than listing every
# vendor account by id, and vendors can rotate publishing accounts without
# the resolver caring. The product-code filter is what makes the match exact.
MARKETPLACE_OWNER_ALIAS = "aws-marketplace"

# ``filter`` arg of ``list_purchase_options``. ``PRODUCT_ID`` is the one filter
# that returns an offer without the caller already knowing which offer id to
# ask about. An invalid filter type produces ``ValidationException`` carrying
# the full enum, so a typo here fails loudly rather than returning nothing.
PRODUCT_ID_FILTER = "PRODUCT_ID"


class _NoProductCodeFallback(NamedTuple):
    """How to find the AMI for an AWS-published product that carries no
    product code on its image.

    These products exist because AWS prices some licences through the
    EC2 billing code (``UsageOperation``) rather than through a
    Marketplace agreement, so the public AMI has no ``ProductCodes``
    entry to filter on.

    Every match is re-checked against three independent facts, so AWS
    metadata drift fails closed instead of silently importing a near-miss:

    * ``name_pattern`` is matched against the FULL image name. Anchors
      matter: a prefix match would admit RHEL_HA-9.* or the BYOL
      RHEL-9.*-Access2 under the same owner.
    * ``architecture`` is the CPU family the entry is for.
    * ``usage_operation`` is the EC2 billing code, which is the licence
      itself (``RunInstances:0010`` RHEL, ``:0g00`` Ubuntu Pro).
    """

    label: str
    owner_id: str
    name_pattern: str
    architecture: str
    usage_operation: str


# Keyed on Marketplace productId. These products publish AMIs with no product
# code: AWS is Seller of Record and the licence lives in the EC2 billing code
# (``UsageOperation``). Entries are per-architecture, because each
# architecture is its own Marketplace product with its own name pattern.
#
# Anything not in this table AND without a product-coded AMI resolves as
# unresolved. Adding a new entry requires:
#   - the full AMI name regex, anchored at both ends and matching the exact
#     name structure of that family
#   - the architecture
#   - the UsageOperation, which is the real licence (cross-check it with the
#     vendor's SSM parameter where one exists)
# and a test that pins the new entry together with the neighbouring families
# it must not match.
NO_PRODUCT_CODE_FALLBACKS: dict[str, _NoProductCodeFallback] = {
    "cbee603d-70d3-47bf-81f6-6215e6e26c7b": _NoProductCodeFallback(
        "Red Hat Enterprise Linux 8",
        "309956199498",
        r"^RHEL-8\.\d+\.\d+_HVM-\d{8}-x86_64-\d+-Hourly2-GP3$",
        "x86_64",
        "RunInstances:0010",
    ),
    "6d7a0d79-ee54-43e2-a382-ed10e65a19da": _NoProductCodeFallback(
        "Red Hat Enterprise Linux 8 (ARM)",
        "309956199498",
        r"^RHEL-8\.\d+\.\d+_HVM-\d{8}-arm64-\d+-Hourly2-GP3$",
        "arm64",
        "RunInstances:0010",
    ),
    "02bec9ca-1c81-40ac-83a2-aa021e2a0b39": _NoProductCodeFallback(
        "Red Hat Enterprise Linux 9",
        "309956199498",
        r"^RHEL-9\.\d+\.\d+_HVM-\d{8}-x86_64-\d+-Hourly2-GP3$",
        "x86_64",
        "RunInstances:0010",
    ),
    "a7b7603b-909e-4c2e-8e1f-8aa9a3232c54": _NoProductCodeFallback(
        "Red Hat Enterprise Linux 9 (ARM)",
        "309956199498",
        r"^RHEL-9\.\d+\.\d+_HVM-\d{8}-arm64-\d+-Hourly2-GP3$",
        "arm64",
        "RunInstances:0010",
    ),
    "prod-6phnsr36pt73e": _NoProductCodeFallback(
        "Red Hat Enterprise Linux for AWS (RHEL 10 - ARM)",
        "309956199498",
        r"^RHEL-10\.\d+\.\d+_HVM-\d{8}-arm64-\d+-Hourly2-GP3$",
        "arm64",
        "RunInstances:0010",
    ),
    "prod-gnc62tfiwrcyw": _NoProductCodeFallback(
        "Red Hat Enterprise Linux for AWS (RHEL 10)",
        "309956199498",
        r"^RHEL-10\.\d+\.\d+_HVM-\d{8}-x86_64-\d+-Hourly2-GP3$",
        "x86_64",
        "RunInstances:0010",
    ),
    "7f64f24e-b75f-4988-8ef0-729959a0a005": _NoProductCodeFallback(
        "Ubuntu Pro 18.04 LTS",
        "099720109477",
        r"^ubuntu-pro-server/images/hvm-ssd/ubuntu-bionic-18\.04-amd64-pro-server-\d{8}(\.\d+)?$",
        "x86_64",
        "RunInstances:0g00",
    ),
    "83368ddc-03bb-42de-ac79-4efee7953610": _NoProductCodeFallback(
        "Ubuntu Pro 18.04 LTS (ARM)",
        "099720109477",
        r"^ubuntu-pro-server/images/hvm-ssd/ubuntu-bionic-18\.04-arm64-pro-server-\d{8}(\.\d+)?$",
        "arm64",
        "RunInstances:0g00",
    ),
    "89c9b5d3-48a2-4098-813e-86b817274442": _NoProductCodeFallback(
        "Ubuntu Pro 20.04 LTS",
        "099720109477",
        r"^ubuntu-pro-server/images/hvm-ssd/ubuntu-focal-20\.04-amd64-pro-server-\d{8}(\.\d+)?$",
        "x86_64",
        "RunInstances:0g00",
    ),
    "464bc8c1-a73a-40c8-830a-464adc94e082": _NoProductCodeFallback(
        "Ubuntu Pro 20.04 LTS (ARM)",
        "099720109477",
        r"^ubuntu-pro-server/images/hvm-ssd/ubuntu-focal-20\.04-arm64-pro-server-\d{8}(\.\d+)?$",
        "arm64",
        "RunInstances:0g00",
    ),
    "756a488e-8d47-45c0-b2c9-3c4001e3b32a": _NoProductCodeFallback(
        "Ubuntu Pro 22.04 LTS",
        "099720109477",
        r"^ubuntu-pro-server/images/hvm-ssd/ubuntu-jammy-22\.04-amd64-pro-server-\d{8}(\.\d+)?$",
        "x86_64",
        "RunInstances:0g00",
    ),
    "09134ddf-66f5-4beb-b0df-e999c9c35665": _NoProductCodeFallback(
        "Ubuntu Pro 22.04 LTS (ARM)",
        "099720109477",
        r"^ubuntu-pro-server/images/hvm-ssd/ubuntu-jammy-22\.04-arm64-pro-server-\d{8}(\.\d+)?$",
        "arm64",
        "RunInstances:0g00",
    ),
    "38b76542-9c8b-4e9a-acdf-aeacfd3fb322": _NoProductCodeFallback(
        "Ubuntu Pro 24.04 LTS",
        "099720109477",
        r"^ubuntu-pro-server/images/hvm-ssd-gp3/ubuntu-noble-24\.04-amd64-pro-server-\d{8}(\.\d+)?$",
        "x86_64",
        "RunInstances:0g00",
    ),
    "0c9bd00a-6a8c-4f62-8745-7ca0157a60c7": _NoProductCodeFallback(
        "Ubuntu Pro 24.04 LTS (ARM)",
        "099720109477",
        r"^ubuntu-pro-server/images/hvm-ssd-gp3/ubuntu-noble-24\.04-arm64-pro-server-\d{8}(\.\d+)?$",
        "arm64",
        "RunInstances:0g00",
    ),
    # Microsoft Windows Server Base (English, Full). The offer carries a
    # product code but the AMI itself does not (``ProductCodes`` is null), so
    # these resolve through this table like plain RHEL and Ubuntu Pro. Billing
    # code RunInstances:0002 is the Windows licence.
    #
    # Full-Base only. Core-Base is a separate product with its own listing
    # (name ``Windows_Server-{YYYY}-English-Core-Base-...``), so the full-name
    # regex has to exclude it. The SQL Server, Office and Visual Studio
    # bundles under the same Full prefix are genuinely ambiguous, because
    # several editions share one family, and are intentionally left
    # unresolved.
    "13c2dbc9-57fc-4958-922e-a1ba7e223b0d": _NoProductCodeFallback(
        "Microsoft Windows Server 2016 Base",
        "801119661308",
        r"^Windows_Server-2016-English-Full-Base-\d{4}\.\d{2}\.\d{2}$",
        "x86_64",
        "RunInstances:0002",
    ),
    "ef297a90-3ad0-4674-83b4-7f0ec07c39bb": _NoProductCodeFallback(
        "Microsoft Windows Server 2019 Base",
        "801119661308",
        r"^Windows_Server-2019-English-Full-Base-\d{4}\.\d{2}\.\d{2}$",
        "x86_64",
        "RunInstances:0002",
    ),
    "b0e459f5-2c38-4939-ad2a-d9784ecab690": _NoProductCodeFallback(
        "Microsoft Windows Server 2022 Base",
        "801119661308",
        r"^Windows_Server-2022-English-Full-Base-\d{4}\.\d{2}\.\d{2}$",
        "x86_64",
        "RunInstances:0002",
    ),
    "prod-m2jdcqhp4xuec": _NoProductCodeFallback(
        "Microsoft Windows Server 2025 Base",
        "801119661308",
        r"^Windows_Server-2025-English-Full-Base-\d{4}\.\d{2}\.\d{2}$",
        "x86_64",
        "RunInstances:0002",
    ),
    # Amazon Linux 2, published by owner 137112412989 (Amazon).
    # UsageOperation ``RunInstances`` with no colon suffix is plain
    # Linux/UNIX billing, so there is no per-licence charge. Both ``-gp2``
    # and ``-ebs`` boot-volume suffixes exist, so the pattern tolerates
    # either. ``-minimal`` is a different product id and must not match.
    "8b955bdf-2a12-455e-9a23-2f5413d383ae": _NoProductCodeFallback(
        "Amazon Linux 2 (x86_64)",
        "137112412989",
        r"^amzn2-ami-hvm-2\.0\.\d{8}\.\d+-x86_64-(gp2|ebs)$",
        "x86_64",
        "RunInstances",
    ),
    "73e47844-343f-49d7-bcdb-69b3588eee9f": _NoProductCodeFallback(
        "Amazon Linux 2 (arm64)",
        "137112412989",
        r"^amzn2-ami-hvm-2\.0\.\d{8}\.\d+-arm64-(gp2|ebs)$",
        "arm64",
        "RunInstances",
    ),
    # SUSE Linux Enterprise Server, published by owner 013907871322.
    # UsageOperation ``RunInstances:000g`` is the SUSE licence billing code.
    # The patterns must exclude three neighbouring families under the same
    # owner: ``-ecs-`` (container-optimised), ``-sapcal-`` (SAP calculation)
    # and ``-sap-`` (the full SAP variant, which has its own product).
    "c284b9cf-620f-4c68-9492-812fc92a2c40": _NoProductCodeFallback(
        "SUSE Linux Enterprise Server 12",
        "013907871322",
        r"^suse-sles-12-sp\d+-v\d{8}-hvm-ssd-x86_64$",
        "x86_64",
        "RunInstances:000g",
    ),
    "472fae9d-3a9d-469b-8946-2282d6d4ff36": _NoProductCodeFallback(
        "SUSE Linux Enterprise Server 15",
        "013907871322",
        r"^suse-sles-15-sp\d+-v\d{8}-hvm-ssd-x86_64$",
        "x86_64",
        "RunInstances:000g",
    ),
    "2549a4da-5743-4a51-83b7-c751e4cda8b8": _NoProductCodeFallback(
        "SUSE Linux Enterprise Server for Arm 15",
        "013907871322",
        r"^suse-sles-15-sp\d+-v\d{8}-hvm-ssd-arm64$",
        "arm64",
        "RunInstances:000g",
    ),
    # Microsoft Windows Server Core (English). Same shape as the Full-Base
    # entries above: owner 801119661308, no product code on the AMI, and the
    # licence in UsageOperation ``RunInstances:0002``. ``-Core-Base-`` and
    # ``-Full-Base-`` are distinct product families and must not cross-match,
    # which is why each pattern is anchored to its own. AWS also publishes the
    # current image of each release at
    # /aws/service/ami-windows-latest/Windows_Server-{YEAR}-English-Core-Base,
    # which is the cheapest way to re-check an entry.
    "a7279983-399c-44f5-84b3-4146456df5bc": _NoProductCodeFallback(
        "Microsoft Windows Server 2016 Core",
        "801119661308",
        r"^Windows_Server-2016-English-Core-Base-\d{4}\.\d{2}\.\d{2}$",
        "x86_64",
        "RunInstances:0002",
    ),
    "8033bff9-9dea-464e-8aec-bb4452c0ca9c": _NoProductCodeFallback(
        "Microsoft Windows Server 2019 Core",
        "801119661308",
        r"^Windows_Server-2019-English-Core-Base-\d{4}\.\d{2}\.\d{2}$",
        "x86_64",
        "RunInstances:0002",
    ),
    "b6d510b1-700d-4af5-879b-b7c877de9348": _NoProductCodeFallback(
        "Microsoft Windows Server 2022 Core",
        "801119661308",
        r"^Windows_Server-2022-English-Core-Base-\d{4}\.\d{2}\.\d{2}$",
        "x86_64",
        "RunInstances:0002",
    ),
    "prod-zmfhc2iwvemfu": _NoProductCodeFallback(
        "Microsoft Windows Server 2025 Core",
        "801119661308",
        r"^Windows_Server-2025-English-Core-Base-\d{4}\.\d{2}\.\d{2}$",
        "x86_64",
        "RunInstances:0002",
    ),
    # Microsoft Windows Server STIG compliance variants. AWS publishes two
    # STIG hardening families per Windows release: ``-STIG-Full-`` is the
    # Base equivalent (full GUI) and ``-STIG-Core-`` is the Core equivalent
    # (no GUI). Only 2016 and 2019 have a single-product Marketplace listing;
    # 2022 and 2025 are STIG-only through SSM, so there is nothing to resolve
    # for them here. The patterns are anchored to their exact family so they
    # cannot cross-match ``-Full-Base-`` or ``-Core-Base-``.
    "3c0cb921-9922-40fd-bb22-e221e24660d8": _NoProductCodeFallback(
        "Microsoft Windows Server 2016 Core for STIG compliance",
        "801119661308",
        r"^Windows_Server-2016-English-STIG-Core-\d{4}\.\d{2}\.\d{2}$",
        "x86_64",
        "RunInstances:0002",
    ),
    "fac1f28c-34f6-4ed4-902b-e59c7b43bbaf": _NoProductCodeFallback(
        "Microsoft Windows Server 2019 Core for STIG compliance",
        "801119661308",
        r"^Windows_Server-2019-English-STIG-Core-\d{4}\.\d{2}\.\d{2}$",
        "x86_64",
        "RunInstances:0002",
    ),
    "d15bfcf9-11f4-49f2-af8e-af0712e06aef": _NoProductCodeFallback(
        "Microsoft Windows Server 2016 Base for STIG compliance",
        "801119661308",
        r"^Windows_Server-2016-English-STIG-Full-\d{4}\.\d{2}\.\d{2}$",
        "x86_64",
        "RunInstances:0002",
    ),
    "2b200d57-e974-4da2-9fd5-160d997638db": _NoProductCodeFallback(
        "Microsoft Windows Server 2019 Base for STIG compliance",
        "801119661308",
        r"^Windows_Server-2019-English-STIG-Full-\d{4}\.\d{2}\.\d{2}$",
        "x86_64",
        "RunInstances:0002",
    ),
    # Amazon ECS-Optimized Amazon Linux: Amazon Linux 2 plus the ECS agent.
    # Owner 591542846629 is a different account from the plain Amazon Linux 2
    # one above, so this entry cannot be folded into it. The listing has no
    # arm64 variant, which is why only x86_64 appears here; the
    # /aws/service/ecs/optimized-ami SSM tree is where to check that.
    # UsageOperation ``RunInstances`` is plain Linux/UNIX, with no per-licence
    # charge.
    "52d5fd7f-92c7-4d60-a830-41a596f4d8f3": _NoProductCodeFallback(
        "Amazon ECS-Optimized Amazon Linux AMI",
        "591542846629",
        r"^amzn2-ami-ecs-hvm-2\.0\.\d{8}-x86_64-ebs$",
        "x86_64",
        "RunInstances",
    ),
    # Red Hat Enterprise Linux 8.4 with High Availability. The listing is
    # labelled "8.4", but Red Hat tags the current HA AMI stream under the
    # broader ``RHEL_HA-8.*_HVM-...`` family, so this entry resolves to the
    # current 8.x build in the same way the plain RHEL 8 entry above does.
    # Owner 309956199498 (Red Hat). UsageOperation ``RunInstances:1010`` is
    # the HA licence, distinct from plain RHEL's ``:0010``. The SAP HA 8.x
    # listings are deliberately absent from this table: no
    # ``RHEL-SAP-HA-8.*`` AMI is published under this owner, so they stay
    # unresolved rather than resolving to the non-SAP HA image.
    "57466132-6b82-42ce-bb80-3a480d63ea39": _NoProductCodeFallback(
        "Red Hat Enterprise Linux 8.4 with High Availability",
        "309956199498",
        r"^RHEL_HA-8\.\d+\.\d+_HVM-\d{8}-x86_64-\d+-Hourly2-GP3$",
        "x86_64",
        "RunInstances:1010",
    ),
}


def _name_prefix(pattern: str) -> str:
    """The literal prefix of an anchored name regex, for the EC2 name filter.

    ``^Windows_Server-2019-English-Core-Base-\\d{4}...`` yields
    ``Windows_Server-2019-English-Core-Base-``. The exact regex still runs on
    the response, so a conservative prefix only costs response size.
    """
    literal = []
    for char in pattern.lstrip("^"):
        if char in REGEX_METACHARACTERS:
            break
        literal.append(char)
    return "".join(literal)


class AwsPublishedAmiResolver(aws_published_ami_resolver_service.AwsPublishedAmiResolverService):
    """Product-code-based AMI resolver with a narrow fallback for the
    plain-OS products AWS publishes without product codes.

    Independent of seller: it works the same for AWS-sold, partner-sold via
    679593333241, and vendor-direct Marketplace AMIs. The only thing that
    varies between them is whether the caller must already have accepted an
    agreement for the product, which is the procurement wizard's concern and
    not this resolver's.
    """

    def __init__(self, boto_session: Optional[boto3.Session] = None) -> None:
        self._boto_session = boto_session

    def resolve(self, product_id: str, region: str) -> AwsPublishedAmiResolution:
        """Resolve ``product_id`` to the AMI(s) it can be imported from.

        The offer's product code is the discriminator: EC2 returns exactly the
        AMIs the vendor stamped with it, which is one image family per
        product. Products AWS publishes without a product code fall back to a
        hand-verified (owner, name, architecture, billing code) entry.

        ``unambiguous`` is True only when one architecture remains, so a
        product shipping x86_64 and arm64 under one code is handed to the
        caller to choose from instead of resolving to whichever build is
        newer. When nothing identifies an AMI, the resolution is returned
        with no candidates and the caller reports it.

        Says nothing about entitlement: whether the account needs an
        agreement for the product is the procurement wizard's concern.
        """
        product_code = self.__describe_offer(product_id)

        if product_code:
            candidates = self.__describe_images_by_product_code(product_code, region)
            if candidates:
                return self.__to_resolution(product_id, candidates)
            logger.warning(
                "Product %s offers product-code %s but no available AMI matches in %s",
                product_id,
                product_code,
                region,
            )
            # Some products carry a code on the offer but not on the AMI, so
            # try the table before giving up.

        fallback = NO_PRODUCT_CODE_FALLBACKS.get(product_id)
        if not fallback:
            logger.warning("Product %s has no product-coded AMI and no verified fallback", product_id)
            return AwsPublishedAmiResolution(productId=product_id, unambiguous=False)

        candidates = self.__describe_images_by_fallback(fallback, region)
        if not candidates:
            logger.warning(
                "No AMIs match verified fallback for %s (owner=%s pattern=%r)",
                product_id,
                fallback.owner_id,
                fallback.name_pattern,
            )
            return AwsPublishedAmiResolution(productId=product_id, unambiguous=False)

        return self.__to_resolution(product_id, candidates)

    @staticmethod
    def __to_resolution(product_id: str, candidates: list[AwsPublishedAmiCandidate]) -> AwsPublishedAmiResolution:
        """Newest build per architecture, unambiguous only if one remains."""
        newest_per_architecture: dict[str, AwsPublishedAmiCandidate] = {}
        for candidate in sorted(candidates, key=lambda c: c.creationDate or "", reverse=True):
            newest_per_architecture.setdefault(candidate.architecture or "", candidate)
        offered = list(newest_per_architecture.values())
        return AwsPublishedAmiResolution(
            productId=product_id,
            unambiguous=len(offered) == 1,
            candidates=offered,
        )

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def __discovery_client(self):
        session = self._boto_session or boto3
        return session.client(MARKETPLACE_DISCOVERY, region_name=MARKETPLACE_REGION)

    def __ec2_client(self, region: str):
        session = self._boto_session or boto3
        return session.client("ec2", region_name=region)

    def __describe_offer(self, product_id: str) -> Optional[str]:
        """Return the product code of the single-product AMI offer attached
        to ``product_id``, or ``None`` if the product has no AMI purchase
        option.

        The ``purchaseOptionId`` returned by ``ListPurchaseOptions`` is the
        same value as the AMI's ``ProductCodes[].ProductCodeId``, which is
        what makes it usable as the EC2 ``product-code`` filter.
        """
        try:
            response = self.__discovery_client().list_purchase_options(
                filters=[{"filterType": PRODUCT_ID_FILTER, "filterValues": [product_id]}]
            )
        except ClientError as e:
            raise adapter_exception.AdapterException(f"Failed to list purchase options for product {product_id}: {e}")

        options = response.get("purchaseOptions") or []
        if not options:
            return None

        return options[0].get("purchaseOptionId")

    def __describe_images_by_product_code(self, product_code: str, region: str) -> list[AwsPublishedAmiCandidate]:
        """Return all available AMIs stamped with ``product_code`` in ``region``.

        Owners is ``aws-marketplace``: the EC2 owner alias that matches
        every published Marketplace AMI regardless of which vendor account
        physically holds it. The product-code filter is what makes the
        match exact; the owner alias is a safety belt against someone
        reusing a product code string on an AMI they published themselves.
        """
        filters: list[dict[str, Any]] = [
            {"Name": "product-code", "Values": [product_code]},
            {"Name": "state", "Values": [AMI_STATE_AVAILABLE]},
        ]
        try:
            response = self.__ec2_client(region).describe_images(Owners=[MARKETPLACE_OWNER_ALIAS], Filters=filters)
        except ClientError as e:
            raise adapter_exception.AdapterException(
                f"Failed to describe images for product code {product_code} in {region}: {e}"
            )
        return [_to_candidate(image, region) for image in response.get("Images", [])]

    def __describe_images_by_fallback(
        self, fallback: _NoProductCodeFallback, region: str
    ) -> list[AwsPublishedAmiCandidate]:
        """Return AMIs that match the hand-verified fallback for a
        no-product-code product.

        ``describe_images`` filters on the owner, the name prefix, the
        architecture and the state, and the exact name regex and billing code
        are applied here. The prefix filter alone would admit neighbouring
        families (``RHEL_HA-9.*``, the BYOL ``RHEL-9.*-Access2``) under the
        same owner, and a different ``UsageOperation`` under one owner is a
        different licensed product, so both exact checks are required. The
        prefix keeps the response small: some of these owners publish tens of
        thousands of images per region.
        """
        name_regex = re.compile(fallback.name_pattern)
        try:
            response = self.__ec2_client(region).describe_images(
                Owners=[fallback.owner_id],
                Filters=[
                    {"Name": "name", "Values": [f"{_name_prefix(fallback.name_pattern)}*"]},
                    {"Name": "architecture", "Values": [fallback.architecture]},
                    {"Name": "state", "Values": [AMI_STATE_AVAILABLE]},
                ],
            )
        except ClientError as e:
            raise adapter_exception.AdapterException(
                f"Failed to describe images for owner {fallback.owner_id} in {region}: {e}"
            )

        matched: list[AwsPublishedAmiCandidate] = []
        for image in response.get("Images", []):
            if not name_regex.fullmatch(image.get("Name") or ""):
                continue
            if image.get("UsageOperation") != fallback.usage_operation:
                continue
            matched.append(_to_candidate(image, region))
        return matched


def _to_candidate(image: dict[str, Any], region: str) -> AwsPublishedAmiCandidate:
    return AwsPublishedAmiCandidate(
        amiId=image["ImageId"],
        amiName=image.get("Name") or image["ImageId"],
        ownerId=image["OwnerId"],
        architecture=image.get("Architecture"),
        platformDetails=image.get("PlatformDetails"),
        usageOperation=image.get("UsageOperation"),
        creationDate=image.get("CreationDate"),
        region=region,
    )
