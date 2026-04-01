from typing import Literal

from pydantic import BaseModel, Field


class ProductsVersionsSyncRequested(BaseModel):
    job_name: Literal["ProductsVersionsSyncRequested"] = Field("ProductsVersionsSyncRequested", alias="jobName")
