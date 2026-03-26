import {
  ColumnLayout,
  FormField,
  Header,
  Icon,
  RadioGroup,
  RadioGroupProps,
  SpaceBetween,
  Toggle
} from '@cloudscape-design/components';
import { i18n } from './user-preferences.translations';
import { FC } from 'react';
import { useLocalStorage } from '../../hooks';
import { applyMode, Mode } from '@cloudscape-design/global-styles';
import { THEME } from '../../constants';

type Props = {
  preferredRegion: string,
  enabledRegions: RadioGroupProps.RadioButtonDefinition[],
  setPreferredRegion: (value: string) => void,
  preferredNetwork: string,
  enabledNetworks: RadioGroupProps.RadioButtonDefinition[],
  setPreferredNetwork: (value: string) => void,
};

const UserPreferenceRadioInput = (
  {
    value,
    items,
    onChange,
    label
  }:
  {
    value: string,
    items: RadioGroupProps.RadioButtonDefinition[],
    onChange: (s: string) => void,
    label: string,
  }) => {
  return <FormField label={label}>
    <RadioGroup
      onChange={({ detail }) => onChange(detail.value)}
      value={value}
      items={items} />
  </FormField>;
};

export const UserPreferencesGeneral: FC<Props> = ({
  preferredRegion,
  enabledRegions,
  setPreferredRegion,
  preferredNetwork,
  enabledNetworks,
  setPreferredNetwork
}) => {
  const [checked, setChecked] = useLocalStorage(THEME);
  return (
    <>
      <SpaceBetween direction='vertical' size='l'>
        <Header description={i18n.tabDescriptionGeneral} variant='h3'>
          {i18n.tabHeadingGeneral}
        </Header>
        <SpaceBetween size='m'>
          <Toggle
            onChange={({ detail }) => {
              const theme = detail.checked ? 'dark' : 'light';
              setChecked(theme);
              applyMode(theme as Mode);
            }
            }
            checked={checked === 'dark'}
          >
            <SpaceBetween size='xxs' direction='horizontal'>
              <Icon svg={
                <svg xmlns="http://www.w3.org/2000/svg">
                  <path
                    /* eslint @stylistic/max-len: "off" */
                    d="M12.8166 9.79921C12.8417 9.75608 12.7942 9.70771 12.7497 9.73041C11.9008 10.164 10.9392 10.4085 9.92054 10.4085C6.48046 10.4085 3.69172 7.61979 3.69172 4.17971C3.69172 3.16099 3.93628 2.19938 4.36989 1.3504C4.39259 1.30596 4.34423 1.25842 4.3011 1.28351C2.44675 2.36242 1.2002 4.37123 1.2002 6.67119C1.2002 10.1113 3.98893 12.9 7.42901 12.9C9.72893 12.9 11.7377 11.6535 12.8166 9.79921Z"
                    fill="white"
                    stroke="white"
                    strokeWidth="2"
                    className="filled"
                  />
                </svg>} />
              <span>{i18n.darkModeToggleButtonLabel}</span>
            </SpaceBetween>
          </Toggle>
          <ColumnLayout columns={2} variant="text-grid">
            <SpaceBetween size='l'>
              <UserPreferenceRadioInput
                value={preferredRegion}
                items={enabledRegions}
                onChange={setPreferredRegion}
                label={i18n.preferenceRegionTitle}
              />
            </SpaceBetween>
            <SpaceBetween size='l'>
              <UserPreferenceRadioInput
                value={preferredNetwork}
                items={enabledNetworks}
                onChange={setPreferredNetwork}
                label={i18n.preferenceNetworkTitle}
              />
            </SpaceBetween>
          </ColumnLayout>
        </SpaceBetween>
      </SpaceBetween>
    </>
  );
};