import { i18n } from './user-preferences.translations';

export type EnabledRegion = 'us-east-1' | 'eu-west-3' | 'ap-south-1' |
'sa-east-1' | 'unspecified' | 'eu-central-1';

export const REGION_NAMES: { [K in EnabledRegion]: string } = {
  'us-east-1': i18n.preferencesRegionNameOption1, // eslint-disable-line
  'eu-west-3': i18n.preferencesRegionNameOption2, // eslint-disable-line
  'eu-central-1': i18n.preferencesRegionNameOption5, // eslint-disable-line
  'ap-south-1': i18n.preferencesRegionNameOption3, // eslint-disable-line
  'sa-east-1': i18n.preferencesRegionNameOption4, // eslint-disable-line
  'unspecified': i18n.preferencesRegionNameOptionUndefined, // eslint-disable-line
};

export const REGION_DESCRIPTIONS: { [K in EnabledRegion]: string } = {
  'us-east-1': i18n.preferencesRegionDescriptionOption1, // eslint-disable-line
  'eu-west-3': i18n.preferencesRegionDescriptionOption2, // eslint-disable-line
  'eu-central-1': i18n.preferencesRegionDescriptionOption5, // eslint-disable-line
  'ap-south-1': i18n.preferencesRegionDescriptionOption3, // eslint-disable-line
  'sa-east-1': i18n.preferencesRegionNameOption4, // eslint-disable-line
  unspecified: '',
};

export const STAGES: { [key: string]: string } = {
  'DEV': i18n.preferencesStageNameOption1, // eslint-disable-line
  'QA': i18n.preferencesStageNameOption2, // eslint-disable-line
  'PROD': i18n.preferencesStageNameOption3, // eslint-disable-line
};
