import abc

import pydantic


class ValueObject(pydantic.BaseModel, abc.ABC):
    model_config = pydantic.ConfigDict(frozen=True, arbitrary_types_allowed=True)
