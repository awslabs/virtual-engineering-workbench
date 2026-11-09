from pydantic import BaseModel, Field


class CreateLicenseGrantResult(BaseModel):
    grantId: str = Field(..., title="GrantId")
    grantArn: str = Field(..., title="GrantArn")
    homeRegion: str = Field(..., title="HomeRegion")
