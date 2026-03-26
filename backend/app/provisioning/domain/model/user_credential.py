from pydantic import BaseModel, Field


class UserCredential(BaseModel):
    username: str = Field(..., title="Username")
    password: str = Field(..., title="Password")
