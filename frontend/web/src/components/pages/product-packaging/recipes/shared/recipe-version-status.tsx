import { StatusIndicator, StatusIndicatorProps } from '@cloudscape-design/components';
import { RecipeVersionState } from './recipe-version.static';

export const VERSION_STATUS_MAP: { [K in RecipeVersionState]: string } = {
  CREATING: 'Creating',
  CREATED: 'Created',
  FAILED: 'Failed',
  RELEASED: 'Released',
  TESTING: 'Testing',
  UPDATING: 'Updating',
  VALIDATED: 'Validated',
  RETIRED: 'Retired',
};

export const VERSION_STATUS_COLOR_MAP: { [K in RecipeVersionState]: StatusIndicatorProps.Type } = {
  CREATING: 'pending',
  CREATED: 'success',
  FAILED: 'error',
  RELEASED: 'success',
  TESTING: 'in-progress',
  UPDATING: 'pending',
  VALIDATED: 'success',
  RETIRED: 'stopped',
};

export const RecipeVersionStatus = ({ status }: { status: string }) => {
  return <StatusIndicator
    type={VERSION_STATUS_COLOR_MAP[status as RecipeVersionState]}
  >
    {VERSION_STATUS_MAP[status as RecipeVersionState]}
  </StatusIndicator>;
};