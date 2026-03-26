import { GetRecipeResponse } from '../../../../../services/API/proserve-wb-packaging-api';
import useSwr from 'swr';
import { useNotifications } from '../../../../layout';
import { i18n } from '../recipes.translations';
import { extractErrorResponseMessage } from '../../../../../utils/api-helpers';
import { useState } from 'react';

interface ServiceAPI {
  archiveRecipe: (
    projectId: string,
    recipeId: string,
  ) => Promise<object>,
  getRecipe: (
    projectId: string,
    recipeId: string
  ) => Promise<GetRecipeResponse>,
}

interface Props {
  serviceApi: ServiceAPI,
  projectId: string,
  recipeId: string,
}

const FETCH_KEY = (projectId?: string, recipeId?: string) => {
  if (!projectId || !recipeId) {
    return null;
  }
  return [`recipes/${recipeId}`, projectId, recipeId];
};

export function useRecipe({ serviceApi, projectId, recipeId }: Props) {
  const [archivingIsLoading, setArchivingIsLoading] = useState(false);
  const [archivePromptVisible, setArchivePromptVisible] = useState(false);
  const { showErrorNotification, showSuccessNotification } = useNotifications();

  const fetcher = ([, projectId, recipeId]: [
    url: string,
    projectId: string,
    recipeId: string
  ]) => {
    return serviceApi.getRecipe(projectId, recipeId);
  };

  const { data, isLoading } = useSwr(
    FETCH_KEY(projectId, recipeId),
    fetcher,
    {
      shouldRetryOnError: false,
      onError: (err) => {
        showErrorNotification({
          header: 'Unable to fetch recipe details',
          content: err.message,
        });
      },
    }
  );

  function archiveConfirmHandler() {
    setArchivingIsLoading(true);
    serviceApi
      .archiveRecipe(projectId, recipeId)
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

  return {
    recipeResponse: data,
    recipeLoading: isLoading,
    archiveConfirmHandler,
    archivePromptVisible,
    archivingIsLoading,
    setArchivePromptVisible
  };
}
