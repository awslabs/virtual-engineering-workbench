export const WORKBENCH_CONNECTION_TYPE = {
  RDP: 'RDPConnect',
  DcvFile: 'DCVFileConnect',
  DcvBrowser: 'DCVBrowserConnect',
  SSH: 'SSH',
  VSCode: 'VSCode',
};

export const SC_PRODUCT_STATES = {
  UnderChange: 'UNDER_CHANGE',
  PlanInProgress: 'PLAN_IN_PROGRESS',
  Available: 'AVAILABLE',
  Tainted: 'TAINTED',
  Error: 'ERROR',
};

export const WORKBENCH_INSTANCE_STATES = {
  Starting: 'Starting',
  Stopping: 'Stopping',
  Stopped: 'Stopped',
  Running: 'Running',
  UnderChange: 'Under change',
  Terminated: 'Terminated',
  InstanceError: 'Instance error',
  ProvisioningError: 'Provisioning error',
  Provisioning: 'Provisioning',
  Deprovisioning: 'Deprovisioning',
  Updating: 'Updating',
};

export const TERMINAL_PRODUCT_SUCCESS_STATUSES = new Set([
  SC_PRODUCT_STATES.Available
]);
export const TERMINAL_PRODUCT_ERROR_STATUSES = new Set([
  SC_PRODUCT_STATES.Tainted,
  SC_PRODUCT_STATES.Error
]);
export const INTERMEDIATE_PRODUCT_STATUSES = new Set([
  SC_PRODUCT_STATES.UnderChange,
  SC_PRODUCT_STATES.PlanInProgress
]);

export const TERMINAL_INSTANCE_SUCCESS_STATUSES = new Set([
  WORKBENCH_INSTANCE_STATES.Running,
  WORKBENCH_INSTANCE_STATES.Terminated,
  WORKBENCH_INSTANCE_STATES.Stopped
]);
export const TERMINAL_INSTANCE_ERROR_STATUSES = new Set([
  WORKBENCH_INSTANCE_STATES.InstanceError,
  WORKBENCH_INSTANCE_STATES.ProvisioningError
]);

export const INTERMEDIATE_WORKBENCH_PROVISIONING_STATUSES = new Set([
  WORKBENCH_INSTANCE_STATES.UnderChange,
  WORKBENCH_INSTANCE_STATES.Provisioning,
  WORKBENCH_INSTANCE_STATES.Deprovisioning,
  WORKBENCH_INSTANCE_STATES.Updating,
]);

export const INTERMEDIATE_WORKBENCH_RUN_STATUSES = new Set([
  WORKBENCH_INSTANCE_STATES.Starting,
  WORKBENCH_INSTANCE_STATES.Stopping,
]);

export const INTERMEDIATE_INSTANCE_STATUSES = new Set([
  ...INTERMEDIATE_WORKBENCH_RUN_STATUSES,
  ...INTERMEDIATE_WORKBENCH_PROVISIONING_STATUSES,
]);
