import { StatusIndicator, StatusIndicatorProps } from '@cloudscape-design/components';

export const TESTS_STATUS_MAP: { [key: string]: string } = {
  PENDING: 'Pending',
  RUNNING: 'Running',
  FAILED: 'Failed',
  SUCCESS: 'Success',
};

export const TESTS_STATUS_COLOR_MAP: { [key: string]: StatusIndicatorProps.Type } = {
  PENDING: 'pending',
  RUNNING: 'pending',
  FAILED: 'error',
  SUCCESS: 'success',
};

export const TestExecutionStatus = ({ status }: { status: string }) => {
  return <StatusIndicator
    type={TESTS_STATUS_COLOR_MAP[status]}
  >
    {TESTS_STATUS_MAP[status]}
  </StatusIndicator>;
};