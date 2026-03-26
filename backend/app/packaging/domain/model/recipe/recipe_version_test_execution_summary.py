from pydantic import BaseModel, Field

from app.packaging.domain.model.recipe import recipe_version_test_execution


class RecipeVersionTestExecutionSummary(BaseModel):
    recipeVersionId: str = Field(..., title="RecipeVersionId")
    instanceArchitecture: str = Field(..., title="InstanceArchitecture")
    instanceImageUpstreamId: str = Field(..., title="InstanceImageId")
    instanceOsVersion: str = Field(..., title="InstanceOsVersion")
    instancePlatform: str = Field(..., title="InstancePlatform")
    status: recipe_version_test_execution.RecipeVersionTestExecutionStatus = Field(..., title="Status")
    testExecutionId: str = Field(..., title="TestExecutionId")
    instanceId: str = Field(..., title="InstanceId")
    createDate: str = Field(..., title="CreateDate")
    lastUpdateDate: str = Field(..., title="LastUpdateDate")
