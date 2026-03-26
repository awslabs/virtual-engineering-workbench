import {
  RecipeVersion,
  GetRecipeVersionsResponse
} from '../../../../../services/API/proserve-wb-packaging-api';
import useSwr, { useSWRConfig } from 'swr';
import { useNotifications } from '../../../../layout';
import { selectedProjectState } from '../../../../../state';
import { useRecoilValue } from 'recoil';
import { useState } from 'react';
import { i18n } from './view-recipe.translations';
import { RouteNames } from '../../../../layout/navigation/navigation.static';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic';
import { extractErrorResponseMessage } from '../../../../../utils/api-helpers';

interface ServiceAPI {
  getRecipeVersions: (projectId: string, recipeId: string) => Promise<GetRecipeVersionsResponse>,
  releaseRecipeVersion: (projectId: string, recipeId: string, versionId: string) => Promise<object>,
  retireRecipeVersion: (projectId: string, recipeId: string, versionId: string) => Promise<object>,
}

interface Props {
  serviceApi: ServiceAPI,
  projectId?: string,
  recipeId?: string,
}

const FETCH_KEY = (
  projectId?: string,
  recipeId?: string,
) => {
  if (!projectId || !recipeId) {
    return null;
  }
  return [
    `recipes/${recipeId}/versions`,
    projectId,
    recipeId,
  ];
};

export function useRecipeVersions({ serviceApi, recipeId }: Props) {
  const [selectedRecipeVersion, setSelectedRecipeVersion] = useState<RecipeVersion>();
  const [isReleaseRecipeVersionModalOpen, setIsReleaseRecipeVersionModalOpen] = useState(false);
  const [isReleaseInProgress, setIsReleaseInProgress] = useState(false);
  const [isRetireRecipeVersionModalOpen, setIsRetireRecipeVersionModalOpen] = useState(false);
  const [isRetireInProgress, setIsRetireInProgress] = useState(false);

  const selectedProject = useRecoilValue(selectedProjectState);

  const { showErrorNotification, showSuccessNotification } = useNotifications();
  const { navigateTo } = useNavigationPaths();

  const { cache } = useSWRConfig();

  const fetcher = ([
    ,
    projectId,
    recipeId,
  ]: [
    url: string,
    projectId: string,
    recipeId: string,
  ]) => {
    return serviceApi.getRecipeVersions(projectId, recipeId);
  };

  const { data, isLoading, mutate } = useSwr(
    FETCH_KEY(selectedProject.projectId, recipeId),
    fetcher, {
      shouldRetryOnError: false,
      onError: (err) => {
        showErrorNotification({
          header: i18n.fetchRecipeVersionsError,
          content: err.message
        });
      }
    }
  );
  return {
    recipeVersions: data?.recipeVersions || [],
    recipeVersionsLoading: isLoading,
    loadRecipeVersions,
    setSelectedRecipeVersion,
    selectedRecipeVersion,
    updateRecipeVersion: navigateToUpdateRecipeVersion,
    isReleaseRecipeVersionModalOpen,
    setIsReleaseRecipeVersionModalOpen,
    releaseRecipeVersion,
    isReleaseInProgress,
    viewRecipeVersion: navigateToViewRecipeVersion,
    isRetireRecipeVersionModalOpen,
    setIsRetireRecipeVersionModalOpen,
    retireRecipeVersion,
    isRetireInProgress,
  };

  function navigateToUpdateRecipeVersion() {
    navigateTo(RouteNames.UpdateRecipeVersion, {
      ':recipeId': recipeId,
      ':versionId': selectedRecipeVersion?.recipeVersionId,
    });
  }

  function navigateToViewRecipeVersion() {
    navigateTo(RouteNames.ViewRecipeVersion, {
      ':recipeId': recipeId,
      ':versionId': selectedRecipeVersion?.recipeVersionId,
    });
  }

  function loadRecipeVersions() {
    cache.delete(`recipes/${recipeId}/versions`);
    mutate(undefined);
  }

  function releaseRecipeVersion() {
    if (selectedProject?.projectId && recipeId && selectedRecipeVersion?.recipeVersionId) {
      setIsReleaseInProgress(true);
      serviceApi.releaseRecipeVersion(
        selectedProject.projectId,
        recipeId,
        selectedRecipeVersion?.recipeVersionId
      ).
        then(() => {
          showSuccessNotification({
            header: i18n.releaseRecipeVersionSuccessMessageHeader,
            content: i18n.releaseRecipeVersionSuccessMessageContent
          });
          loadRecipeVersions();
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
    if (selectedProject?.projectId && recipeId && selectedRecipeVersion?.recipeVersionId) {
      setIsRetireInProgress(true);
      serviceApi.retireRecipeVersion(
        selectedProject.projectId,
        recipeId,
        selectedRecipeVersion?.recipeVersionId
      ).
        then(() => {
          showSuccessNotification({
            header: i18n.retireRecipeVersionSuccessMessageHeader,
            content: i18n.retireRecipeVersionSuccessMessageContent
          });
          loadRecipeVersions();
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