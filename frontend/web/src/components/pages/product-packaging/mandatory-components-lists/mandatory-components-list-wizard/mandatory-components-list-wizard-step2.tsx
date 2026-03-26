
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

export interface MandatoryComponentsListWizardStep2Props {
  projectId: string,
  mandatoryComponentsListPlatform: string,
  mandatoryComponentsListOsVersion: string,
  mandatoryComponentsListArchitecture: string,
  componentVersionEntries: ComponentVersionEntry[],
  setComponentVersionEntries: (mandatoryComponentsVersions: ComponentVersionEntry[]) => void,
  isComponentsVersionEntriesValid: boolean,
  isMainComponentPresent: boolean,
  minComponentVersionEntries: number,
}

export const MandatoryComponentsListWizardStep2: FC<MandatoryComponentsListWizardStep2Props> = ({
  projectId,
  mandatoryComponentsListPlatform,
  mandatoryComponentsListOsVersion,
  mandatoryComponentsListArchitecture,
  componentVersionEntries,
  setComponentVersionEntries,
  isComponentsVersionEntriesValid,
  isMainComponentPresent,
  minComponentVersionEntries
}) => {
  return (
    <Container header={<Header variant="h2">{i18n.step2Header}</Header>}>
      <SpaceBetween size='xs'>
        <ComponentVersionEntriesInput
          projectId={projectId}
          platform={mandatoryComponentsListPlatform}
          osVersion={mandatoryComponentsListOsVersion}
          architecture={mandatoryComponentsListArchitecture}
          componentVersionEntries={componentVersionEntries}
          setComponentVersionEntries={(entries) =>
            setComponentVersionEntries(entries as ComponentVersionEntry[])
          }
          isComponentVersionsEntriesValid={isComponentsVersionEntriesValid}
          minComponentVersionEntries={minComponentVersionEntries}
          componentVersionView={componentVersionEntries}
        />
        {!isMainComponentPresent && <Alert
          type='error'
          header={i18n.step2MainComponentError}
        >
          {i18n.step2MainComponentErrorDescription}
        </Alert>}
      </SpaceBetween>
    </Container>
  );
};
