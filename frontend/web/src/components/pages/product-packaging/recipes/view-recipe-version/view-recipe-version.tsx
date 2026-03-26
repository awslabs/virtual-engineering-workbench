/* eslint-disable complexity */
import { Box, HelpPanel, SpaceBetween, Spinner, Tabs, TabsProps } from '@cloudscape-design/components';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic.ts';
import { RouteNames } from '../../../../layout/navigation/navigation.static.ts';
import { WorkbenchAppLayout } from '../../../../layout/workbench-app-layout/workbench-app-layout.tsx';
import { i18n } from './view-recipe-version.translations';
import { packagingAPI } from '../../../../../services/API/packaging-api.ts';
import { useViewRecipeVersion } from './view-recipe-version.logic.ts';
import { useRecoilValue } from 'recoil';
import { selectedProjectState } from '../../../../../state/index.ts';
import { useParams } from 'react-router-dom';
import { ViewRecipeVersionHeader } from './view-recipe-version-header.tsx';
import { ViewRecipeVersionOverview } from './view-recipe-version-overview.tsx';
import { ComponentVersionEntriesView, ReleaseVersionModal, RetireVersionModal } from '../../shared';
import { ViewRecipeVersionTests } from './view-recipe-version-tests.tsx';


export const ViewRecipeVersion = () => {
  const { getPathFor, navigateTo } = useNavigationPaths();
  const selectedProject = useRecoilValue(selectedProjectState);
  const { recipeId, versionId } = useParams();

  if (!recipeId || !versionId) {
    navigateTo(RouteNames.Recipes);
    return <></>;
  }

  const {
    recipeVersion,
    recipeVersionLoading,
    isReleaseRecipeVersionModalOpen,
    setIsReleaseRecipeVersionModalOpen,
    releaseRecipeVersion,
    isReleaseInProgress,
    viewRecipe,
    updateRecipeVersion,
    isRetireRecipeVersionModalOpen,
    setIsRetireRecipeVersionModalOpen,
    retireRecipeVersion,
    isRetireInProgress,
  } = useViewRecipeVersion({
    serviceApi: packagingAPI,
    projectId: selectedProject.projectId,
    recipeId,
    versionId
  });

  const tabDefinitions: TabsProps.Tab[] = [
    {
      label: i18n.componentsVersionsHeader,
      id: 'component-versions',
      content: <ComponentVersionEntriesView
        componentVersionEntries={recipeVersion?.recipeComponentsVersions || [] }
        typeColumnEnabled
      />
    },
    {
      label: i18n.testExecutionsHeader,
      id: 'test-executions',
      content: <ViewRecipeVersionTests
        recipeId={recipeId}
        versionId={versionId}
      />
    },
  ];

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
    customHeader={!recipeVersionLoading &&
      <ViewRecipeVersionHeader
        recipeVersion={recipeVersion}
        viewRecipe = {viewRecipe}
        updateRecipeVersion = {updateRecipeVersion}
        openReleaseRecipeVersionModal={()=> setIsReleaseRecipeVersionModalOpen(true)}
        openRetireRecipeVersionModal={()=> setIsRetireRecipeVersionModalOpen(true)}
      />
    }
    tools={renderTools()}
  />;

  function renderContent() {
    if (!recipeId || recipeVersionLoading) {
      return <Spinner size="large" />;
    }

    return <SpaceBetween direction="vertical" size="l">
      <SpaceBetween size="l">
        <ViewRecipeVersionOverview
          recipeVersion={recipeVersion}
          recipeVersionLoading={recipeVersionLoading}
        />
        <Tabs tabs={tabDefinitions} />
      </SpaceBetween>
      <ReleaseVersionModal
        isLoading={recipeVersionLoading || isReleaseInProgress}
        isOpen={isReleaseRecipeVersionModalOpen}
        onClose={() => setIsReleaseRecipeVersionModalOpen(false)}
        onConfirm={releaseRecipeVersion}
        versionName={recipeVersion?.recipeVersionName || ''}
      />
      <RetireVersionModal
        isLoading={recipeVersionLoading || isRetireInProgress}
        isOpen={isRetireRecipeVersionModalOpen}
        onClose={() => setIsRetireRecipeVersionModalOpen(false)}
        onConfirm={retireRecipeVersion}
        versionName={recipeVersion?.recipeVersionName || ''}
      />
    </SpaceBetween>;
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
            </ul>
          </Box>
        </SpaceBetween>
      </HelpPanel>
    );
  }
};