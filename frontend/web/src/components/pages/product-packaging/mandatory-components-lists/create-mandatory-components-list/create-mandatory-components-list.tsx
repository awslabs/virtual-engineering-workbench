import { WorkbenchAppLayout } from '../../../../layout/workbench-app-layout/workbench-app-layout';
import { HelpPanel } from '@cloudscape-design/components';
import { selectedProjectState } from '../../../../../state';
import { useRecoilValue } from 'recoil';
import { MandatoryComponentsListWizard } from '..';
import { i18n } from './create-mandatory-components-list.translations';
import {
  ComponentVersionEntry,
  CreateMandatoryComponentsListRequest
} from '../../../../../services/API/proserve-wb-packaging-api';
import { packagingAPI } from '../../../../../services';
import { extractErrorResponseMessage } from '../../../../../utils/api-helpers';
import { useState } from 'react';
import { useNotifications } from '../../../../layout';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../../../layout/navigation/navigation.static';

export const CreateMandatoryComponentsList = () => {
  const selectedProject = useRecoilValue(selectedProjectState);
  const [
    createMandatoryComponentsListInProgress,
    setCreateMandatoryComponentsListInProgress,
  ] = useState(false);
  const { showErrorNotification, showSuccessNotification } = useNotifications();
  const { navigateTo, getPathFor } = useNavigationPaths();

  function createMandatoryComponentsList(
    mandatoryComponentsListPlatform: string,
    mandatoryComponentsListOsVersion: string,
    mandatoryComponentsListArchitecture: string,
    prependedComponentsVersions: ComponentVersionEntry[],
    appendedComponentsVersions: ComponentVersionEntry[],
  ) {
    if (!selectedProject.projectId) {
      return;
    }

    const mandatoryComponentsList: CreateMandatoryComponentsListRequest = {
      mandatoryComponentsListPlatform: mandatoryComponentsListPlatform,
      mandatoryComponentsListOsVersion: mandatoryComponentsListOsVersion,
      mandatoryComponentsListArchitecture: mandatoryComponentsListArchitecture,
      prependedComponentsVersions: prependedComponentsVersions,
      appendedComponentsVersions: appendedComponentsVersions
    };

    setCreateMandatoryComponentsListInProgress(true);
    packagingAPI.createMandatoryComponentsList(
      selectedProject.projectId,
      mandatoryComponentsList
    ).then(() => {
      showSuccessNotification({
        header: i18n.createSuccessMessageHeader,
        content: i18n.createSuccessMessageContent
      });
      navigateTo(RouteNames.MandatoryComponentsLists);
    }).catch(async e => {
      showErrorNotification({
        header: i18n.createFailMessageHeader,
        content: await extractErrorResponseMessage(e)
      });
    }).finally(() => setCreateMandatoryComponentsListInProgress(false));
  }

  return <WorkbenchAppLayout
    breadcrumbItems={[
      { path: i18n.breadcrumbLevel1, href: getPathFor(RouteNames.MandatoryComponentsLists) },
      { path: i18n.breadcrumbLevel2, href: '#' },
    ]}
    content={<MandatoryComponentsListWizard
      projectId={selectedProject.projectId || ''}
      wizardCancelAction={() => navigateTo(RouteNames.MandatoryComponentsLists)}
      wizardSubmitAction={createMandatoryComponentsList}
      wizardSubmitInProgress={createMandatoryComponentsListInProgress}></MandatoryComponentsListWizard>}
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