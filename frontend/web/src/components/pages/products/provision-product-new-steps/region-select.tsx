import { FC } from 'react';
import { FormField, Select } from '@cloudscape-design/components';
import { Step1Version } from './step-1-configure-settings';
import { StepsTranslations } from '../../../../hooks/provisioning/provision-product.logic';

type RegionSelectParams = {
  selectedVersionRegion: string,
  setSelectedVersionRegion?: (region: string) => void,
  disabled: boolean,
  setSelectedVersion?: (version?: Step1Version) => void,
  getRegionLabel: (region: string) => string,
  isRegionEnabled: (region: string) => boolean,
  i18n: StepsTranslations,
  enabledRegions: string[],
};

const regionSelect: FC<RegionSelectParams> = (params: RegionSelectParams) => {
  return <FormField
    label={params.i18n.formFieldRegionHeader}
    description={params.i18n.formFieldRegionDescription}
  >
    <Select
      selectedOption={getRegionOption(params.selectedVersionRegion, false)}
      onChange={({ detail }) => {
        params.setSelectedVersionRegion?.(detail.selectedOption.value ?? '');
        params.setSelectedVersion?.();
      }}
      options={params.enabledRegions!.map(region => getRegionOption(region, !params.isRegionEnabled(region)))}
      data-test="select-region"
      disabled={params.disabled}
    />
  </FormField>;

  function getRegionOption(region: string, disabled: boolean) {
    return {
      label: params.getRegionLabel(region),
      value: region,
      disabled: disabled,
    };
  }
};

export { regionSelect as RegionSelect };