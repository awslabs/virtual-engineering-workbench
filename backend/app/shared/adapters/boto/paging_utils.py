import typing
from typing import Generic, TypeVar

import pydantic
from pydantic import ConfigDict

T = TypeVar("T")


class PageInfo(pydantic.BaseModel):
    page_token: typing.Any | None = pydantic.Field(None)
    page_size: int | None = pydantic.Field(None)


class PagedResponse(pydantic.BaseModel, Generic[T]):
    items: list[T] = pydantic.Field(default_factory=list)
    page_token: typing.Any | None = pydantic.Field(None)
    model_config = ConfigDict(arbitrary_types_allowed=True)
