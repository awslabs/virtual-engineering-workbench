
import {
  Alert,
  Container,
  Header,
  SpaceBetween,
} from '@cloudscape-design/components';
import { FC } from 'react';
import { i18n } from './mandatory-components-list-wizard.translations';
import { ComponentVersionEntriesInput } from '../..';
import { ComponentVersionEntry } from '../../../../../services/API/proserve-wb-packaging-api';

export interface MandatoryComponentsListWizardStep2PrependedProps {
  projectId: string,
  mandatoryComponentsListPlatform: string,
  mandatoryComponentsListOsVersion: string,
  mandatoryComponentsListArchitecture: string,
  prependedComponentVersionEntries: ComponentVersionEntry[],
  setPrependedComponentVersionEntries: (components: ComponentVersionEntry[]) => void,
  isPrependedComponentsValid: boolean,
  hasDuplicateComponents: boolean,
}

export const MandatoryComponentsListWizardStep2Prepended: FC<
  MandatoryComponentsListWizardStep2PrependedProps
> = ({
  projectId,
  mandatoryComponentsListPlatform,
  mandatoryComponentsListOsVersion,
  mandatoryComponentsListArchitecture,
  prependedComponentVersionEntries,
  setPrependedComponentVersionEntries,
  isPrependedComponentsValid,
  hasDuplicateComponents,
}) => {
  return (
    <Container header={<Header variant="h2">{i18n.step2Header}</Header>}>
      <SpaceBetween size='m'>
        <div>{i18n.step2Description}</div>
        <ComponentVersionEntriesInput
          projectId={projectId}
          platform={mandatoryComponentsListPlatform}
          osVersion={mandatoryComponentsListOsVersion}
          architecture={mandatoryComponentsListArchitecture}
          componentVersionEntries={prependedComponentVersionEntries}
          setComponentVersionEntries={(entries) =>
            setPrependedComponentVersionEntries(entries as ComponentVersionEntry[])
          }
          isComponentVersionsEntriesValid={isPrependedComponentsValid}
          minComponentVersionEntries={0}
        />
        {hasDuplicateComponents && <Alert
          type='error'
          header={i18n.duplicateComponentError}
        >
          {i18n.duplicateComponentErrorDescription}
        </Alert>}
      </SpaceBetween>
    </Container>
  );
};
