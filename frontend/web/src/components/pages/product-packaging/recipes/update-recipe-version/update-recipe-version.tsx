import { RouteNames } from '../../../../layout/navigation/navigation.static';
import { WorkbenchAppLayout } from '../../../../layout/workbench-app-layout/workbench-app-layout';
import { i18n } from './update-recipe-version.translations';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic';
import { useParams } from 'react-router-dom';
import { Box, HelpPanel, SpaceBetween, Spinner } from '@cloudscape-design/components';
import { RecipeVersionWizard } from '../shared';
import { useUpdateRecipeVersion } from './update-recipe-version.logic';
import { selectedProjectState } from '../../../../../state';
import { useRecoilValue } from 'recoil';
import { useState, useEffect } from 'react';
import { BreadcrumbItem } from '../../../../layout';

const EMPTY_ARRAY_LENGTH = 0;
const STEP_1_INDEX = 0;
const STEP_2_INDEX = 1;
const STEP_3_INDEX = 2;

export const UpdateRecipeVersion = () => {
  const { getPathFor, navigateTo } = useNavigationPaths();
  const { recipeId, versionId } = useParams();
  const selectedProject = useRecoilValue(selectedProjectState);
  const [activeStepIndex, setActiveStepIndex] = useState(EMPTY_ARRAY_LENGTH);

  const {
    recipeVersion,
    isRecipeVersionLoading,
    updateRecipeVersion,
    updateRecipeVersionInProgress,
    recipeVersionMandatories,
  } = useUpdateRecipeVersion({
    recipeId: recipeId as string,
    recipeVersionId: versionId as string,
    projectId: selectedProject.projectId as string,
  });

  useEffect(() => {
    if (!recipeId || !versionId) {
      navigateTo(RouteNames.Recipes);
    }
  }, [recipeId, versionId, navigateTo]);

  if (!recipeId || !versionId || !recipeVersion) {
    return <></>;
  }

  return <WorkbenchAppLayout
    breadcrumbItems={getBreadcrumbItems()}
    content={renderContent()}
    contentType="default"
    tools={renderTools()}
  />;

  function getBreadcrumbItems(): BreadcrumbItem[] {
    return [
      { path: i18n.breadcrumbLevel1, href: getPathFor(RouteNames.Recipes) },
      {
        path: i18n.breadcrumbLevel2,
        href: getPathFor(RouteNames.ViewRecipe, { ':recipeId': recipeId })
      },
      { path: i18n.breadcrumbLevel3, href: '#' },
    ];
  }
  function renderContent() {
    if (isRecipeVersionLoading) {
      return <Spinner size="large" />;
    }

    return <RecipeVersionWizard
      projectId={selectedProject.projectId || ''}
      recipeId={recipeId || ''}
      recipeVersion={recipeVersion}
      wizardCancelAction={() =>
        navigateTo(RouteNames.ViewRecipeVersion, {
          ':recipeId': recipeId,
          ':versionId': recipeVersion?.recipeVersionId,
        })}
      wizardSubmitAction={updateRecipeVersion}
      wizardSubmitInProgress={updateRecipeVersionInProgress}
      activeStepIndex={activeStepIndex}
      setActiveStepIndex={setActiveStepIndex}
      recipeVersionMandatories={recipeVersionMandatories}
    />;
  }
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