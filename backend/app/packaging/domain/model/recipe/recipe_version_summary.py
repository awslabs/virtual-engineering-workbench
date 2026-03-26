from pydantic import BaseModel, Field


class RecipeVersionSummary(BaseModel):
    recipeId: str = Field(..., title="RecipeId")
    recipeVersionId: str = Field(..., title="RecipeVersionId")
    recipeVersionName: str = Field(..., title="RecipeVersionName")
    recipeName: str = Field(..., title="RecipeName")
