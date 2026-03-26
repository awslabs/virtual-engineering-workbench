import { atomFamily } from 'recoil';

export interface OutputParameter {
  outputKey: string,
  outputValue: string,
  description?: string,
  outputType?: string,
}

export const workbenchOutputParameters = atomFamily<OutputParameter[], string>({
  key: 'workbench-output-parameters-state',
  default: [],
});

export const workbenchOutputParametersLoading = atomFamily<boolean, string>({
  key: 'workbench-output-parameters-state-loading',
  default: false,
});

export const workbenchOutputParametersLoaded = atomFamily<boolean, string>({
  key: 'workbench-output-parameters-state-loaded',
  default: false,
});
