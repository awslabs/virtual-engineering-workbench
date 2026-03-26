import {
  ComponentVersionTestExecutionSummary,
  GetComponentVersionTestExecutionsResponse,
  GetComponentVersionTestExecutionLogsUrlResponse
} from '../../../../../services/API/proserve-wb-packaging-api';
import useSwr, { useSWRConfig } from 'swr';
import { useNotifications } from '../../../../layout';
import { useState } from 'react';
import { i18n } from './view-component-version.translations';
import { downloadFile } from '../../../../../utils/download-file';

interface ServiceAPI {
  getComponentVersionTestExecutions: (projectId: string, componentId: string, versionId: string)
  => Promise<GetComponentVersionTestExecutionsResponse>,
  getComponentVersionTestExecutionLogsUrl: (
    projectId: string,
    componentId: string,
    versionId: string,
    testExecutionId: string,
    instanceId: string
  )=> Promise<GetComponentVersionTestExecutionLogsUrlResponse>,
}

interface Props {
  serviceApi: ServiceAPI,
  projectId: string,
  componentId: string,
  versionId: string,
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
    `components/${componentId}/versions/${versionId}/test-executions`,
    projectId,
    componentId,
    versionId
  ];
};


export function useViewComponentVersionTests({ serviceApi, projectId, componentId, versionId }: Props) {
  const [selectedTestExecution, setSelectedTestExecution]
    = useState<ComponentVersionTestExecutionSummary>();
  const { showErrorNotification } = useNotifications();
  const { cache } = useSWRConfig();
  const [downloadLogsInProgress, setDownloadLogsInProgress] = useState(false);
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
    return serviceApi.getComponentVersionTestExecutions(projectId, componentId, versionId);
  };

  const { data, isLoading, mutate } = useSwr(
    FETCH_KEY(projectId, componentId, versionId),
    fetcher, {
      shouldRetryOnError: false,
      onError: (err) => {
        showErrorNotification({
          header: i18n.fetchComponentVersionTestError,
          content: err.message
        });
      }
    }
  );

  function loadTestExecutions() {
    cache.delete(`components/${componentId}/versions/${versionId}/test-executions`);
    mutate(undefined);
  }

  const downloadLogs = () => {
    if (selectedTestExecution) {
      setDownloadLogsInProgress(true);
      serviceApi.getComponentVersionTestExecutionLogsUrl(
        projectId,
        componentId,
        versionId,
        selectedTestExecution.testExecutionId,
        selectedTestExecution.instanceId
      )
        .then((response) => {
          const fileName = `${selectedTestExecution.testExecutionId}_${selectedTestExecution.instanceId}.log`;
          downloadFile(response.logsUrl, fileName)
            .catch(() => {
              showErrorNotification({
                header: i18n.fetchTestLogsErrorHeader,
                content: i18n.fetchTestLogsErrorContent
              });
            }).finally(() => {
              setDownloadLogsInProgress(false);
            });
        })
        .catch(() => {
          showErrorNotification({
            header: i18n.fetchTestLogsErrorHeader,
            content: i18n.fetchTestLogsErrorContent
          });
          setDownloadLogsInProgress(false);
        });

    }
  };

  return {
    testExecutions: data?.componentVersionTestExecutionSummaries || [],
    testExecutionsLoading: isLoading,
    loadTestExecutions,
    selectedTestExecution,
    setSelectedTestExecution,
    downloadLogs,
    downloadLogsInProgress
  };
}