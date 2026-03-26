from enum import StrEnum
from typing import List

from pydantic import Field

from app.shared.adapters.unit_of_work_v2 import unit_of_work


class ComponentPlatform(StrEnum):
    Linux = "Linux"
    Windows = "Windows"

    @staticmethod
    def list():
        return list(map(lambda v: v.value, ComponentPlatform))


class ComponentStatus(StrEnum):
    Archived = "ARCHIVED"
    Created = "CREATED"

    @staticmethod
    def list():
        return list(map(lambda v: v.value, ComponentStatus))


class ComponentSupportedArchitectures(StrEnum):
    Amd64 = "amd64"
    Arm64 = "arm64"

    @staticmethod
    def list():
        return list(map(lambda v: v.value, ComponentSupportedArchitectures))


class ComponentSupportedOsVersions(StrEnum):
    Ubuntu_24 = "Ubuntu 24"
    Windows_2025 = "Microsoft Windows Server 2025"

    @staticmethod
    def list():
        return list(map(lambda v: v.value, ComponentSupportedOsVersions))


class ComponentPrimaryKey(unit_of_work.PrimaryKey):
    componentId: str = Field(..., title="ComponentId")


class Component(unit_of_work.Entity):
    componentId: str = Field(..., title="ComponentId")
    componentDescription: str = Field(..., title="ComponentDescription")
    componentName: str = Field(..., title="ComponentName")
    componentPlatform: str = Field(..., title="ComponentPlatform")
    componentSupportedArchitectures: List[str] = Field(..., title="ComponentSupportedArchitectures")
    componentSupportedOsVersions: List[str] = Field(..., title="ComponentSupportedOsVersions")
    status: ComponentStatus = Field(..., title="Status")
    createDate: str = Field(..., title="CreateDate")
    createdBy: str = Field(..., title="CreatedBy")
    lastUpdateDate: str = Field(..., title="LastUpdateDate")
    lastUpdatedBy: str = Field(..., title="LastUpdatedBy")
