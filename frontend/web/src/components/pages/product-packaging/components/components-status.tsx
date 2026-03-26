import { StatusIndicator, StatusIndicatorProps } from '@cloudscape-design/components';
import { ComponentState } from './components.static';

export const COMPONENT_STATUS_MAP: { [K in ComponentState]: string } = {
  ARCHIVED: 'Archived',
  CREATED: 'Created',
};

export const COMPONENT_STATUS_COLOR_MAP: { [K in ComponentState]: StatusIndicatorProps.Type } = {
  ARCHIVED: 'stopped',
  CREATED: 'success',
};

export const ComponentStatus = ({ status }: { status: string }) => {
  return <StatusIndicator
    type={COMPONENT_STATUS_COLOR_MAP[status as ComponentState]}
  >
    {COMPONENT_STATUS_MAP[status as ComponentState]}
  </StatusIndicator>;
};