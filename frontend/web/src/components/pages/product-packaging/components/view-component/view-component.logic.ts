import { GetComponentResponse } from '../../../../../services/API/proserve-wb-packaging-api';
import useSwr from 'swr';
import { useNotifications } from '../../../../layout';
import { i18n } from '../components.translations';
import { extractErrorResponseMessage } from '../../../../../utils/api-helpers';
import { useState } from 'react';

interface ServiceAPI {
  archiveComponent: (
    projectId: string,
    componentId: string,
  ) => Promise<object>,
  getComponent: (
    projectId: string,
    componentId: string
  ) => Promise<GetComponentResponse>,
  shareComponent: (
    projectId: string,
    componentId: string,
    projectIds: string[]
  ) => Promise<object>,
}

interface Props {
  serviceApi: ServiceAPI,
  projectId: string,
  componentId: string,
}

const FETCH_KEY = (projectId?: string, componentId?: string) => {
  if (!projectId || !componentId) {
    return null;
  }
  return [`components/${componentId}`, projectId, componentId];
};

export function useComponent({ serviceApi, projectId, componentId }: Props) {
  const [archivingIsLoading, setArchivingIsLoading] = useState(false);
  const [archivePromptVisible, setArchivePromptVisible] = useState(false);
  const [sharingIsLoading, setSharingIsLoading] = useState(false);
  const [sharePromptVisible, setSharePromptVisible] = useState(false);
  const { showErrorNotification, showSuccessNotification } = useNotifications();

  const fetcher = ([, projectId, componentId]: [
    url: string,
    projectId: string,
    componentId: string
  ]) => {
    return serviceApi.getComponent(projectId, componentId);
  };

  const { data, mutate, isLoading } = useSwr(
    FETCH_KEY(projectId, componentId),
    fetcher,
    {
      shouldRetryOnError: false,
      onError: (err) => {
        showErrorNotification({
          header: 'Unable to fetch component details',
          content: err.message,
        });
      },
    }
  );

  function archiveConfirmHandler() {
    setArchivingIsLoading(true);
    serviceApi
      .archiveComponent(projectId, componentId)
      .then(() => {
        showSuccessNotification({
          header: i18n.createSuccessMessageHeader,
          content: i18n.createArchiveSuccessMessageContent,
        });
      })
      .catch(async (e) => {
        showErrorNotification({
          header: i18n.createFailMessageHeader,
          content: await extractErrorResponseMessage(e),
        });
      })
      .finally(() => {
        setArchivingIsLoading(false);
        setArchivePromptVisible(false);
      });
  }

  function shareConfirmHandler(values: string[]) {
    setSharingIsLoading(true);
    serviceApi
      .shareComponent(projectId, componentId, values)
      .then(() => {
        showSuccessNotification({
          header: i18n.createSuccessMessageHeader,
          content: i18n.createShareSuccessMessageContent(values),
        });
        mutate();
      })
      .catch(async (e) => {
        showErrorNotification({
          header: i18n.createFailMessageHeader,
          content: await extractErrorResponseMessage(e),
        });
      })
      .finally(() => {
        setSharingIsLoading(false);
        setSharePromptVisible(false);
      });
  }

  return {
    componentResponse: data,
    componentLoading: isLoading,
    archiveConfirmHandler,
    archivePromptVisible,
    archivingIsLoading,
    setArchivePromptVisible,
    shareConfirmHandler,
    sharePromptVisible,
    sharingIsLoading,
    setSharePromptVisible,
  };
}
