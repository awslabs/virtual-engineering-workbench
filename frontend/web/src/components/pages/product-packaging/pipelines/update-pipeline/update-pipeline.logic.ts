import { useEffect, useState } from 'react';
import { useNotifications } from '../../../../layout';
import { extractErrorResponseMessage } from '../../../../../utils/api-helpers';
import { RouteNames } from '../../../../layout/navigation/navigation.static';
import { i18n } from './update-pipeline.translations';
import {
  Pipeline,
  UpdatePipelineRequest,
  GetPipelineResponse
} from '../../../../../services/API/proserve-wb-packaging-api';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic';
import useSwr from 'swr';

interface ServiceAPI {
  getPipeline: (
    projectId: string,
    pipelineId: string,
  ) => Promise<GetPipelineResponse>,
  updatePipeline: (
    projectId: string,
    pipelineId: string,
    body: UpdatePipelineRequest,
  )=> Promise<object>,
}

const FETCH_KEY = (
  projectId: string,
  pipelineId: string,
) => {
  if (!projectId || !pipelineId) {
    return null;
  }
  return [
    `projects/${projectId}/pipelines/${pipelineId}`,
    projectId,
    pipelineId,
  ];
};

type UpdatePipelineProps = {
  projectId: string,
  pipelineId: string,
  serviceApi: ServiceAPI,
};

export const useUpdatePipeline = ({ projectId, pipelineId, serviceApi }: UpdatePipelineProps) => {

  const { showErrorNotification, showSuccessNotification } = useNotifications();
  const [pipeline, setPipeline] = useState<Pipeline>({} as Pipeline);
  const [isUpdateInProgress, setIsUpdateInProgress] = useState(false);
  const { navigateTo } = useNavigationPaths();

  const fetcher = ([
    ,
    projectId,
    pipelineId,
  ]: [
      url: string,
      projectId: string,
      pipelineId: string,
  ]) => {
    return serviceApi.getPipeline(
      projectId,
      pipelineId
    );
  };

  const { data, isLoading } = useSwr(
    FETCH_KEY(
      projectId,
      pipelineId,
    ),
    fetcher, {
      shouldRetryOnError: false,
      onError: (err) => {
        showErrorNotification({
          header: i18n.fetchPipelineError,
          content: err.message
        });
      }
    }
  );

  useEffect(()=>{
    if (data && !isLoading) {
      setPipeline(data?.pipeline);
    }
  }, [data, isLoading]);

  function updatePipeline() {
    setIsUpdateInProgress(true);
    serviceApi.updatePipeline(projectId,
      pipeline.pipelineId,
      {
        pipelineSchedule: pipeline.pipelineSchedule,
        buildInstanceTypes: pipeline.buildInstanceTypes,
        recipeVersionId: pipeline.recipeVersionId,
        pipelineId: pipeline.pipelineId,
        productId: pipeline.productId ?? '',
      }).then(() => {
      showSuccessNotification({
        header: i18n.updateSuccessMessageHeader,
        content: i18n.updateSuccessMessageContent
      });
      navigateTo(RouteNames.Pipelines);
    }).catch(async e => {
      showErrorNotification({
        header: i18n.updateFailMessageHeader,
        content: await extractErrorResponseMessage(e)
      });
    }).finally(() => {
      setIsUpdateInProgress(false);
    });
  }

  return {
    pipeline,
    setPipeline,
    isPipelineLoading: isLoading,
    isUpdateInProgress,
    updatePipeline,
  };
};