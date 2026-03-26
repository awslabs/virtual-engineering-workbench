from pydantic import BaseModel, Field


class ProductsVersionsSyncRequested(BaseModel):
    job_name: str = Field("ProductsVersionsSyncRequested", alias="jobName", const=True)
