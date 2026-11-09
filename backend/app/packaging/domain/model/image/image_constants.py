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

    @staticmethod
    def list():
        return list(map(lambda v: v.value, ImageSource))


class SubscriptionOwnership(StrEnum):
    VEW_MANAGED = "VEW_MANAGED"
    EXTERNALLY_MANAGED = "EXTERNALLY_MANAGED"

    @staticmethod
    def list():
        return list(map(lambda v: v.value, SubscriptionOwnership))
