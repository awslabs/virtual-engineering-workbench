import { useRecoilValue } from 'recoil';
import { useState, useEffect } from 'react';
import {
  ComponentVersionEntry,
  GetMandatoryComponentsListResponse,
  MandatoryComponentsList,
  UpdateMandatoryComponentsListRequest
} from '../../../../../services/API/proserve-wb-packaging-api';
import { selectedProjectState } from '../../../../../state';
import { useNotifications } from '../../../../layout';
import { extractErrorResponseMessage } from '../../../../../utils/api-helpers';
import { i18n } from './update-mandatory-components-list.translations';
import { RouteNames } from '../../../../layout/navigation/navigation.static';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic';

interface ServiceAPI {
  getMandatoryComponentsList: (
    projectId: string,
    mandatoryComponentsListPlatform: string,
    mandatoryComponentsListArchitecture: string,
    mandatoryComponentsListOsVersion: string
  ) => Promise<GetMandatoryComponentsListResponse>,
  updateMandatoryComponentsList: (
    projectId: string,
    body: UpdateMandatoryComponentsListRequest
  ) => Promise<object>,
}

interface Props {
  serviceApi: ServiceAPI,
  mandatoryComponentsListPlatform: string,
  mandatoryComponentsListArchitecture: string,
  mandatoryComponentsListOsVersion: string,
}

const parametersValid = (
  a: string | undefined,
  b: string | undefined,
  c: string | undefined,
  d: string | undefined
) => {
  return a && b && c && d;
};

export const useUpdateMandatoryComponentsList = ({
  serviceApi,
  mandatoryComponentsListPlatform,
  mandatoryComponentsListArchitecture,
  mandatoryComponentsListOsVersion
}: Props) => {
  const selectedProject = useRecoilValue(selectedProjectState);
  const [
    updateMandatoryComponentsListInProgress,
    setUpdateMandatoryComponentsListInProgress,
  ] = useState(false);
  const [mandatoryComponentsList, setUpdateMandatoryComponentsList] = useState<MandatoryComponentsList>();
  const [mandatoryComponentsListLoading, setUpdateMandatoryComponentsListLoading] = useState(false);
  const { showErrorNotification, showSuccessNotification } = useNotifications();
  const { navigateTo } = useNavigationPaths();

  function getMandatoryComponentsList() {
    if (!selectedProject.projectId) { return; }

    setUpdateMandatoryComponentsListLoading(true);
    serviceApi.getMandatoryComponentsList(
      selectedProject.projectId,
      mandatoryComponentsListPlatform,
      mandatoryComponentsListArchitecture,
      mandatoryComponentsListOsVersion
    ).then((response) => {
      setUpdateMandatoryComponentsList(response.mandatoryComponentsList);
    }).catch(async e => {
      showErrorNotification({
        header: i18n.fetchMandatoryComponentsListError,
        content: await extractErrorResponseMessage(e)
      });
    }).finally(() => setUpdateMandatoryComponentsListLoading(false));
  }

  useEffect(() => {
    getMandatoryComponentsList();
  }, []);

  function updateMandatoryComponentsList(
    mandatoryComponentsListPlatform: string,
    mandatoryComponentsListOsVersion: string,
    mandatoryComponentsListArchitecture: string,
    prependedComponentsVersions: ComponentVersionEntry[],
    appendedComponentsVersions: ComponentVersionEntry[]
  ) {
    const mandatoryComponentsList: UpdateMandatoryComponentsListRequest = {
      mandatoryComponentsListPlatform: mandatoryComponentsListPlatform,
      mandatoryComponentsListArchitecture: mandatoryComponentsListArchitecture,
      mandatoryComponentsListOsVersion: mandatoryComponentsListOsVersion,
      prependedComponentsVersions: prependedComponentsVersions,
      appendedComponentsVersions: appendedComponentsVersions
    };
    if (parametersValid(selectedProject.projectId, mandatoryComponentsListPlatform,
      mandatoryComponentsListArchitecture, mandatoryComponentsListOsVersion)) {
      setUpdateMandatoryComponentsListInProgress(true);
      serviceApi.updateMandatoryComponentsList(
        selectedProject.projectId!,
        mandatoryComponentsList
      ).then(() => {
        showSuccessNotification({
          header: i18n.updateSuccessMessageHeader,
          content: i18n.updateSuccessMessageContent
        });
        navigateTo(RouteNames.MandatoryComponentsLists);
      }).catch(async e => {
        showErrorNotification({
          header: i18n.updateFailMessageHeader,
          content: await extractErrorResponseMessage(e)
        });
      }).finally(() => setUpdateMandatoryComponentsListInProgress(false));
    }
  }

  return {
    projectId: selectedProject.projectId || '',
    mandatoryComponentsList: mandatoryComponentsList,
    isMandatoryComponentsListLoading: mandatoryComponentsListLoading,
    updateMandatoryComponentsList,
    updateMandatoryComponentsListInProgress,
  };
};