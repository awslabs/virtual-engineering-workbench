import { StatusIndicator, StatusIndicatorProps } from '@cloudscape-design/components';
import { PipelineState } from './pipeline-status.static';

export const STATUS_MAP: { [K in PipelineState]: string } = {
  CREATING: 'Creating',
  CREATED: 'Created',
  FAILED: 'Failed',
  UPDATING: 'Updating',
  RETIRED: 'Retired',
};

export const STATUS_COLOR_MAP: { [K in PipelineState]: StatusIndicatorProps.Type } = {
  CREATING: 'pending',
  CREATED: 'success',
  FAILED: 'error',
  UPDATING: 'pending',
  RETIRED: 'stopped',
};

export const PipelineStatus = ({ status }: { status: string }) => {
  return <StatusIndicator
    type={STATUS_COLOR_MAP[status as PipelineState]}
  >
    {STATUS_MAP[status as PipelineState]}
  </StatusIndicator>;
};