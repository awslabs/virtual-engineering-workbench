from pydantic import BaseModel, Field


class LaunchTestEnvironmentRequest(BaseModel):
    event_type: str = Field("LaunchTestEnvironmentRequest", alias="eventType")
    project_id: str = Field(..., alias="projectId")
    recipe_id: str = Field(..., alias="recipeId")
    recipe_version_id: str = Field(..., alias="recipeVersionId")
    test_execution_id: str = Field(..., alias="testExecutionId")


class LaunchTestEnvironmentResponse(BaseModel):
    event_type: str = Field("LaunchTestEnvironmentResponse", alias="eventType")


class CheckTestEnvironmentLaunchStatusRequest(BaseModel):
    event_type: str = Field("CheckTestEnvironmentLaunchStatusRequest", alias="eventType")
    recipe_version_id: str = Field(..., alias="recipeVersionId")
    test_execution_id: str = Field(..., alias="testExecutionId")


class CheckTestEnvironmentLaunchStatusResponse(BaseModel):
    event_type: str = Field("CheckTestEnvironmentLaunchStatusResponse", alias="eventType")
    instance_status: str = Field(..., alias="instanceStatus")


class SetupTestEnvironmentRequest(BaseModel):
    event_type: str = Field("SetupTestEnvironmentRequest", alias="eventType")
    recipe_version_id: str = Field(..., alias="recipeVersionId")
    test_execution_id: str = Field(..., alias="testExecutionId")


class SetupTestEnvironmentResponse(BaseModel):
    event_type: str = Field("SetupTestEnvironmentResponse", alias="eventType")


class CheckTestEnvironmentSetupStatusRequest(BaseModel):
    event_type: str = Field("CheckTestEnvironmentSetupStatusRequest", alias="eventType")
    recipe_version_id: str = Field(..., alias="recipeVersionId")
    test_execution_id: str = Field(..., alias="testExecutionId")


class CheckTestEnvironmentSetupStatusResponse(BaseModel):
    event_type: str = Field("CheckTestEnvironmentSetupStatusResponse", alias="eventType")
    setup_command_status: str = Field(..., alias="setupCommandStatus")


class RunRecipeVersionTestRequest(BaseModel):
    event_type: str = Field("RunRecipeVersionTestRequest", alias="eventType")
    recipe_id: str = Field(..., alias="recipeId")
    recipe_version_id: str = Field(..., alias="recipeVersionId")
    test_execution_id: str = Field(..., alias="testExecutionId")


class RunRecipeVersionTestResponse(BaseModel):
    event_type: str = Field("RunRecipeVersionTestResponse", alias="eventType")


class CheckRecipeVersionTestStatusRequest(BaseModel):
    event_type: str = Field("CheckRecipeVersionTestStatusRequest", alias="eventType")
    recipe_version_id: str = Field(..., alias="recipeVersionId")
    test_execution_id: str = Field(..., alias="testExecutionId")


class CheckRecipeVersionTestStatusResponse(BaseModel):
    event_type: str = Field("CheckRecipeVersionTestStatusResponse", alias="eventType")
    test_command_status: str = Field(..., alias="testCommandStatus")


class CompleteRecipeVersionTestRequest(BaseModel):
    event_type: str = Field("CompleteRecipeVersionTestRequest", alias="eventType")
    project_id: str = Field(..., alias="projectId")
    recipe_id: str = Field(..., alias="recipeId")
    recipe_version_id: str = Field(..., alias="recipeVersionId")
    test_execution_id: str = Field(..., alias="testExecutionId")


class CompleteRecipeVersionTestResponse(BaseModel):
    event_type: str = Field("CompleteRecipeVersionTestResponse", alias="eventType")
    recipe_version_test_status: str = Field(..., alias="recipeVersionTestStatus")
