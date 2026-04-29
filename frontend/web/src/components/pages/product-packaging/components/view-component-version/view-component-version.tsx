/* eslint-disable complexity */
import { Box, HelpPanel, SpaceBetween, Spinner, Tabs, TabsProps } from '@cloudscape-design/components';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic.ts';
import { RouteNames } from '../../../../layout/navigation/navigation.static.ts';
import { WorkbenchAppLayout } from '../../../../layout/workbench-app-layout/workbench-app-layout.tsx';
import { i18n } from './view-component-version.translations';
import { packagingAPI } from '../../../../../services/API/packaging-api.ts';
import { useViewComponentVersion } from './view-component-version.logic.ts';
import { useRecoilValue } from 'recoil';
import { selectedProjectState } from '../../../../../state/index.ts';
import { useParams } from 'react-router-dom';
import { ViewComponentVersionHeader } from './view-component-version-header.tsx';
import { ViewComponentVersionOverview } from './view-component-version-overview.tsx';
import { ComponentVersionEntriesView, RetireVersionModal, ReleaseVersionModal } from '../../shared';
import { ViewComponentVersionYaml } from './view-component-version-yaml.tsx';
import { ViewComponentVersionTests } from './view-component-version-tests.tsx';
import { ViewComponentVersionAssociatedComponents } from './view-component-version-associated-components';
import { ViewComponentVersionAssociatedRecipes } from './view-component-version-associated-recipes';


export const ViewComponentVersion = () => {
  const { getPathFor, navigateTo } = useNavigationPaths();
  const selectedProject = useRecoilValue(selectedProjectState);
  const { componentId, versionId } = useParams();

  // Call hooks before any early returns to comply with rules of hooks
  const {
    componentVersion,
    componentVersionLoading,
    isReleaseComponentVersionModalOpen,
    setIsReleaseComponentVersionModalOpen,
    releaseComponentVersion,
    isReleaseInProgress,
    yamlDefinitionBase64,
    viewComponent,
    updateComponentVersion,
    isRetireComponentVersionModalOpen,
    setIsRetireComponentVersionModalOpen,
    retireComponentVersion,
    isRetireInProgress,
  } = useViewComponentVersion({
    serviceApi: packagingAPI,
    projectId: selectedProject.projectId,
    componentId: componentId || '',
    versionId: versionId || ''
  });

  if (!componentId || !versionId) {
    navigateTo(RouteNames.Components);
    return <></>;
  }

  const CHAR_CODE_BASE = 0;
  const yamlDefinitionBinaryString = atob(yamlDefinitionBase64 || '');
  const bytes = Uint8Array.from(yamlDefinitionBinaryString, char => char.charCodeAt(CHAR_CODE_BASE));
  const yamlDefinitionDecodedString = new TextDecoder().decode(bytes);

  const tabDefinitions: TabsProps.Tab[] = [
    {
      label: i18n.yamlHeader,
      id: 'yaml-configuration',
      content: <ViewComponentVersionYaml
        componentVersion={componentVersion}
        componentVersionLoading={componentVersionLoading}
        yamlDefinition={yamlDefinitionDecodedString}
      />
    },
    {
      label: i18n.componentVersionDependenciesHeader,
      id: 'component-version-dependencies',
      content:
        componentVersion?.componentVersionDependencies &&
        // eslint-disable-next-line @typescript-eslint/no-magic-numbers
        componentVersion?.componentVersionDependencies?.length > 0
          ? <ComponentVersionEntriesView
            componentVersionEntries={
              componentVersion?.componentVersionDependencies || []
            }
          />
          : <Box>{i18n.noComponentVersionDependencies}</Box>
    },
    {
      label: i18n.testExecutionsHeader,
      id: 'test-executions',
      content: <ViewComponentVersionTests
        componentId={componentId}
        versionId={versionId}
      />
    },
    {
      label: i18n.associatedComponentsHeader,
      id: 'associated-components',
      content: <ViewComponentVersionAssociatedComponents
        associatedComponentsVersions={componentVersion?.associatedComponentsVersions}
        isLoading={componentVersionLoading}
      />
    },
    {
      label: i18n.associatedRecipesHeader,
      id: 'associated-recipes',
      content: <ViewComponentVersionAssociatedRecipes
        associatedRecipesVersions={componentVersion?.associatedRecipesVersions}
        isLoading={componentVersionLoading}
      />
    },
  ];

  return <WorkbenchAppLayout
    breadcrumbItems={[
      { path: i18n.breadcrumbLevel1, href: getPathFor(RouteNames.Components) },
      {
        path: i18n.breadcrumbLevel2,
        href: getPathFor(RouteNames.ViewComponent, { ':componentId': componentId })
      },
      { path: i18n.breadcrumbLevel3, href: '#' },
    ]}
    content={renderContent()}
    contentType="default"
    customHeader={!componentVersionLoading &&
      <ViewComponentVersionHeader
        componentVersion={componentVersion}
        viewComponent = {viewComponent}
        updateComponentVersion = {updateComponentVersion}
        openReleaseComponentVersionModal={()=> setIsReleaseComponentVersionModalOpen(true)}
        openRetireComponentVersionModal={()=> setIsRetireComponentVersionModalOpen(true)}
      />
    }
    tools={renderTools()}
  />;

  function renderContent() {
    if (!componentId || componentVersionLoading) {
      return <Spinner size="large" />;
    }

    return <SpaceBetween direction="vertical" size="l">
      <SpaceBetween size="l">
        <ViewComponentVersionOverview
          componentVersion={componentVersion}
          componentVersionLoading={componentVersionLoading}
        />
        <Tabs tabs={tabDefinitions} />
      </SpaceBetween>
      <ReleaseVersionModal
        isLoading={componentVersionLoading || isReleaseInProgress}
        isOpen={isReleaseComponentVersionModalOpen}
        onClose={() => setIsReleaseComponentVersionModalOpen(false)}
        onConfirm={() => releaseComponentVersion()}
        versionName={componentVersion?.componentVersionName || ''}
      />
      <RetireVersionModal
        isLoading={componentVersionLoading || isRetireInProgress}
        isOpen={isRetireComponentVersionModalOpen}
        onClose={() => setIsRetireComponentVersionModalOpen(false)}
        onConfirm={retireComponentVersion}
        versionName={componentVersion?.componentVersionName || ''}
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