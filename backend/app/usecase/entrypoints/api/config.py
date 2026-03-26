import os

from pydantic import BaseModel


class AppConfig(BaseModel):
    """Reference config — add environment variables as needed."""

    def get_bounded_context_name(self) -> str:
        return os.environ.get("BOUNDED_CONTEXT", "usecase")
