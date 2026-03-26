export type VersionSummaryStatus = 'CREATED' | 'FAILED' | 'RETIRED' | 'PROCESSING';

export type VersionStatus = 'CREATING' | 'CREATED' | 'FAILED' |
'RETIRING' | 'RETIRED' | 'RESTORING' | 'UPDATING';

export type VersionStage = 'DEV' | 'QA' | 'PROD';

export type VersionType = 'RELEASE_CANDIDATE' | 'RELEASED' | 'RESTORED';
