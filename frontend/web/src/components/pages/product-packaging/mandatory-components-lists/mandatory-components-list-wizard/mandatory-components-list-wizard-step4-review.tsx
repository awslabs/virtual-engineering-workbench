import { Alert, Button, ColumnLayout, Container, Header, SpaceBetween } from '@cloudscape-design/components';
import { FC } from 'react';
import { i18n } from './mandatory-components-list-wizard.translations';
import { ComponentVersionEntriesView } from '../..';
import { ValueWithLabel } from '../../../shared/value-with-label';
import { ComponentVersionEntry } from '../../../../../services/API/proserve-wb-packaging-api';

export interface MandatoryComponentsListWizardStep4ReviewProps {
  mandatoryComponentsListPlatform: string,
  mandatoryComponentsListOsVersion: string,
  mandatoryComponentsListArchitecture: string,
  prependedComponentVersionEntries: ComponentVersionEntry[],
  appendedComponentVersionEntries: ComponentVersionEntry[],
  setActiveStepIndex: (index: number) => void,
  isUpdate: boolean,
  step1Index: number,
  step2Index: number,
  step3Index: number,
}

const EMPTY_ARRAY_LENGTH = 0;

export const MandatoryComponentsListWizardStep4Review: FC<MandatoryComponentsListWizardStep4ReviewProps> = ({
  mandatoryComponentsListPlatform,
  mandatoryComponentsListOsVersion,
  mandatoryComponentsListArchitecture,
  prependedComponentVersionEntries,
  appendedComponentVersionEntries,
  setActiveStepIndex,
  isUpdate,
  step1Index,
  step2Index,
  step3Index,
}) => {
  const hasNoComponents = prependedComponentVersionEntries.length === EMPTY_ARRAY_LENGTH &&
                          appendedComponentVersionEntries.length === EMPTY_ARRAY_LENGTH;

  return <SpaceBetween direction='vertical' size='l'>
    {!isUpdate && <SpaceBetween direction='vertical' size='xs'>
      <Header
        variant='h3'
        actions={
          // eslint-disable-next-line @typescript-eslint/no-magic-numbers
          <Button onClick={() => setActiveStepIndex(step1Index - 1)}>
            {i18n.step4ButtonEdit}
          </Button>
        }
      >
        {i18n.step4Step1Header}
      </Header>
      <Container
        data-test="mandatory-component-details-container"
        header={<Header variant="h2">
          {i18n.step4DetailsHeader}
        </Header>}
      >
        <ColumnLayout columns={3}>
          <ValueWithLabel
            label={i18n.platformLabel}
            data-test="create-mandatory-components-list-platform">
            {mandatoryComponentsListPlatform}
          </ValueWithLabel>
          <ValueWithLabel
            label={i18n.supportedArchitectureLabel}
            data-test="create-mandatory-components-list-architecture">
            {mandatoryComponentsListArchitecture}
          </ValueWithLabel>
          <ValueWithLabel
            label={i18n.supportedOsVersionLabel}
            data-test="create-mandatory-components-list-os-version">
            {mandatoryComponentsListOsVersion}
          </ValueWithLabel>
        </ColumnLayout>
      </Container>
    </SpaceBetween>}

    {hasNoComponents && <Alert
      type='error'
      header={i18n.noComponentsError}
    >
      {i18n.noComponentsErrorDescription}
    </Alert>}

    <SpaceBetween direction='vertical' size='xs'>
      <Header
        variant='h3'
        actions={
          // eslint-disable-next-line @typescript-eslint/no-magic-numbers
          <Button onClick={() => setActiveStepIndex(step2Index - 1)}>
            {i18n.step4ButtonEdit}
          </Button>
        }
      >
        {i18n.step4Step2Header}
      </Header>
      <ComponentVersionEntriesView
        data-test="prepended-component-version-entries-container"
        componentVersionEntries={prependedComponentVersionEntries}
      />
    </SpaceBetween>

    <SpaceBetween direction='vertical' size='xs'>
      <Header
        variant='h3'
        actions={
          // eslint-disable-next-line @typescript-eslint/no-magic-numbers
          <Button onClick={() => setActiveStepIndex(step3Index - 1)}>
            {i18n.step4ButtonEdit}
          </Button>
        }
      >
        {i18n.step4Step3Header}
      </Header>
      <ComponentVersionEntriesView
        data-test="appended-component-version-entries-container"
        componentVersionEntries={appendedComponentVersionEntries}
      />
    </SpaceBetween>
  </SpaceBetween>;
};
