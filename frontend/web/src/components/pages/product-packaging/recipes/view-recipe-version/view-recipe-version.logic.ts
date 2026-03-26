import {
  GetRecipeVersionResponse,
} from '../../../../../services/API/proserve-wb-packaging-api';
import useSwr, { useSWRConfig } from 'swr';
import { useNotifications } from '../../../../layout';
import { useState } from 'react';
import { i18n } from './view-recipe-version.translations';
import { extractErrorResponseMessage } from '../../../../../utils/api-helpers';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../../../layout/navigation/navigation.static';

interface ServiceAPI {
  getRecipeVersion: (projectId: string, recipeId: string, versionId: string)
  => Promise<GetRecipeVersionResponse>,
  releaseRecipeVersion: (projectId: string, recipeId: string, versionId: string) => Promise<object>,
  retireRecipeVersion: (projectId: string, recipeId: string, versionId: string) => Promise<object>,
}

interface Props {
  serviceApi: ServiceAPI,
  projectId?: string,
  recipeId?: string,
  versionId?: string,
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
    `recipes/${recipeId}/versions/${versionId}`,
    projectId,
    recipeId,
    versionId
  ];
};

export function useViewRecipeVersion({ serviceApi, projectId, recipeId, versionId }: Props) {
  const { navigateTo } = useNavigationPaths();
  const [isReleaseRecipeVersionModalOpen, setIsReleaseRecipeVersionModalOpen] = useState(false);
  const [isReleaseInProgress, setIsReleaseInProgress] = useState(false);
  const [isRetireRecipeVersionModalOpen, setIsRetireRecipeVersionModalOpen] = useState(false);
  const [isRetireInProgress, setIsRetireInProgress] = useState(false);
  const { showSuccessNotification, showErrorNotification } = useNotifications();
  const { cache } = useSWRConfig();
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
    return serviceApi.getRecipeVersion(projectId, recipeId, versionId);
  };

  const { data, isLoading, mutate } = useSwr(
    FETCH_KEY(projectId, recipeId, versionId),
    fetcher, {
      shouldRetryOnError: false,
      onError: (err) => {
        showErrorNotification({
          header: i18n.fetchRecipeVersionError,
          content: err.message
        });
      }
    }
  );

  function loadRecipeVersion() {
    cache.delete(`recipes/${recipeId}/versions/${versionId}`);
    mutate();
  }

  function navigateToViewRecipe() {
    navigateTo(RouteNames.ViewRecipe, {
      ':recipeId': recipeId
    });
  }

  function navigateToUpdateRecipeVersion() {
    navigateTo(RouteNames.UpdateRecipeVersion, {
      ':recipeId': recipeId,
      ':versionId': versionId,
    });
  }

  return {
    recipeVersion: data?.recipeVersion,
    recipeVersionLoading: isLoading,
    isReleaseRecipeVersionModalOpen,
    setIsReleaseRecipeVersionModalOpen,
    releaseRecipeVersion,
    isReleaseInProgress,
    viewRecipe: navigateToViewRecipe,
    updateRecipeVersion: navigateToUpdateRecipeVersion,
    isRetireRecipeVersionModalOpen,
    setIsRetireRecipeVersionModalOpen,
    retireRecipeVersion,
    isRetireInProgress,
  };

  function releaseRecipeVersion() {
    if (projectId && recipeId && data?.recipeVersion?.recipeVersionId) {
      setIsReleaseInProgress(true);
      serviceApi.releaseRecipeVersion(
        projectId,
        recipeId,
        data?.recipeVersion?.recipeVersionId
      ).
        then(() => {
          showSuccessNotification({
            header: i18n.releaseRecipeVersionSuccessMessageHeader,
            content: i18n.releaseRecipeVersionSuccessMessageContent
          });
          loadRecipeVersion();
          setIsReleaseRecipeVersionModalOpen(false);
        }).catch(async e => {
          showErrorNotification({
            header: i18n.releaseRecipeVersionFailedMessageHeader,
            content: await extractErrorResponseMessage(e)
          });
        }).finally(() => setIsReleaseInProgress(false));
    }
  }

  function retireRecipeVersion() {
    if (projectId && recipeId && data?.recipeVersion?.recipeVersionId) {
      setIsRetireInProgress(true);
      serviceApi.retireRecipeVersion(
        projectId,
        recipeId,
        data?.recipeVersion?.recipeVersionId
      ).
        then(() => {
          showSuccessNotification({
            header: i18n.retireRecipeVersionSuccessMessageHeader,
            content: i18n.retireRecipeVersionSuccessMessageContent
          });
          loadRecipeVersion();
          setIsRetireRecipeVersionModalOpen(false);
        }).catch(async e => {
          showErrorNotification({
            header: i18n.retireRecipeVersionFailedMessageHeader,
            content: await extractErrorResponseMessage(e)
          });
        }).finally(() => setIsRetireInProgress(false));
    }
  }
}