import { StatusIndicator, StatusIndicatorProps } from '@cloudscape-design/components';
import { ImageState } from './image-status.static';

export const STATUS_MAP: { [K in ImageState]: string } = {
  CREATING: 'Creating',
  CREATED: 'Created',
  FAILED: 'Failed',
  RETIRED: 'Retired',
};

export const STATUS_COLOR_MAP: { [K in ImageState]: StatusIndicatorProps.Type } = {
  CREATING: 'pending',
  CREATED: 'success',
  FAILED: 'error',
  RETIRED: 'stopped',
};

export const ImageStatus = ({ status }: { status: string }) => {
  return <StatusIndicator
    type={STATUS_COLOR_MAP[status as ImageState]}
  >
    {STATUS_MAP[status as ImageState]}
  </StatusIndicator>;
};