import pydantic


class ProjectAssignment(pydantic.BaseModel):
    userId: str = pydantic.Field(...)
    roles: list[str] = pydantic.Field(...)
