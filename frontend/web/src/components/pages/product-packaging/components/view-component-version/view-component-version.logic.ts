import {
  GetComponentVersionResponse,
} from '../../../../../services/API/proserve-wb-packaging-api';

import useSwr, { useSWRConfig } from 'swr';
import { useNotifications } from '../../../../layout';
import { useState } from 'react';
import { i18n } from './view-component-version.translations';
import { extractErrorResponseMessage } from '../../../../../utils/api-helpers';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../../../layout/navigation/navigation.static';

interface ServiceAPI {
  getComponentVersion: (projectId: string, componentId: string, versionId: string)
  => Promise<GetComponentVersionResponse>,
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
  versionId?: string,
}

const FETCH_KEY = (
  projectId?: string,
  componentId?: string,
  versionId?: string
) => {
  if (!projectId || !componentId) {
    return null;
  }
  return [
    `components/${componentId}/versions/${versionId}`,
    projectId,
    componentId,
    versionId
  ];
};

export function useViewComponentVersion({ serviceApi, projectId, componentId, versionId }: Props) {
  const { navigateTo } = useNavigationPaths();
  const [isReleaseComponentVersionModalOpen, setIsReleaseComponentVersionModalOpen] = useState(false);
  const [isReleaseInProgress, setIsReleaseInProgress] = useState(false);
  const [isRetireComponentVersionModalOpen, setIsRetireComponentVersionModalOpen] = useState(false);
  const [isRetireInProgress, setIsRetireInProgress] = useState(false);
  const { showSuccessNotification, showErrorNotification } = useNotifications();
  const { cache } = useSWRConfig();
  const fetcher = ([
    ,
    projectId,
    componentId,
    versionId
  ]: [
    url: string,
    projectId: string,
    componentId: string,
    versionId: string
  ]) => {
    return serviceApi.getComponentVersion(projectId, componentId, versionId);
  };

  const { data, isLoading, mutate } = useSwr(
    FETCH_KEY(projectId, componentId, versionId),
    fetcher, {
      shouldRetryOnError: false,
      onError: (err) => {
        showErrorNotification({
          header: i18n.fetchComponentVersionError,
          content: err.message
        });
      }
    }
  );

  function loadComponentVersion() {
    cache.delete(`components/${componentId}/versions/${versionId}`);
    mutate();
  }

  function navigateToViewComponent() {
    navigateTo(RouteNames.ViewComponent, {
      ':componentId': componentId
    });
  }

  function navigateToUpdateComponentVersion() {
    navigateTo(RouteNames.UpdateComponentVersion, {
      ':componentId': componentId,
      ':versionId': versionId,
    });
  }

  return {
    componentVersion: data?.componentVersion,
    componentVersionLoading: isLoading,
    isReleaseComponentVersionModalOpen,
    setIsReleaseComponentVersionModalOpen,
    releaseComponentVersion,
    isReleaseInProgress,
    yamlDefinition: data?.yamlDefinition,
    yamlDefinitionBase64: data?.yamlDefinitionB64,
    viewComponent: navigateToViewComponent,
    updateComponentVersion: navigateToUpdateComponentVersion,
    isRetireComponentVersionModalOpen,
    setIsRetireComponentVersionModalOpen,
    retireComponentVersion,
    isRetireInProgress,
  };

  function releaseComponentVersion() {
    if (projectId && componentId && data?.componentVersion?.componentVersionId) {
      setIsReleaseInProgress(true);
      serviceApi.releaseComponentVersion(
        projectId,
        componentId,
        data?.componentVersion?.componentVersionId,
      ).
        then(() => {
          showSuccessNotification({
            header: i18n.releaseComponentVersionSuccessMessageHeader,
            content: i18n.releaseComponentVersionSuccessMessageContent
          });
          loadComponentVersion();
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
    if (projectId && componentId && data?.componentVersion?.componentVersionId) {
      setIsRetireInProgress(true);
      serviceApi.retireComponentVersion(
        projectId,
        componentId,
        data?.componentVersion?.componentVersionId
      ).
        then(() => {
          showSuccessNotification({
            header: i18n.retireComponentVersionSuccessMessageHeader,
            content: i18n.retireComponentVersionSuccessMessageContent
          });
          loadComponentVersion();
          setIsRetireComponentVersionModalOpen(false);
        }).catch(async e => {
          showErrorNotification({
            header: i18n.retireComponentVersionFailedMessageHeader,
            content: await extractErrorResponseMessage(e)
          });
        }).finally(()=> setIsRetireInProgress(false));
    }
  }
}