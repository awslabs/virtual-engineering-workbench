import { SelectProps } from '@cloudscape-design/components';

export const COMPONENT_VERSION_ENTRY_TYPE_TRANSLATIONS: { [key: string]: string } = {
  MAIN: 'Main',
  HELPER: 'Helper',
};

export const COMPONENT_VERSION_ENTRY_TYPES: SelectProps.Option[] = [
  { label: COMPONENT_VERSION_ENTRY_TYPE_TRANSLATIONS.MAIN, value: 'MAIN' },
  { label: COMPONENT_VERSION_ENTRY_TYPE_TRANSLATIONS.HELPER, value: 'HELPER' },
];