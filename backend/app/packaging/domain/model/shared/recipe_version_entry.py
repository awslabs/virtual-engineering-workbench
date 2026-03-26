from pydantic import BaseModel, Field


class RecipeVersionEntry(BaseModel):
    recipeId: str = Field(..., title="RecipeId")
    recipeName: str = Field(..., title="RecipeName")
    recipeVersionId: str = Field(..., title="RecipeVersionId")
    recipeVersionName: str = Field(..., title="RecipeVersionName")
