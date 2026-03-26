import {
  ComponentVersion,
  GetComponentVersionsResponse,
} from '../../../../../services/API/proserve-wb-packaging-api';

import useSwr, { useSWRConfig } from 'swr';
import { useNotifications } from '../../../../layout';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic';
import { selectedProjectState } from '../../../../../state';
import { useRecoilValue } from 'recoil';
import { RouteNames } from '../../../../layout/navigation/navigation.static';
import { useState } from 'react';
import { i18n } from './view-component.translations';
import { extractErrorResponseMessage } from '../../../../../utils/api-helpers';

interface ServiceAPI {
  getComponentVersions: (projectId: string, componentId: string) => Promise<GetComponentVersionsResponse>,
  releaseComponentVersion: (
    projectId: string,
    componentId: string,
    versionId: string,
  ) => Promise<object>,
  retireComponentVersion: (projectId: string, componentId: string, versionId: string) => Promise<object>,
}

interface Props {
  serviceApi: ServiceAPI,
  projectId?: string,
  componentId?: string,
}

const FETCH_KEY = (
  projectId?: string,
  componentId?: string,
) => {
  if (!projectId || !componentId) {
    return null;
  }
  return [
    `components/${componentId}/versions`,
    projectId,
    componentId,
  ];
};

export function useComponentVersions({ serviceApi, componentId }: Props) {
  const { navigateTo } = useNavigationPaths();
  const [selectedComponentVersion, setSelectedComponentVersion] = useState<ComponentVersion>();
  const [isReleaseComponentVersionModalOpen, setIsReleaseComponentVersionModalOpen] = useState(false);
  const [isReleaseInProgress, setIsReleaseInProgress] = useState(false);
  const [isRetireComponentVersionModalOpen, setIsRetireComponentVersionModalOpen] = useState(false);
  const [isRetireInProgress, setIsRetireInProgress] = useState(false);

  const selectedProject = useRecoilValue(selectedProjectState);

  const { showErrorNotification, showSuccessNotification } = useNotifications();

  const { cache } = useSWRConfig();

  const fetcher = ([
    ,
    projectId,
    componentId,
  ]: [
    url: string,
    projectId: string,
    componentId: string,
  ]) => {
    return serviceApi.getComponentVersions(projectId, componentId);
  };

  const { data, isLoading, mutate } = useSwr(
    FETCH_KEY(selectedProject.projectId, componentId),
    fetcher, {
      shouldRetryOnError: false,
      onError: (err) => {
        showErrorNotification({
          header: i18n.fetchComponentVersionsError,
          content: err.message
        });
      }
    }
  );
  return {
    componentVersions: data?.componentVersions || [],
    componentVersionsLoading: isLoading,
    loadComponentVersions,
    updateComponentVersion: navigateToUpdateComponentVersion,
    viewComponentVersion: navigateToViewComponentVersion,
    setSelectedComponentVersion,
    selectedComponentVersion,
    releaseComponentVersion,
    setIsReleaseComponentVersionModalOpen,
    isReleaseComponentVersionModalOpen,
    isReleaseInProgress,
    setIsRetireComponentVersionModalOpen,
    isRetireComponentVersionModalOpen,
    retireComponentVersion,
    isRetireInProgress
  };

  function loadComponentVersions() {
    cache.delete(`components/${componentId}/versions`);
    mutate(undefined);
  }

  function navigateToUpdateComponentVersion() {
    navigateTo(RouteNames.UpdateComponentVersion, {
      ':componentId': componentId,
      ':versionId': selectedComponentVersion?.componentVersionId,
    });
  }

  function navigateToViewComponentVersion() {
    navigateTo(RouteNames.ViewComponentVersion, {
      ':componentId': componentId,
      ':versionId': selectedComponentVersion?.componentVersionId,
    }, {
      componentVersionDescription: selectedComponentVersion?.componentVersionDescription,
    });
  }

  function releaseComponentVersion() {
    if (selectedProject?.projectId && componentId && selectedComponentVersion?.componentVersionId) {
      setIsReleaseInProgress(true);
      serviceApi.releaseComponentVersion(
        selectedProject.projectId,
        componentId,
        selectedComponentVersion?.componentVersionId,
      ).
        then(() => {
          showSuccessNotification({
            header: i18n.releaseComponentVersionSuccessMessageHeader,
            content: i18n.releaseComponentVersionSuccessMessageContent
          });
          loadComponentVersions();
          setIsReleaseComponentVersionModalOpen(false);
        }).catch(async e => {
          showErrorNotification({
            header: i18n.releaseComponentVersionFailedMessageHeader,
            content: await extractErrorResponseMessage(e)
          });
        }).finally(() => setIsReleaseInProgress(false));
    }
  }

  function retireComponentVersion() {
    if (selectedProject?.projectId && componentId && selectedComponentVersion?.componentVersionId) {
      setIsRetireInProgress(true);
      serviceApi.retireComponentVersion(
        selectedProject.projectId,
        componentId,
        selectedComponentVersion?.componentVersionId
      ).
        then(() => {
          showSuccessNotification({
            header: i18n.retireComponentVersionSuccessMessageHeader,
            content: i18n.retireComponentVersionSuccessMessageContent
          });
          loadComponentVersions();
          setIsRetireComponentVersionModalOpen(false);
        }).catch(async e => {
          showErrorNotification({
            header: i18n.retireComponentVersionFailedMessageHeader,
            content: await extractErrorResponseMessage(e)
          });
        }).finally(() => setIsRetireInProgress(false));
    }
  }
}