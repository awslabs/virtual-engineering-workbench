from enum import StrEnum
from typing import Optional

from pydantic import Field

from app.shared.adapters.unit_of_work_v2 import unit_of_work


class RecipeVersionTestExecutionCommandStatus(StrEnum):
    Failed = "FAILED"
    Pending = "PENDING"
    Running = "RUNNING"
    Success = "SUCCESS"

    @staticmethod
    def list():
        return list(map(lambda v: v.value, RecipeVersionTestExecutionCommandStatus))


class RecipeVersionTestExecutionInstanceStatus(StrEnum):
    Connected = "CONNECTED"
    Disconnected = "DISCONNECTED"

    @staticmethod
    def list():
        return list(map(lambda v: v.value, RecipeVersionTestExecutionInstanceStatus))


class RecipeVersionTestExecutionStatus(StrEnum):
    Failed = "FAILED"
    Pending = "PENDING"
    Running = "RUNNING"
    Success = "SUCCESS"

    @staticmethod
    def list():
        return list(map(lambda v: v.value, RecipeVersionTestExecutionStatus))


class RecipeVersionTestExecutionPrimaryKey(unit_of_work.PrimaryKey):
    recipeVersionId: str = Field(..., title="RecipeVersionId")
    testExecutionId: str = Field(..., title="TestExecutionId")


class RecipeVersionTestExecution(unit_of_work.Entity):
    recipeVersionId: str = Field(..., title="RecipeVersionId")
    testExecutionId: str = Field(..., title="TestExecutionId")
    instanceId: str = Field(..., title="InstanceId")
    instanceArchitecture: str = Field(..., title="InstanceArchitecture")
    instanceOsVersion: str = Field(..., title="InstanceOsVersion")
    instancePlatform: str = Field(..., title="InstancePlatform")
    instanceStatus: RecipeVersionTestExecutionInstanceStatus = Field(..., title="InstanceStatus")
    instanceImageUpstreamId: str = Field(..., title="InstanceImageId")
    s3LogLocation: Optional[str] = Field(None, title="S3LogLocation")
    setupCommandId: Optional[str] = Field(None, title="SetupCommandId")
    setupCommandStatus: Optional[RecipeVersionTestExecutionCommandStatus] = Field(None, title="SetupCommandStatus")
    status: RecipeVersionTestExecutionStatus = Field(..., title="Status")
    testCommandId: Optional[str] = Field(None, title="TestCommandId")
    testCommandStatus: Optional[RecipeVersionTestExecutionCommandStatus] = Field(None, title="TestCommandStatus")
    createDate: str = Field(..., title="CreateDate")
    lastUpdateDate: str = Field(..., title="LastUpdateDate")
