/* eslint-disable */

import {
  Container,
  Form,
  FormField,
  Header,
  Input,
  RadioGroup,
  SpaceBetween,
  Textarea
} from '@cloudscape-design/components';
import { FC } from 'react';
import { i18n } from './component-version-wizard.translations';
import { COMPONENT_VERSION_RELEASE_TYPE_MAP } from '../component-version-release-type-map';
import { isNullOrEmpty } from '../../../../../../utils/form-validation-helper';

function isUrl(url: string) {
  try {
    const parsed_url = new URL(url);
    return parsed_url.protocol === 'http:' || parsed_url.protocol === 'https:';
  } catch (e) {
    return false;
  }
}

export interface ComponentVersionWizardStep1Props{
  isUpdate: boolean,
  description: string,
  setDescription: (description: string) => void,
  isDescriptionValid: boolean,
  versionReleaseTypes: string[],
  versionReleaseType: string,
  setVersionReleaseType: (versionReleaseType: string) => void,
  isVersionReleaseTypeValid: boolean,
  softwareVendor: string,
  setSoftwareVendor: (softwareVendor: string) => void,
  isSoftwareVendorValid: boolean,
  softwareVersion: string,
  setSoftwareVersion: (softwareVersion: string) => void,
  isSoftwareVersionValid: boolean,
  licenseDashboard: string,
  setLicenseDashboard: (licenseDashboard: string) => void,
  isLicenseDashboardValid: boolean,
  notes: string,
  setNotes: (notes: string) => void,
}

export const ComponentVersionWizardStep1: FC<ComponentVersionWizardStep1Props> = ({
  isUpdate,
  description,
  setDescription,
  isDescriptionValid,
  versionReleaseTypes,
  versionReleaseType,
  setVersionReleaseType,
  isVersionReleaseTypeValid,
  softwareVendor,
  setSoftwareVendor,
  isSoftwareVendorValid,
  softwareVersion,
  setSoftwareVersion,
  isSoftwareVersionValid,
  licenseDashboard,
  setLicenseDashboard,
  isLicenseDashboardValid,
  notes,
  setNotes,
}) => {
  function getReleaseTypeOption(prodType: string) {
    return {
      label: COMPONENT_VERSION_RELEASE_TYPE_MAP[prodType],
      value: prodType
    };
  }

  function getDescriptionError() {
    return !isDescriptionValid && isNullOrEmpty(description) ? i18n.step1InputDescriptionError : '';
  }

  function getReleaseTypeError() {
    return !isVersionReleaseTypeValid && isNullOrEmpty(versionReleaseType) ? i18n.step1InputReleaseTypeError : '';
  }

  function getSoftwareVendorError() {
    return !isSoftwareVendorValid && isNullOrEmpty(softwareVendor) ? i18n.step1InputSoftwareVendorError : '';
  }

  function getSoftwareVersionError() {
    return !isSoftwareVersionValid && isNullOrEmpty(softwareVersion)
      ? i18n.step1InputSoftwareVersionError
      : '';
  }

  function getLicenseDashboardError() {
    return !isLicenseDashboardValid && !isUrl(licenseDashboard) 
      ? i18n.step1InputLicenseDashboardError
      : '';
  }

  return <Container
    header={<Header variant="h2">
      {i18n.step1Header}
    </Header>}
  >
    <Form>
      <SpaceBetween direction="vertical" size="l">
        <FormField
          label={i18n.step1InputDescription}
          errorText={ getDescriptionError() }
        >
          <Input
            value={description}
            onChange={({ detail: { value } }) => setDescription(value)}
            placeholder={i18n.step1InputDescriptionPlaceholder}
            data-test="component-version-description"
          />
        </FormField>
        <FormField
          label={i18n.step1InputSoftwareVendor}
          errorText={ getSoftwareVendorError() }
        >
          <Input
            value={softwareVendor}
            onChange={({ detail: { value } }) => setSoftwareVendor(value)}
            placeholder={i18n.step1InputSoftwareVendorPlaceholder}
            data-test="component-version-software-vendor"
          />
        </FormField>
        <FormField
          label={i18n.step1InputSoftwareVersion}
          errorText={ getSoftwareVersionError() }
        >
          <Input
            value={softwareVersion}
            onChange={({ detail: { value } }) => setSoftwareVersion(value)}
            placeholder={i18n.step1InputSoftwareVersionPlaceholder}
            data-test="component-version-software-version"
          />
        </FormField>
        <FormField
          label={i18n.step1InputLicenseDashboard}
          errorText={ getLicenseDashboardError() }
        >
          <Input
            value={licenseDashboard}
            onChange={({ detail: { value } }) => setLicenseDashboard(value)}
            placeholder={i18n.step1InputLicenseDashboardPlaceholder}
            data-test="component-version-license-dashboard"
          />
        </FormField>
        <FormField
          label={i18n.step1InputNotes}
        >
          <Textarea
            value={notes}
            onChange={({ detail: { value } }) => setNotes(value)}
            placeholder={i18n.step1InputNotesPlaceholder}
            data-test="component-version-notes"
            rows={2}
          />
        </FormField>
        {!isUpdate &&
          <FormField
            label={i18n.step1InputReleaseType}
            errorText={ getReleaseTypeError() }
          >
            <RadioGroup
              onChange={({ detail }) => setVersionReleaseType ? setVersionReleaseType(detail.value) : null}
              value={versionReleaseType ? versionReleaseType : ''}
              items={versionReleaseTypes.map(getReleaseTypeOption)}
              data-test="component-version-release-type"
            />
          </FormField>}
      </SpaceBetween>
    </Form>
  </Container>;
};