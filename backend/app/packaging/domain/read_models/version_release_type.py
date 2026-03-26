from enum import StrEnum


class VersionReleaseType(StrEnum):
    Major = "MAJOR"
    Minor = "MINOR"
    Patch = "PATCH"

    @staticmethod
    def list():
        return list(map(lambda v: v.value, VersionReleaseType))
