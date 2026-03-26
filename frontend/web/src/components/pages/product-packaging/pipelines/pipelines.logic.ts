import { selectedProjectState } from '../../../../state';
import { useRecoilValue } from 'recoil';
import { useNotifications } from '../../../layout';
import { i18n } from './pipelines.translations';
import useSWR, { useSWRConfig } from 'swr';
import { useNavigationPaths } from '../../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../../layout/navigation/navigation.static';
import { useState } from 'react';
import {
  CreateImageRequest,
  GetPipelinesResponse,
  Pipeline,
} from '../../../../services/API/proserve-wb-packaging-api';
import { extractErrorResponseMessage } from '../../../../utils/api-helpers';

interface ServiceAPI {
  getPipelines: (projectId: string,) => Promise<GetPipelinesResponse>,
  retirePipeline: (projectId: string, pipelineId: string) => Promise<object>,
  createImage: (projectId: string, body: CreateImageRequest)=> Promise<object>,
}

const PIPELINE_FETCH_KEY = (projectId?: string,) => {
  if (!projectId) {
    return null;
  }
  return [
    `projects/${projectId}/pipelines`,
    projectId,
  ];
};

export const usePipelines = ({ serviceApi }:{ serviceApi: ServiceAPI }) => {
  const { showErrorNotification, showSuccessNotification } = useNotifications();
  const { navigateTo } = useNavigationPaths();
  const { cache } = useSWRConfig();
  const [selectedPipeline, setSelectedPipeline] = useState<Pipeline>();
  const [isRetirePipelineModalOpen, setIsRetirePipelineModalOpen] = useState(false);
  const [isRetireInProgress, setIsRetireInProgress] = useState(false);
  const [isCreateImageModalOpen, setIsCreateImageModalOpen] = useState(false);
  const [isCreateImageInProgress, setIsCreateImageInProgress] = useState(false);

  const selectedProject = useRecoilValue(selectedProjectState);

  const FETCHER = ([, projectId, ]: [url: string, projectId: string]) => {
    return serviceApi.getPipelines(projectId);
  };

  const { data, isLoading, mutate } = useSWR(
    PIPELINE_FETCH_KEY(selectedProject.projectId),
    FETCHER,
    {
      shouldRetryOnError: false,
      onError: (err) => {
        showErrorNotification({
          header: i18n.pipelinesFetchErrorTitle,
          content: err.message,
        });
      }
    }
  );

  const fetchData = () => {
    cache.delete(`projects/${selectedProject.projectId}/pipelines`);
    mutate(undefined);
  };

  function navigateToUpdatePipeline() {
    navigateTo(RouteNames.UpdatePipeline, {
      ':pipelineId': selectedPipeline?.pipelineId,
    });
  }

  function retirePipeline() {
    if (selectedProject?.projectId && selectedPipeline?.pipelineId) {
      setIsRetireInProgress(true);
      serviceApi.retirePipeline(
        selectedProject.projectId,
        selectedPipeline?.pipelineId
      ).
        then(() => {
          showSuccessNotification({
            header: i18n.retirePipelineSuccessMessageHeader,
            content: i18n.retirePipelineSuccessMessageContent
          });
          fetchData();
          setIsRetirePipelineModalOpen(false);
        }).catch(async e => {
          showErrorNotification({
            header: i18n.retirePipelineFailedMessageHeader,
            content: await extractErrorResponseMessage(e)
          });
        }).finally(() => setIsRetireInProgress(false));
    }
  }

  function createImage() {
    if (selectedProject?.projectId && selectedPipeline?.pipelineId) {
      setIsCreateImageInProgress(true);
      serviceApi.createImage(
        selectedProject.projectId,
        { pipelineId: selectedPipeline?.pipelineId }
      ).
        then(() => {
          showSuccessNotification({
            header: i18n.createImageSuccessMessageHeader,
            content: i18n.createImageSuccessMessageContent
          });
          setIsCreateImageModalOpen(false);
          navigateTo(RouteNames.Images);
        }).catch(async e => {
          showErrorNotification({
            header: i18n.createImageFailedMessageHeader,
            content: await extractErrorResponseMessage(e)
          });
        }).finally(() => setIsCreateImageInProgress(false));
    }
  }

  return {
    pipelines: data?.pipelines || [],
    isLoading,
    loadPipelines: fetchData,
    updatePipeline: navigateToUpdatePipeline,
    setSelectedPipeline,
    isRetirePipelineModalOpen,
    setIsRetirePipelineModalOpen,
    isRetireInProgress,
    retirePipeline,
    isCreateImageModalOpen,
    setIsCreateImageModalOpen,
    isCreateImageInProgress,
    createImage,
  };
};

