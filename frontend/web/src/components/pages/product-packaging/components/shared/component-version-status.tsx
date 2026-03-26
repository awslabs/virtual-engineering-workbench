import { StatusIndicator, StatusIndicatorProps } from '@cloudscape-design/components';
import { ComponentVersionState } from '.';

export const COMPONENT_VERSION_STATUS_MAP: { [K in ComponentVersionState]: string } = {
  CREATING: 'Creating',
  CREATED: 'Created',
  FAILED: 'Failed',
  RELEASED: 'Released',
  TESTING: 'Testing',
  UPDATING: 'Updating',
  VALIDATED: 'Validated',
  RETIRED: 'Retired',
};

export const COMPONENT_VERSION_STATUS_COLOR_MAP: {
  [K in ComponentVersionState]: StatusIndicatorProps.Type
} = {
  CREATING: 'pending',
  CREATED: 'success',
  FAILED: 'error',
  RELEASED: 'success',
  TESTING: 'in-progress',
  UPDATING: 'pending',
  VALIDATED: 'success',
  RETIRED: 'stopped',
};

export const ComponentVersionStatus = ({ status }: { status: string }) => {
  return <StatusIndicator
    type={COMPONENT_VERSION_STATUS_COLOR_MAP[status as ComponentVersionState]}
  >
    {COMPONENT_VERSION_STATUS_MAP[status as ComponentVersionState]}
  </StatusIndicator>;
};