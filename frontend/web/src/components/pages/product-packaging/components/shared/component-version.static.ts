export type ComponentVersionState = 'CREATING' | 'CREATED' | 'FAILED' | 'RELEASED'
| 'TESTING' | 'UPDATING' | 'VALIDATED' | 'RETIRED';

export const COMPONENT_VERSION_STATES_FOR_UPDATE: Set<ComponentVersionState> =
  new Set(['CREATED', 'FAILED', 'VALIDATED']);
export const COMPONENT_VERSION_STATES_FOR_RELEASE: Set<ComponentVersionState> =
  new Set(['VALIDATED']);
export const COMPONENT_VERSION_STATES_FOR_FORCE_RELEASE: Set<ComponentVersionState> =
  new Set(['FAILED', 'VALIDATED']);
export const COMPONENT_VERSION_STATES_FOR_RETIRE: Set<ComponentVersionState> =
  new Set(['RELEASED', 'FAILED', 'VALIDATED']);