
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

export interface MandatoryComponentsListWizardStep3AppendedProps {
  projectId: string,
  mandatoryComponentsListPlatform: string,
  mandatoryComponentsListOsVersion: string,
  mandatoryComponentsListArchitecture: string,
  appendedComponentVersionEntries: ComponentVersionEntry[],
  setAppendedComponentVersionEntries: (components: ComponentVersionEntry[]) => void,
  isAppendedComponentsValid: boolean,
  hasDuplicateComponents: boolean,
}

export const MandatoryComponentsListWizardStep3Appended: FC<
  MandatoryComponentsListWizardStep3AppendedProps
> = ({
  projectId,
  mandatoryComponentsListPlatform,
  mandatoryComponentsListOsVersion,
  mandatoryComponentsListArchitecture,
  appendedComponentVersionEntries,
  setAppendedComponentVersionEntries,
  isAppendedComponentsValid,
  hasDuplicateComponents,
}) => {
  return (
    <Container header={<Header variant="h2">{i18n.step3Header}</Header>}>
      <SpaceBetween size='m'>
        <div>{i18n.step3Description}</div>
        <ComponentVersionEntriesInput
          projectId={projectId}
          platform={mandatoryComponentsListPlatform}
          osVersion={mandatoryComponentsListOsVersion}
          architecture={mandatoryComponentsListArchitecture}
          componentVersionEntries={appendedComponentVersionEntries}
          setComponentVersionEntries={(entries) =>
            setAppendedComponentVersionEntries(entries as ComponentVersionEntry[])
          }
          isComponentVersionsEntriesValid={isAppendedComponentsValid}
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
