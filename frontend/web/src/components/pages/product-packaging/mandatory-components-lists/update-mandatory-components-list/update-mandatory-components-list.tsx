import { useParams } from 'react-router-dom';
import { HelpPanel, Spinner } from '@cloudscape-design/components';
import { useUpdateMandatoryComponentsList } from './update-mandatory-components-list.logic';
import { packagingAPI } from '../../../../../services';
import { WorkbenchAppLayout } from '../../../../layout/workbench-app-layout/workbench-app-layout';
import { i18n } from './update-mandatory-components-list.translations';
import { MandatoryComponentsListWizard } from '..';
import { RouteNames } from '../../../../layout/navigation/navigation.static';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic';

export const UpdateMandatoryComponentsList = () => {
  const { navigateTo, getPathFor } = useNavigationPaths();
  const {
    platform,
    architecture,
    osVersion
  } = useParams();

  if (!platform || !architecture || !osVersion) {
    navigateTo(RouteNames.MandatoryComponentsLists);
    return <></>;
  }

  const {
    projectId,
    mandatoryComponentsList,
    isMandatoryComponentsListLoading,
    updateMandatoryComponentsList,
    updateMandatoryComponentsListInProgress,
  } = useUpdateMandatoryComponentsList({
    serviceApi: packagingAPI,
    mandatoryComponentsListPlatform: platform,
    mandatoryComponentsListArchitecture: architecture,
    mandatoryComponentsListOsVersion: osVersion
  });

  function renderContent() {
    if (isMandatoryComponentsListLoading || !mandatoryComponentsList) {
      return <Spinner size="large" />;
    }

    return <MandatoryComponentsListWizard
      projectId={projectId}
      mandatoryComponentsList={mandatoryComponentsList}
      wizardCancelAction={() => {
        navigateTo(RouteNames.ViewMandatoryComponentsList, {
          ':platform': platform,
          ':architecture': architecture,
          ':osVersion': osVersion,
        });
      }}
      wizardSubmitAction={updateMandatoryComponentsList}
      wizardSubmitInProgress={updateMandatoryComponentsListInProgress}
    />;
  }

  return <WorkbenchAppLayout
    breadcrumbItems={[
      { path: i18n.breadcrumbLevel1, href: getPathFor(RouteNames.MandatoryComponentsLists) },
      { path: i18n.breadcrumbLevel2, href: '#' },
    ]}
    content={renderContent()}
    contentType="default"
    tools={renderTools()}
  />;

  function renderTools() {
    return (
      <HelpPanel
        header={<h2>{i18n.helpTitle}</h2>}
      >
        <p>{i18n.helpDescription}</p>
      </HelpPanel>
    );
  }
};