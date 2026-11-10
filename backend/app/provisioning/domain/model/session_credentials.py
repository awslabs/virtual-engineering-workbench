from pydantic import BaseModel, Field


class SessionCredentials(BaseModel):
    accessKeyId: str = Field(..., title="AccessKeyId")
    secretAccessKey: str = Field(..., title="SecretAccessKey")
    sessionToken: str = Field(..., title="SessionToken")
    instanceId: str = Field(..., title="InstanceId")
    region: str = Field(..., title="Region")
