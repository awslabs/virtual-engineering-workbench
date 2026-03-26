import typing
from enum import StrEnum

from pydantic import BaseModel, Field


class ComponentVersionEntryType(StrEnum):
    Main = "MAIN"
    Helper = "HELPER"

    @staticmethod
    def list():
        return list(map(lambda v: v.value, ComponentVersionEntryType))


class ComponentVersionEntryPosition(StrEnum):
    Append = "APPEND"
    Prepend = "PREPEND"

    @staticmethod
    def list():
        return list(map(lambda v: v.value, ComponentVersionEntryPosition))


class ComponentVersionEntry(BaseModel):
    componentId: str = Field(..., title="ComponentId")
    componentName: str = Field(..., title="ComponentName")
    componentVersionId: str = Field(..., title="ComponentVersionId")
    componentVersionName: str = Field(..., title="ComponentVersionName")
    componentVersionType: typing.Optional[ComponentVersionEntryType] = Field(
        ComponentVersionEntryType.Helper.value, title="ComponentVersionType"
    )
    order: typing.Optional[int] = Field(None, title="Order")
    position: typing.Optional[ComponentVersionEntryPosition] = Field(None, title="Position")
