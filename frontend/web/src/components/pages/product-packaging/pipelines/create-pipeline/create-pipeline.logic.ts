import { useState } from 'react';
import { useNotifications } from '../../../../layout';
import { packagingAPI } from '../../../../../services/API/packaging-api';
import { extractErrorResponseMessage } from '../../../../../utils/api-helpers';
import { RouteNames } from '../../../../layout/navigation/navigation.static';
import { i18n } from './create-pipeline.translations';
import { Pipeline } from '../../../../../services/API/proserve-wb-packaging-api';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic';

type CreatePipelineProps = {
  projectId: string,
};

export const useCreatePipeline = ({ projectId }: CreatePipelineProps) => {

  const { showErrorNotification, showSuccessNotification } = useNotifications();
  const [pipeline, setPipeline] = useState<Pipeline>({} as Pipeline);
  const [isCreateInProgress, setIsCreateInProgress] = useState(false);
  const { navigateTo } = useNavigationPaths();

  function createPipeline() {
    setIsCreateInProgress(true);
    packagingAPI.createPipeline(projectId, {
      pipelineName: pipeline.pipelineName,
      pipelineDescription: pipeline.pipelineDescription,
      pipelineSchedule: pipeline.pipelineSchedule,
      buildInstanceTypes: pipeline.buildInstanceTypes,
      recipeId: pipeline.recipeId,
      recipeVersionId: pipeline.recipeVersionId,
      productId: pipeline.productId,
    }).then(() => {
      showSuccessNotification({
        header: i18n.createSuccessMessageHeader,
        content: i18n.createSuccessMessageContent
      });
      navigateTo(RouteNames.Pipelines);
    }).catch(async e => {
      showErrorNotification({
        header: i18n.createFailMessageHeader,
        content: await extractErrorResponseMessage(e)
      });
    }).finally(() => {
      setIsCreateInProgress(false);
    });
  }

  return {
    pipeline,
    setPipeline,
    isCreateInProgress,
    createPipeline,
  };
};