import React, { useState } from 'react';
import { RouteNames } from '../../../../layout/navigation/navigation.static';
import { WorkbenchAppLayout } from '../../../../layout/workbench-app-layout/workbench-app-layout';
import { i18n } from './create-recipe-version.translations';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic';
import { useParams } from 'react-router-dom';
import { Box, HelpPanel, SpaceBetween, Spinner } from '@cloudscape-design/components';
import { RecipeVersionWizard } from '../shared';
import { selectedProjectState } from '../../../../../state';
import { useRecoilValue } from 'recoil';
import { useCreateRecipeVersion } from './create-recipe-version.logic';

const EMPTY_ARRAY_LENGTH = 0;
const STEP_1_INDEX = 0;
const STEP_2_INDEX = 1;
const STEP_3_INDEX = 2;

export const CreateRecipeVersion: React.FC = () => {
  const { getPathFor, navigateTo } = useNavigationPaths();
  const { recipeId } = useParams();
  const [activeStepIndex, setActiveStepIndex] = useState(EMPTY_ARRAY_LENGTH);
  const selectedProject = useRecoilValue(selectedProjectState);
  const projectId = selectedProject.projectId;

  if (!recipeId) { navigateTo(RouteNames.Recipes); return true; }
  if (!projectId) { navigateTo(RouteNames.Recipes); return true; }


  const {
    createRecipeVersion,
    createRecipeVersionInProgress,
    recipeVersion,
    isRecipeVersionLoading,
    recipeVersionMandatories,
  } = useCreateRecipeVersion({
    recipeId,
    projectId,
  });

  function renderContent() {
    if (isRecipeVersionLoading) {
      return <Spinner size="large" />;
    }

    return <RecipeVersionWizard
      recipeVersion={recipeVersion}
      projectId={projectId || ''}
      recipeId={recipeId || ''}
      wizardCancelAction={() => navigateTo(RouteNames.ViewRecipe, { ':recipeId': recipeId })}
      wizardSubmitAction={createRecipeVersion}
      wizardSubmitInProgress={createRecipeVersionInProgress}
      activeStepIndex={activeStepIndex}
      setActiveStepIndex={setActiveStepIndex}
      recipeVersionMandatories={recipeVersionMandatories}
    />;
  }

  return <WorkbenchAppLayout
    breadcrumbItems={[
      { path: i18n.breadcrumbLevel1, href: getPathFor(RouteNames.Recipes) },
      {
        path: i18n.breadcrumbLevel2,
        href: getPathFor(RouteNames.ViewRecipe, { ':recipeId': recipeId })
      },
      { path: i18n.breadcrumbLevel3, href: '#' },
    ]}
    content={renderContent()}
    contentType="default"
    tools={renderTools()}
  />;

  function renderTools() {
    return <>
      {activeStepIndex === STEP_1_INDEX && renderStep1InfoPanel()}
      {activeStepIndex === STEP_2_INDEX && renderStep2InfoPanel()}
      {activeStepIndex === STEP_3_INDEX && renderStep3InfoPanel()}
    </>;

  }

  function renderStep1InfoPanel() {
    return <HelpPanel header={<h2>{i18n.step1infoPanelHeader}</h2>}><SpaceBetween size={'s'}>
      <Box variant="awsui-key-label">{i18n.step1infoPanelLabel1}</Box>
      <Box variant="p">{i18n.step1infoPanelMessage1}</Box>
      <Box>
        <p>{i18n.step1infoPanelMessage2}</p>
        <ul>
          <li>{i18n.step1infoPanelPoint1}</li>
          <li>{i18n.step1infoPanelPoint2}</li>
          <li>{i18n.step1infoPanelPoint3}</li>
        </ul>
      </Box>
    </SpaceBetween>
    </HelpPanel>;
  }

  function renderStep2InfoPanel() {
    return <HelpPanel header={<h2>{i18n.step2infoPanelHeader}</h2>}><SpaceBetween size={'s'}>
      <Box variant="awsui-key-label">{i18n.step2infoPanelLabel1}</Box>
      <Box variant="p">{i18n.step2infoPanelMessage1}</Box>
      <Box variant="p">{i18n.step2infoPanelMessage2}</Box>
      <Box variant="p">{i18n.step2infoPanelMessage3}</Box>
    </SpaceBetween>
    </HelpPanel>;
  }

  function renderStep3InfoPanel() {
    return <HelpPanel header={<h2>{i18n.step3infoPanelHeader}</h2>}><SpaceBetween size={'s'}>
      <Box variant="p">{i18n.step3infoPanelMessage1}</Box>
      <Box variant="p">{i18n.step3infoPanelMessage2}</Box>
    </SpaceBetween>
    </HelpPanel>;
  }
};