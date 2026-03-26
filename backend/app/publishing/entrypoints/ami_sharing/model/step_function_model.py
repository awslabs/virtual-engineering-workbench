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
    decision: str = Field(..., alias="decision", description="COPY/SHARE/DONE")
    original_ami_id: Optional[str] = Field(None, alias="originalAmiId")
    copied_ami_id: Optional[str] = Field(None, alias="copiedAmiId")
    region: str = Field(..., alias="region")


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
    copied_ami_id: Optional[str] = Field(..., alias="copiedAmiId")
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
