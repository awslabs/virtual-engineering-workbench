from pydantic import Field

from app.shared.adapters.unit_of_work_v2 import unit_of_work


class SharedAmiPrimaryKey(unit_of_work.PrimaryKey):
    originalAmiId: str = Field(..., title="OriginalAmiId")
    awsAccountId: str = Field(..., title="AwsAccountId")


class SharedAmi(unit_of_work.Entity):
    originalAmiId: str = Field(..., title="OriginalAmiId")
    copiedAmiId: str = Field(..., title="CopiedAmiId")
    awsAccountId: str = Field(..., title="AwsAccountId")
    region: str = Field(..., title="Region")
    createDate: str = Field(..., title="CreateDate")
    lastUpdateDate: str = Field(..., title="LastUpdateDate")
