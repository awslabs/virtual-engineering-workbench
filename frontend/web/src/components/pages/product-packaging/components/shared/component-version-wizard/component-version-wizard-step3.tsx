import { Container, Header } from '@cloudscape-design/components';
import { FC } from 'react';
import { i18n } from './component-version-wizard.translations';
import {
  Component,
  ComponentVersionEntry,
  RecipeComponentVersion,
} from '../../../../../../services/API/proserve-wb-packaging-api';
import { ComponentVersionEntriesInput } from '../../../shared';

export interface ComponentVersionWizardStep3Props {
  projectId: string,
  component: Component,
  componentVersionDependencies: ComponentVersionEntry[],
  setComponentVersionDependencies: (componentVersionDependencies: ComponentVersionEntry[]) => void,
  isComponentVersionDependenciesValid: boolean,
  minComponentVersionDependencies: number,
  recipeMandatoriesComponentsVersions: RecipeComponentVersion[],
}

const COMPONENT_VERSION_STATUSES = ['VALIDATED', 'RELEASED'];

export const ComponentVersionWizardStep3: FC<ComponentVersionWizardStep3Props> = ({
  projectId,
  component,
  componentVersionDependencies,
  setComponentVersionDependencies,
  isComponentVersionDependenciesValid,
  minComponentVersionDependencies,
  recipeMandatoriesComponentsVersions,
}) => {
  return (
    <Container header={<Header variant="h2">{i18n.step3Header}</Header>}>
      <ComponentVersionEntriesInput
        projectId={projectId}
        platform={component.componentPlatform}
        osVersion={component.componentSupportedOsVersions[0] || ''}
        architecture={component.componentSupportedArchitectures[0] || ''}
        componentVersionEntries={componentVersionDependencies}
        setComponentVersionEntries={setComponentVersionDependencies}
        isComponentVersionsEntriesValid={isComponentVersionDependenciesValid}
        minComponentVersionEntries={minComponentVersionDependencies}
        excludedComponents={[component.componentId]} // this is to prevent cyclic dependencies of components
        componentVersionStatuses={COMPONENT_VERSION_STATUSES}
        componentVersionView={recipeMandatoriesComponentsVersions}
      />
    </Container>
  );
};