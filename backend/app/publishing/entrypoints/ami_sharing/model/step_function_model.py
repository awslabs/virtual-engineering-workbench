from typing import Optional

from pydantic import BaseModel, Field


class DecideActionRequest(BaseModel):
    event_type: str = Field("DecideActionRequest", alias="eventType")
    product_id: str = Field(..., alias="productId")
    version_id: str = Field(..., alias="versionId")
    aws_account_id: str = Field(..., alias="awsAccountId")
    product_type: str = Field(..., alias="productType")


class DecideActionResponse(BaseModel):
    event_type: str = Field("DecideActionResponse", alias="eventType")
    decision: str = Field(..., alias="decision", description="COPY/SHARE/DONE/LICENSE_GRANT/VERIFY_EXTERNAL_GRANT")
    original_ami_id: Optional[str] = Field(None, alias="originalAmiId")
    copied_ami_id: Optional[str] = Field(None, alias="copiedAmiId")
    region: str = Field(..., alias="region")
    image_id: Optional[str] = Field(None, alias="imageId")
    project_id: Optional[str] = Field(None, alias="projectId")
    license_arn: Optional[str] = Field(None, alias="licenseArn")
    home_region: Optional[str] = Field(None, alias="homeRegion")
    grant_name: Optional[str] = Field(None, alias="grantName")


class CopyAmiRequest(BaseModel):
    event_type: str = Field("CopyAmiRequest", alias="eventType")
    original_ami_id: str = Field(..., alias="originalAmiId")
    region: str = Field(..., alias="region")


class CopyAmiResponse(BaseModel):
    event_type: str = Field("CopyAmiResponse", alias="eventType")
    copied_ami_id: str = Field(..., alias="copiedAmiId")


class ShareAmiRequest(BaseModel):
    event_type: str = Field("ShareAmiRequest", alias="eventType")
    original_ami_id: str = Field(..., alias="originalAmiId")
    copied_ami_id: str = Field(..., alias="copiedAmiId")
    region: str = Field(..., alias="region")
    aws_account_id: str = Field(..., alias="awsAccountId")


class ShareAmiResponse(BaseModel):
    event_type: str = Field("ShareAmiResponse", alias="eventType")


class VerifyCopyRequest(BaseModel):
    event_type: str = Field("VerifyCopyRequest", alias="eventType")
    region: str = Field(..., alias="region")
    copied_ami_id: str = Field(..., alias="copiedAmiId")


class VerifyCopyResponse(BaseModel):
    event_type: str = Field("VerifyCopyResponse", alias="eventType")
    is_copy_verified: bool = Field(..., alias="isCopyVerified")


class SucceedAmiSharingRequest(BaseModel):
    event_type: str = Field("SucceedAmiSharingRequest", alias="eventType")
    product_id: str = Field(..., alias="productId")
    version_id: str = Field(..., alias="versionId")
    aws_account_id: str = Field(..., alias="awsAccountId")
    copied_ami_id: Optional[str] = Field(
        ..., alias="copiedAmiId"
    )  # Required but nullable: callers must explicitly pass this field, even if the value is None
    previous_event_name: str = Field(..., alias="previousEventName")
    old_version_id: Optional[str] = Field(None, alias="oldVersionId")
    product_type: str = Field(..., alias="productType")


class SucceedAmiSharingResponse(BaseModel):
    event_type: str = Field("SucceedAmiSharingResponse", alias="eventType")


class FailAmiSharingRequest(BaseModel):
    event_type: str = Field("FailAmiSharingRequest", alias="eventType")
    product_id: str = Field(..., alias="productId")
    version_id: str = Field(..., alias="versionId")
    aws_account_id: str = Field(..., alias="awsAccountId")


class FailAmiSharingResponse(BaseModel):
    event_type: str = Field("FailAmiSharingResponse", alias="eventType")


class CreateLicenseGrantRequest(BaseModel):
    event_type: str = Field("CreateLicenseGrantRequest", alias="eventType")
    product_id: str = Field(..., alias="productId")
    version_id: str = Field(..., alias="versionId")
    aws_account_id: str = Field(..., alias="awsAccountId")
    image_id: str = Field(..., alias="imageId")
    grant_name: str = Field(..., alias="grantName")
    project_id: str = Field(..., alias="projectId")


class CreateLicenseGrantResponse(BaseModel):
    event_type: str = Field("CreateLicenseGrantResponse", alias="eventType")
    grant_id: str = Field(..., alias="grantId")
    grant_arn: str = Field(..., alias="grantArn")
    home_region: str = Field(..., alias="homeRegion")


class AcceptLicenseGrantRequest(BaseModel):
    event_type: str = Field("AcceptLicenseGrantRequest", alias="eventType")
    grant_id: str = Field(..., alias="grantId")
    grant_arn: str = Field(..., alias="grantArn")
    aws_account_id: str = Field(..., alias="awsAccountId")
    project_id: str = Field(..., alias="projectId")
    home_region: str = Field(..., alias="homeRegion")


class AcceptLicenseGrantResponse(BaseModel):
    event_type: str = Field("AcceptLicenseGrantResponse", alias="eventType")


class VerifyLicenseGrantRequest(BaseModel):
    event_type: str = Field("VerifyLicenseGrantRequest", alias="eventType")
    ami_id: str = Field(..., alias="amiId")
    region: str = Field(..., alias="region")
    aws_account_id: str = Field(..., alias="awsAccountId")


class VerifyLicenseGrantResponse(BaseModel):
    event_type: str = Field("VerifyLicenseGrantResponse", alias="eventType")
    is_accessible: bool = Field(..., alias="isAccessible")


class VerifyExternalGrantRequest(BaseModel):
    event_type: str = Field("VerifyExternalGrantRequest", alias="eventType")
    product_id: str = Field(..., alias="productId")
    version_id: str = Field(..., alias="versionId")
    aws_account_id: str = Field(..., alias="awsAccountId")
    license_arn: str = Field(..., alias="licenseArn")
    ami_id: str = Field(..., alias="amiId")
    region: str = Field(..., alias="region")
    home_region: str = Field(..., alias="homeRegion")


class VerifyExternalGrantResponse(BaseModel):
    event_type: str = Field("VerifyExternalGrantResponse", alias="eventType")
    grant_verified: bool = Field(..., alias="grantVerified")
