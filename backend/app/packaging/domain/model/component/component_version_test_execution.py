from enum import StrEnum
from typing import Optional

from pydantic import Field

from app.shared.adapters.unit_of_work_v2 import unit_of_work


class ComponentVersionTestExecutionCommandStatus(StrEnum):
    Failed = "FAILED"
    Pending = "PENDING"
    Running = "RUNNING"
    Success = "SUCCESS"

    @staticmethod
    def list():
        return list(map(lambda v: v.value, ComponentVersionTestExecutionCommandStatus))


class ComponentVersionTestExecutionInstanceStatus(StrEnum):
    Connected = "CONNECTED"
    Disconnected = "DISCONNECTED"

    @staticmethod
    def list():
        return list(map(lambda v: v.value, ComponentVersionTestExecutionInstanceStatus))


class ComponentVersionTestStatus(StrEnum):
    Failed = "FAILED"
    Success = "SUCCESS"

    @staticmethod
    def list():
        return list(map(lambda v: v.value, ComponentVersionTestStatus))


class ComponentVersionTestExecutionStatus(StrEnum):
    Failed = "FAILED"
    Pending = "PENDING"
    Running = "RUNNING"
    Success = "SUCCESS"

    @staticmethod
    def list():
        return list(map(lambda v: v.value, ComponentVersionTestExecutionStatus))


class ComponentVersionTestExecutionPrimaryKey(unit_of_work.PrimaryKey):
    componentVersionId: str = Field(..., title="ComponentVersionId")
    testExecutionId: str = Field(..., title="TestExecutionId")
    instanceId: str = Field(..., title="InstanceId")


class ComponentVersionTestExecution(unit_of_work.Entity):
    componentVersionId: str = Field(..., title="ComponentVersionId")
    testExecutionId: str = Field(..., title="TestExecutionId")
    instanceId: str = Field(..., title="InstanceId")
    instanceArchitecture: str = Field(..., title="InstanceArchitecture")
    instanceImageUpstreamId: str = Field(..., title="InstanceImageId")
    instanceOsVersion: str = Field(..., title="InstanceOsVersion")
    instancePlatform: str = Field(..., title="InstancePlatform")
    instanceStatus: ComponentVersionTestExecutionInstanceStatus = Field(..., title="InstanceStatus")
    s3LogLocation: Optional[str] = Field(None, title="S3LogLocation")
    setupCommandId: Optional[str] = Field(None, title="SetupCommandId")
    setupCommandStatus: Optional[ComponentVersionTestExecutionCommandStatus] = Field(None, title="SetupCommandStatus")
    status: ComponentVersionTestExecutionStatus = Field(..., title="Status")
    testCommandId: Optional[str] = Field(None, title="TestCommandId")
    testCommandStatus: Optional[ComponentVersionTestExecutionCommandStatus] = Field(None, title="TestCommandStatus")
    createDate: str = Field(..., title="CreateDate")
    lastUpdateDate: str = Field(..., title="LastUpdateDate")
