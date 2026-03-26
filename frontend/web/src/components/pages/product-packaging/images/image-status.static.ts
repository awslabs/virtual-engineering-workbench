export type ImageState = 'CREATING' | 'CREATED' | 'FAILED' | 'RETIRED';

export const IMAGE_STATES_FOR_UPDATE: Set<ImageState> =
  new Set(['CREATED', 'FAILED']);
export const IMAGE_STATES_FOR_RETIRE: Set<ImageState> =
  new Set(['CREATED', 'FAILED']);