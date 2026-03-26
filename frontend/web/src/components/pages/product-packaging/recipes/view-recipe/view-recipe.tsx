import { Box, HelpPanel, SpaceBetween, Spinner } from '@cloudscape-design/components';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic.ts';
import { RouteNames } from '../../../../layout/navigation/navigation.static.ts';
import { WorkbenchAppLayout } from '../../../../layout/workbench-app-layout/workbench-app-layout.tsx';
import { i18n } from './view-recipe.translations';
import { packagingAPI } from '../../../../../services/API/packaging-api.ts';
import { useRecipe } from './view-recipe.logic.ts';
import { useRecoilValue } from 'recoil';
import { selectedProjectState } from '../../../../../state/index.ts';
import { useParams } from 'react-router-dom';
import { ViewRecipeHeader } from './view-recipe-header.tsx';
import { ViewRecipeDetails } from './view-recipe-details.tsx';
import { ViewRecipeVersions } from './view-recipe-versions.tsx';
import { ArchiveRecipeModal } from '../../shared/archive-version-modal/archive-recipe-modal.tsx';

export const ViewRecipe = () => {
  const { getPathFor, navigateTo } = useNavigationPaths();
  const selectedProject = useRecoilValue(selectedProjectState);
  const { recipeId } = useParams();

  if (!recipeId) {
    navigateTo(RouteNames.Recipes);
    return <></>;
  }
  if (!selectedProject.projectId) {
    return <></>;
  }
  const {
    recipeResponse,
    recipeLoading,
    archiveConfirmHandler,
    archivePromptVisible,
    archivingIsLoading,
    setArchivePromptVisible,
  } = useRecipe({
    serviceApi: packagingAPI,
    projectId: selectedProject.projectId,
    recipeId,
  });

  return (
    <WorkbenchAppLayout
      breadcrumbItems={[
        {
          path: i18n.breadcrumbLevel1,
          href: getPathFor(RouteNames.Recipes),
        },
        { path: i18n.breadcrumbLevel2, href: '#' },
      ]}
      content={renderContent()}
      contentType="default"
      customHeader={
        !recipeLoading &&
          <ViewRecipeHeader
            recipe={recipeResponse?.recipe}
            setArchivePromptVisible={setArchivePromptVisible}
          />
      }
      tools={renderTools()}
    />
  );


  function renderContent() {
    if (!recipeId || recipeLoading) {
      return <Spinner size="large" />;
    }

    return (
      <>
        <SpaceBetween direction="vertical" size="l">
          <ViewRecipeDetails
            recipe={recipeResponse?.recipe}
            recipeLoading={recipeLoading}
          />
          <ViewRecipeVersions recipeId={recipeId} />
        </SpaceBetween>
        <ArchiveRecipeModal
          recipeName={recipeResponse?.recipe.recipeName || ''}
          onClose={() => setArchivePromptVisible(false)}
          isOpen={archivePromptVisible}
          onConfirm={archiveConfirmHandler}
          isLoading={archivingIsLoading}
        />
      </>
    );
  }

  function renderTools() {
    return (
      <HelpPanel header={<h2>{i18n.infoPanelHeader}</h2>}>
        <SpaceBetween size={'s'}>
          <Box variant="awsui-key-label">{i18n.infoPanelLabel1}</Box>
          <Box variant="p">{i18n.infoPanelMessage1}</Box>
          <Box>
            <p>{i18n.infoPanelMessage2}</p>
            <ul>
              <li><b>{i18n.infoPanelPoint1}</b><br />{i18n.infoPanelPoint1Message}</li>
              <li><b>{i18n.infoPanelPoint2}</b><br />{i18n.infoPanelPoint2Message}</li>
              <li><b>{i18n.infoPanelPoint3}</b><br />{i18n.infoPanelPoint3Message}</li>
              <li><b>{i18n.infoPanelPoint4}</b><br />{i18n.infoPanelPoint4Message}</li>
              <li><b>{i18n.infoPanelPoint5}</b><br />{i18n.infoPanelPoint5Message}</li>
            </ul>
          </Box>
        </SpaceBetween>
      </HelpPanel>
    );
  }
};
