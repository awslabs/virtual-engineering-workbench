export type RecipeVersionState = 'CREATING' | 'CREATED' | 'FAILED' | 'RELEASED'
| 'TESTING' | 'UPDATING' | 'VALIDATED' | 'RETIRED';

export const RECIPE_VERSION_STATES_FOR_UPDATE: Set<RecipeVersionState> =
  new Set(['CREATED', 'FAILED', 'VALIDATED']);
export const RECIPE_VERSION_STATES_FOR_RELEASE: Set<RecipeVersionState> =
  new Set(['VALIDATED']);
export const RECIPE_VERSION_STATES_FOR_FORCE_RELEASE: Set<RecipeVersionState> =
  new Set(['FAILED', 'VALIDATED']);
export const RECIPE_VERSION_STATES_FOR_RESTORE: Set<RecipeVersionState> =
  new Set(['RETIRED']);
export const RECIPE_VERSION_STATES_FOR_RETIRE: Set<RecipeVersionState> =
  new Set(['RELEASED', 'FAILED', 'VALIDATED']);