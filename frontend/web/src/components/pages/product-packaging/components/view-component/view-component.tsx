import { Box, HelpPanel, SpaceBetween, Spinner } from '@cloudscape-design/components';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic.ts';
import { RouteNames } from '../../../../layout/navigation/navigation.static.ts';
import { WorkbenchAppLayout } from '../../../../layout/workbench-app-layout/workbench-app-layout.tsx';
import { i18n } from './view-component.translations';
import { packagingAPI } from '../../../../../services/API/packaging-api.ts';
import { useComponent } from './view-component.logic.ts';
import { useRecoilValue } from 'recoil';
import { selectedProjectState } from '../../../../../state/index.ts';
import { useParams } from 'react-router-dom';
import { ViewComponentHeader } from './view-component-header.tsx';
import { ViewComponentDetails } from './view-component-details.tsx';
import { ViewComponentVersions } from './view-component-versions.tsx';
import { ComponentShareModal } from '../component-share-modal/page.tsx';
import { ArchiveComponentModal } from '../../shared/archive-version-modal/archive-component-modal.tsx';

export const ViewComponent = () => {
  const { getPathFor, navigateTo } = useNavigationPaths();
  const selectedProject = useRecoilValue(selectedProjectState);
  const { componentId } = useParams();

  if (!componentId) {
    navigateTo(RouteNames.Components);
    return <></>;
  }
  if (!selectedProject.projectId) {
    return <></>;
  }
  const {
    componentResponse,
    componentLoading,
    archiveConfirmHandler,
    archivePromptVisible,
    archivingIsLoading,
    setArchivePromptVisible,
    shareConfirmHandler,
    sharePromptVisible,
    setSharePromptVisible,
    sharingIsLoading,
  } = useComponent({
    serviceApi: packagingAPI,
    projectId: selectedProject.projectId,
    componentId,
  });

  return (
    <WorkbenchAppLayout
      breadcrumbItems={[
        {
          path: i18n.breadcrumbLevel1,
          href: getPathFor(RouteNames.Components),
        },
        { path: i18n.breadcrumbLevel2, href: '#' },
      ]}
      content={renderContent()}
      contentType="default"
      customHeader={
        !componentLoading &&
          <ViewComponentHeader
            component={componentResponse?.component}
            setArchivePromptVisible={setArchivePromptVisible}
            setSharePromptVisible={setSharePromptVisible}
          />
      }
      tools={renderTools()}
    />
  );

  // eslint-disable-next-line complexity
  function renderContent() {
    if (!componentId || componentLoading) {
      return <Spinner size="large" />;
    }

    return (
      <>
        <SpaceBetween direction="vertical" size="l">
          <ViewComponentDetails
            component={componentResponse?.component}
            componentLoading={componentLoading}
            componentMetadata={componentResponse?.metadata}
          />
          <ViewComponentVersions component={componentResponse?.component} />
        </SpaceBetween>
        <ArchiveComponentModal
          componentName={componentResponse?.component.componentName || ''}
          onClose={() => setArchivePromptVisible(false)}
          isOpen={archivePromptVisible}
          onConfirm={archiveConfirmHandler}
          isLoading={archivingIsLoading}
        />
        <ComponentShareModal
          somethingIsPending={sharingIsLoading}
          sharePromptVisible={sharePromptVisible}
          setSharePromptVisible={setSharePromptVisible}
          associatedProjectIds={
            componentResponse?.metadata?.associatedProjects.map(
              (md) => md.projectId
            ) ?? []
          }
          shareConfirmHandler={shareConfirmHandler}
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
              <li><b>{i18n.infoPanelPoint6}</b><br />{i18n.infoPanelPoint6Message}</li>
            </ul>
          </Box>
        </SpaceBetween>
      </HelpPanel>
    );
  }
};
