export type PipelineState = 'CREATING' | 'CREATED' | 'FAILED' | 'UPDATING' | 'RETIRED';

export const PIPELINE_STATES_FOR_UPDATE: Set<PipelineState> =
  new Set(['CREATED', 'FAILED']);
export const PIPELINE_STATES_FOR_RETIRE: Set<PipelineState> =
  new Set(['CREATED', 'FAILED']);
export const PIPELINE_STATES_FOR_CREATE_IMAGE: Set<PipelineState> =
  new Set(['CREATED']);
export const PIPELINE_STATES_FOR_ANY_ACTION: Set<PipelineState> =
  new Set(['CREATED', 'FAILED']);