
import {
  Container,
  Form,
  FormField,
  Header,
  RadioGroup,
  SpaceBetween,
  Select,
  SelectProps
} from '@cloudscape-design/components';
import { FC } from 'react';
import { i18n } from './mandatory-components-list-wizard.translations';

export interface MandatoryComponentsListWizardStep1Props {
  mandatoryComponentsListPlatform: string,
  setMandatoryComponentsListPlatform: (platform: string) => void,
  mandatoryComponentsListOsVersion: SelectProps.Option,
  setMandatoryComponentsListOsVersion: (osVersion: SelectProps.Option) => void,
  mandatoryComponentsListArchitecture: SelectProps.Option,
  setMandatoryComponentsListArchitecture: (architecture: SelectProps.Option) => void,
  availableMandatoryComponentSupportedArchitectures: SelectProps.Option[],
  availableMandatoryComponentSupportedOsVersions: SelectProps.Option[],
  isSupportedArchitectureValid: () => boolean,
  isSupportedOsVersionValid: () => boolean,
  isPlatformValid: () => boolean,
  isSubmitted: boolean,
  isUpdate: boolean,
}

export const MandatoryComponentsListWizardStep1: FC<MandatoryComponentsListWizardStep1Props> = ({
  mandatoryComponentsListPlatform,
  setMandatoryComponentsListPlatform,
  mandatoryComponentsListOsVersion,
  setMandatoryComponentsListOsVersion,
  mandatoryComponentsListArchitecture,
  setMandatoryComponentsListArchitecture,
  availableMandatoryComponentSupportedArchitectures,
  availableMandatoryComponentSupportedOsVersions,
  isSupportedArchitectureValid,
  isSupportedOsVersionValid,
  isPlatformValid,
  isSubmitted,
}) => {


  function getArchitectureError() {
    return isSubmitted && !isSupportedArchitectureValid() ? i18n.supportedArchitectureValidationMessage : '';
  }

  function getOsVersionError() {
    return isSubmitted && !isSupportedOsVersionValid() ? i18n.supportedOsVersionValidationMessage : '';
  }

  function getPlatformError() {
    return isSubmitted && !isPlatformValid() ? i18n.platformValidationMessage : '';
  }

  return <Container
    header={<Header variant="h2">
      {i18n.step1Header}
    </Header>}
  >
    <Form data-test="create-mandatory-components-list-step-1-form">
      <SpaceBetween direction='vertical' size='l'>
        <FormField
          label={i18n.platformLabel}
          errorText={getPlatformError()}
        >
          <RadioGroup
            onChange={({ detail }) => {
              setMandatoryComponentsListPlatform(detail.value);
              setMandatoryComponentsListOsVersion(undefined!);
              setMandatoryComponentsListArchitecture(undefined!);
            }}
            value={mandatoryComponentsListPlatform}
            items={[
              {
                value: 'Windows',
                label: i18n.platformWindowsLabel,
                description: i18n.platformWindowsDescription
              },
              {
                value: 'Linux',
                label: i18n.platformLinuxLabel,
                description: i18n.platformLinuxDescription
              },
            ]}
            data-test="create-mandatory-components-list-platform-radio"
          />
        </FormField>
        <FormField
          label={i18n.supportedArchitectureLabel}
          errorText={getArchitectureError()}>

          <Select
            placeholder={i18n.supportedArchitecturePlaceholder}
            options={availableMandatoryComponentSupportedArchitectures}
            selectedOption={mandatoryComponentsListArchitecture}
            onChange={({ detail }) => setMandatoryComponentsListArchitecture(detail.selectedOption)}
            data-test="create-mandatory-components-list-architectures-select"
          />
        </FormField>
        <FormField
          label={i18n.supportedOsVersionLabel}
          errorText={getOsVersionError()}>
          <Select
            placeholder={i18n.supportedOsVersionPlaceholder}
            options={availableMandatoryComponentSupportedOsVersions}
            selectedOption={mandatoryComponentsListOsVersion}
            onChange={({ detail }) => setMandatoryComponentsListOsVersion(detail.selectedOption)}
            data-test="create-mandatory-components-list-os-versions-select"
          />
        </FormField>
      </SpaceBetween>
    </Form>
  </Container>;
};