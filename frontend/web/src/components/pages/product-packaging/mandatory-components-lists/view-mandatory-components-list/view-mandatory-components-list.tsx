/* eslint-disable complexity */
import {
  Alert,
  SpaceBetween,
  Spinner,
} from '@cloudscape-design/components';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic.ts';
import { RouteNames } from '../../../../layout/navigation/navigation.static.ts';
import { WorkbenchAppLayout } from '../../../../layout/workbench-app-layout/workbench-app-layout.tsx';
import { i18n } from './view-mandatory-components-list.translations.ts';
import { packagingAPI } from '../../../../../services/API/packaging-api.ts';
import { useViewMandatoryComponentsList } from './view-mandatory-components-list.logic.ts';
import { useRecoilValue } from 'recoil';
import { selectedProjectState } from '../../../../../state/index.ts';
import { useParams } from 'react-router-dom';
import { ViewMandatoryComponentsListHeader } from './view-mandatory-components-list-header.tsx';
import { ViewMandatoryComponentsListOverview } from './view-mandatory-components-list-overview.tsx';
import { MandatoryComponentsPositionedView } from './mandatory-components-positioned-view.tsx';

export const ViewMandatoryComponentsList = () => {
  const { getPathFor, navigateTo } = useNavigationPaths();
  const selectedProject = useRecoilValue(selectedProjectState);
  const { platform, architecture, osVersion } = useParams();

  if (!platform || !architecture || !osVersion) {
    navigateTo(RouteNames.Recipes);
    return <></>;
  }

  const {
    mandatoryComponentsList,
    mandatoryComponentsListLoading,
    viewMandatoryComponentsLists,
    updateMandatoryComponentsList,
  } = useViewMandatoryComponentsList({
    serviceApi: packagingAPI,
    projectId: selectedProject.projectId || '',
    platform,
    architecture,
    osVersion,
  });

  return (
    <WorkbenchAppLayout
      breadcrumbItems={[
        {
          path: i18n.breadcrumbLevel1,
          href: getPathFor(RouteNames.MandatoryComponentsLists),
        },
        { path: i18n.breadcrumbLevel2, href: '#' },
      ]}
      content={renderContent()}
      contentType="default"
      customHeader={
        !mandatoryComponentsListLoading &&
          <ViewMandatoryComponentsListHeader
            mandatoryComponentsList={mandatoryComponentsList}
            viewMandatoryComponentsLists={viewMandatoryComponentsLists}
            updateMandatoryComponentsList={updateMandatoryComponentsList}
          />

      }
    />
  );

  function renderContent() {
    if (!mandatoryComponentsList || mandatoryComponentsListLoading) {
      return <Spinner size="large" />;
    }

    return (
      <SpaceBetween direction="vertical" size="l">
        <SpaceBetween size="l">
          <Alert type="info">{i18n.mandatoryComponentListsAlert}</Alert>
          <ViewMandatoryComponentsListOverview
            mandatoryComponentsList={mandatoryComponentsList}
            mandatoryComponentsListLoading={mandatoryComponentsListLoading}
          />
          <MandatoryComponentsPositionedView
            prependedComponents={mandatoryComponentsList.prependedComponentsVersions || []}
            appendedComponents={mandatoryComponentsList.appendedComponentsVersions || []}
          />
        </SpaceBetween>
      </SpaceBetween>
    );
  }
};
