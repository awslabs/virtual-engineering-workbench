import {
  RecipeVersionTestExecutionSummary,
  GetRecipeVersionTestExecutionsResponse,
  GetRecipeVersionTestExecutionLogsUrlResponse
} from '../../../../../services/API/proserve-wb-packaging-api';
import useSwr, { useSWRConfig } from 'swr';
import { useNotifications } from '../../../../layout';
import { useState } from 'react';
import { i18n } from './view-recipe-version.translations';
import { downloadFile } from '../../../../../utils/download-file';

interface ServiceAPI {
  getRecipeVersionTestExecutions: (projectId: string, recipeId: string, versionId: string)
  => Promise<GetRecipeVersionTestExecutionsResponse>,
  getRecipeVersionTestExecutionLogsUrl: (
    projectId: string,
    recipeId: string,
    versionId: string,
    testExecutionId: string,
  )=> Promise<GetRecipeVersionTestExecutionLogsUrlResponse>,
}

interface Props {
  serviceApi: ServiceAPI,
  projectId: string,
  recipeId: string,
  versionId: string,
}

const FETCH_KEY = (
  projectId?: string,
  recipeId?: string,
  versionId?: string
) => {
  if (!projectId || !recipeId) {
    return null;
  }
  return [
    `recipes/${recipeId}/versions/${versionId}/test-executions`,
    projectId,
    recipeId,
    versionId
  ];
};


export function useViewRecipeVersionTests({ serviceApi, projectId, recipeId, versionId }: Props) {
  const [selectedTestExecution, setSelectedTestExecution]
    = useState<RecipeVersionTestExecutionSummary>();
  const { showErrorNotification } = useNotifications();
  const { cache } = useSWRConfig();
  const [downloadLogsInProgress, setDownloadLogsInProgress] = useState(false);

  const fetcher = ([
    ,
    projectId,
    recipeId,
    versionId
  ]: [
    url: string,
    projectId: string,
    recipeId: string,
    versionId: string
  ]) => {
    return serviceApi.getRecipeVersionTestExecutions(projectId, recipeId, versionId);
  };

  const { data, isLoading, mutate } = useSwr(
    FETCH_KEY(projectId, recipeId, versionId),
    fetcher, {
      shouldRetryOnError: false,
      onError: (err) => {
        showErrorNotification({
          header: i18n.fetchRecipeVersionTestError,
          content: err.message
        });
      }
    }
  );

  function loadTestExecutions() {
    cache.delete(`recipes/${recipeId}/versions/${versionId}/test-executions`);
    mutate(undefined);
  }

  const downloadLogs = () => {
    if (selectedTestExecution) {
      setDownloadLogsInProgress(true);
      serviceApi.getRecipeVersionTestExecutionLogsUrl(
        projectId,
        recipeId,
        versionId,
        selectedTestExecution.testExecutionId,
      )
        .then((response) => {
          const fileName = `${selectedTestExecution.testExecutionId}.log`;
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
    testExecutions: data?.recipeVersionTestExecutionSummaries || [],
    testExecutionsLoading: isLoading,
    loadTestExecutions,
    selectedTestExecution,
    setSelectedTestExecution,
    downloadLogs,
    downloadLogsInProgress
  };
}