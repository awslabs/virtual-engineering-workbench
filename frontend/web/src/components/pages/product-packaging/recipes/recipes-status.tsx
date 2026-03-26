import { StatusIndicator, StatusIndicatorProps } from '@cloudscape-design/components';
import { RecipeState } from './recipe.static';

export const RECIPE_STATUS_MAP: { [K in RecipeState]: string } = {
  ARCHIVED: 'Archived',
  CREATED: 'Created',
};

export const RECIPE_STATUS_COLOR_MAP: { [K in RecipeState]: StatusIndicatorProps.Type } = {
  ARCHIVED: 'stopped',
  CREATED: 'success',
};

export const RecipeStatus = ({ status }: { status: string }) => {
  return <StatusIndicator
    type={RECIPE_STATUS_COLOR_MAP[status as RecipeState]}
  >
    {RECIPE_STATUS_MAP[status as RecipeState]}
  </StatusIndicator>;
};