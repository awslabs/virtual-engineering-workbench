from pydantic import BaseModel, Field

from app.packaging.domain.model.component import component_version_test_execution


class ComponentVersionTestExecutionSummary(BaseModel):
    componentVersionId: str = Field(..., title="ComponentVersionId")
    instanceArchitecture: str = Field(..., title="InstanceArchitecture")
    instanceId: str = Field(..., title="InstanceId")
    instanceImageUpstreamId: str = Field(..., title="InstanceImageId")
    instanceOsVersion: str = Field(..., title="InstanceOsVersion")
    instancePlatform: str = Field(..., title="InstancePlatform")
    status: component_version_test_execution.ComponentVersionTestExecutionStatus = Field(..., title="Status")
    testExecutionId: str = Field(..., title="TestExecutionId")
    createDate: str = Field(..., title="CreateDate")
    lastUpdateDate: str = Field(..., title="LastUpdateDate")
