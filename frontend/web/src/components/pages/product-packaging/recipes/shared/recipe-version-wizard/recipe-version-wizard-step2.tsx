
import {
  Container,
  Header,
  SpaceBetween,
  Alert,
} from '@cloudscape-design/components';
import { FC } from 'react';
import { i18n, i18nStep2 } from './recipe-version-wizard.translations';
import {
  Recipe,
  RecipeComponentVersion,
  ComponentVersionEntry
} from '../../../../../../services/API/proserve-wb-packaging-api';
import { ComponentVersionEntriesInput } from '../../../shared';
import { useParams } from 'react-router-dom';


export interface RecipeVersionWizardStep2Props {
  projectId: string,
  recipe: Recipe,
  recipeComponentsVersions: RecipeComponentVersion[],
  setRecipeComponentsVersions: (recipeComponentsVersions: RecipeComponentVersion[]) => void,
  isRecipeComponentsVersionsValid: boolean,
  minRecipeComponentsVersions: number,
  recipeMandatoriesComponentsVersions: ComponentVersionEntry[],
  integrationComponentsVersions?: ComponentVersionEntry[],
}

const COMPONENT_VERSION_STATUSES = ['VALIDATED', 'RELEASED'];

export const RecipeVersionWizardStep2: FC<RecipeVersionWizardStep2Props> = ({
  projectId,
  recipe,
  recipeComponentsVersions,
  setRecipeComponentsVersions,
  isRecipeComponentsVersionsValid,
  minRecipeComponentsVersions,
  recipeMandatoriesComponentsVersions,
  integrationComponentsVersions = []
}) => {
  const { versionId } = useParams();
  const isCreation = !versionId;
  const OFFSET = 1;

  const mandatoryComponentsLength = recipeMandatoriesComponentsVersions.length;
  const integrationComponentsWithPosition = integrationComponentsVersions.map((comp, index) => ({
    ...comp,
    position: 'PREPEND' as const,
    order: mandatoryComponentsLength + index + OFFSET,
    isIntegrationComponent: true
  }));

  return (
    <Container header={<Header variant="h2">{i18n.step2Header}</Header>}>
      <SpaceBetween size='xs'>
        <Alert type="info">
          <span style={{ whiteSpace: 'pre-line' }}>{i18nStep2(isCreation).recipeVersionInfo}</span>
        </Alert>
        <ComponentVersionEntriesInput
          projectId={projectId}
          platform={recipe.recipePlatform}
          osVersion={recipe.recipeOsVersion}
          architecture={recipe.recipeArchitecture}
          componentVersionEntries={recipeComponentsVersions}
          setComponentVersionEntries={(entries) =>
            setRecipeComponentsVersions(entries as RecipeComponentVersion[])
          }
          isComponentVersionsEntriesValid={isRecipeComponentsVersionsValid}
          typeSelectionEnabled
          minComponentVersionEntries={minRecipeComponentsVersions}
          componentVersionStatuses={COMPONENT_VERSION_STATUSES}
          componentVersionView={[
            ...recipeMandatoriesComponentsVersions,
            ...integrationComponentsWithPosition
          ]}
        />
      </SpaceBetween>
    </Container>
  );
};
