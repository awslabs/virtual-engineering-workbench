from enum import StrEnum


class ImageArchitecture(StrEnum):
    Arm64 = "arm64"
    X86_64 = "x86_64"

    @staticmethod
    def list():
        return list(map(lambda v: v.value, ImageArchitecture))


class ImageSource(StrEnum):
    PIPELINE = "PIPELINE"
    EXISTING_AMI = "EXISTING_AMI"
    MARKETPLACE_PRODUCT = "MARKETPLACE_PRODUCT"
    # An AMI published by AWS itself (RHEL, Windows, SLES, Ubuntu Pro, Amazon
    # Linux). Distinct from MARKETPLACE_PRODUCT because no agreement, product
    # code or License Manager grant exists: AWS is Seller of Record and the
    # licence is priced through the instance-hour billing code. Kept as its own
    # source rather than relaxing MARKETPLACE_PRODUCT's product-code guard, so
    # the entitlement-backed path keeps its invariant intact.
    AWS_PUBLISHED_AMI = "AWS_PUBLISHED_AMI"

    @staticmethod
    def list():
        return list(map(lambda v: v.value, ImageSource))


# Accounts that publish the AMIs behind Marketplace products for which AWS is
# Seller of Record. An AWS_PUBLISHED_AMI import is first checked by
# re-resolving the listing server-side and requiring the resolution to offer
# the submitted AMI; this allowlist is the second check behind that. It is
# what identifies an AMI that has no product code and no Image Service
# ownership, since for those images the owner and the name are all there is to
# go on. Every owner in the resolver's no-product-code table must appear here;
# a test asserts it.
AWS_PUBLISHED_AMI_OWNER_IDS = frozenset(
    {
        "309956199498",  # Red Hat
        "013907871322",  # SUSE
        "137112412989",  # Amazon Linux
        "591542846629",  # Amazon ECS-optimized Amazon Linux
        "099720109477",  # Canonical (Ubuntu Pro)
        "801119661308",  # Microsoft Windows
    }
)


class SubscriptionOwnership(StrEnum):
    VEW_MANAGED = "VEW_MANAGED"
    EXTERNALLY_MANAGED = "EXTERNALLY_MANAGED"
    # No subscription exists to own. AWS grants the licence at RunInstances.
    AWS_MANAGED = "AWS_MANAGED"

    @staticmethod
    def list():
        return list(map(lambda v: v.value, SubscriptionOwnership))
