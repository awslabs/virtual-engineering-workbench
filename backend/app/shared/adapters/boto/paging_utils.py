import typing
from typing import Generic, TypeVar

import pydantic

T = TypeVar("T")


class PageInfo(pydantic.BaseModel):
    page_token: typing.Any | None = pydantic.Field(None)
    page_size: int | None = pydantic.Field(None)


class PagedResponse(pydantic.BaseModel, Generic[T]):
    items: list[T] = pydantic.Field(default_factory=list)
    page_token: typing.Any | None = pydantic.Field(None)

    class Config:
        arbitrary_types_allowed = True
