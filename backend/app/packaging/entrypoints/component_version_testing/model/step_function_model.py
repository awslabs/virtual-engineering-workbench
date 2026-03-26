from pydantic import BaseModel, Field


class LaunchTestEnvironmentRequest(BaseModel):
    event_type: str = Field("LaunchTestEnvironmentRequest", alias="eventType")
    component_id: str = Field(..., alias="componentId")
    component_version_id: str = Field(..., alias="componentVersionId")
    test_execution_id: str = Field(..., alias="testExecutionId")


class LaunchTestEnvironmentResponse(BaseModel):
    event_type: str = Field("LaunchTestEnvironmentResponse", alias="eventType")


class CheckTestEnvironmentLaunchStatusRequest(BaseModel):
    event_type: str = Field("CheckTestEnvironmentLaunchStatusRequest", alias="eventType")
    component_version_id: str = Field(..., alias="componentVersionId")
    test_execution_id: str = Field(..., alias="testExecutionId")


class CheckTestEnvironmentLaunchStatusResponse(BaseModel):
    event_type: str = Field("CheckTestEnvironmentLaunchStatusResponse", alias="eventType")
    instances_status: str = Field(..., alias="instancesStatus")


class SetupTestEnvironmentRequest(BaseModel):
    event_type: str = Field("SetupTestEnvironmentRequest", alias="eventType")
    component_version_id: str = Field(..., alias="componentVersionId")
    test_execution_id: str = Field(..., alias="testExecutionId")


class SetupTestEnvironmentResponse(BaseModel):
    event_type: str = Field("SetupTestEnvironmentResponse", alias="eventType")


class CheckTestEnvironmentSetupStatusRequest(BaseModel):
    event_type: str = Field("CheckTestEnvironmentSetupStatusRequest", alias="eventType")
    component_version_id: str = Field(..., alias="componentVersionId")
    test_execution_id: str = Field(..., alias="testExecutionId")


class CheckTestEnvironmentSetupStatusResponse(BaseModel):
    event_type: str = Field("CheckTestEnvironmentSetupStatusResponse", alias="eventType")
    setup_commands_status: str = Field(..., alias="setupCommandsStatus")


class RunComponentVersionTestRequest(BaseModel):
    event_type: str = Field("RunComponentVersionTestRequest", alias="eventType")
    component_id: str = Field(..., alias="componentId")
    component_version_id: str = Field(..., alias="componentVersionId")
    test_execution_id: str = Field(..., alias="testExecutionId")


class RunComponentVersionTestResponse(BaseModel):
    event_type: str = Field("RunComponentVersionTestResponse", alias="eventType")


class CheckComponentVersionTestStatusRequest(BaseModel):
    event_type: str = Field("CheckComponentVersionTestStatusRequest", alias="eventType")
    component_version_id: str = Field(..., alias="componentVersionId")
    test_execution_id: str = Field(..., alias="testExecutionId")


class CheckComponentVersionTestStatusResponse(BaseModel):
    event_type: str = Field("CheckComponentVersionTestStatusResponse", alias="eventType")
    test_commands_status: str = Field(..., alias="testCommandsStatus")


class CompleteComponentVersionTestRequest(BaseModel):
    event_type: str = Field("CompleteComponentVersionTestRequest", alias="eventType")
    component_id: str = Field(..., alias="componentId")
    component_version_id: str = Field(..., alias="componentVersionId")
    test_execution_id: str = Field(..., alias="testExecutionId")


class CompleteComponentVersionTestResponse(BaseModel):
    event_type: str = Field("CompleteComponentVersionTestResponse", alias="eventType")
    component_version_test_status: str = Field(..., alias="componentVersionTestStatus")
