from pydantic import BaseModel, Field


class LicenseGrantResult(BaseModel):
    grantArn: str = Field(..., title="GrantArn")
    status: str = Field(..., title="Status")
