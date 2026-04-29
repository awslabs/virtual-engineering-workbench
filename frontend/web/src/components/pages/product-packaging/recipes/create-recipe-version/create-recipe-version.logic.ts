import {
  GetRecipeVersionsResponse,
  RecipeComponentVersion,
  RecipeVersion,
} from '../../../../../services/API/proserve-wb-packaging-api';
import useSwr from 'swr';
import { useState, useEffect, useMemo } from 'react';
import { useNotifications } from '../../../../layout';
import { i18n } from './create-recipe-version.translations';
import { RouteNames } from '../../../../layout/navigation/navigation.static';
import { extractErrorResponseMessage } from '../../../../../utils/api-helpers';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic';
import { compare } from '../../../../../utils/semantic-versioning';
import { useRecipe } from '../view-recipe/view-recipe.logic';
import { packagingAPI } from '../../../../../services';
import { useViewMandatoryComponentsList }
  from '../../mandatory-components-lists/view-mandatory-components-list/view-mandatory-components-list.logic';

interface Props {
  recipeId: string,
  projectId: string,
}
interface ComponentVersionEntry {
  componentVersionType?: string,
  componentId: string,
  componentVersionName: string,
  componentName: string,
  componentVersionId: string,
  order?: number,
  position?: string,
}
interface RecipeData {
  recipeVersionMandatories: RecipeVersion,
  recipeVersion: RecipeVersion,
  recipeComponents: RecipeComponentVersion[],
}
interface LocalMandatoryComponentsList {
  prependedComponentsVersions: ComponentVersionEntry[],
  appendedComponentsVersions: ComponentVersionEntry[],
}
interface RecipeVersionData {
  status: string,
  recipeVersionName: string,
  recipeComponentsVersions: RecipeComponentVersion[],
  recipeVersionDescription?: string,
  recipeVersionVolumeSize?: string,
  recipeVersionIntegrations?: string[],
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
const INITIAL_ORDER_OFFSET = 1;
const convertToRecipeComponentVersion = (
  entry: ComponentVersionEntry,
  index: number
): RecipeComponentVersion => ({
  componentVersionType: entry.componentVersionType || 'HELPER',
  componentId: entry.componentId,
  componentVersionName: entry.componentVersionName,
  componentName: entry.componentName,
  componentVersionId: entry.componentVersionId,
  order: index + INITIAL_ORDER_OFFSET,
});
const getRecipeComponents = (recipeVersion: RecipeVersion | undefined): RecipeComponentVersion[] => {
  return recipeVersion?.recipeComponentsVersions || [];
};
/* eslint-disable complexity */
const handleRecipeData = (
  data: GetRecipeVersionsResponse | undefined,
  mandatoryComponentsList: LocalMandatoryComponentsList | undefined,
): RecipeData => {
  const prependedComponents = mandatoryComponentsList?.prependedComponentsVersions || [];
  const appendedComponents = mandatoryComponentsList?.appendedComponentsVersions || [];

  const allMandatoryComponents = [
    ...prependedComponents.map(c => ({ ...c, position: 'PREPEND' })),
    ...appendedComponents.map(c => ({ ...c, position: 'APPEND' }))
  ];

  const recipeVersionMandatories: RecipeVersion = {
    recipeComponentsVersions: allMandatoryComponents.map(
      (entry, index) => ({
        ...convertToRecipeComponentVersion(entry, index),
        position: entry.position
      } as any)
    )
  } as RecipeVersion;

  const mandatoryComponentIds = recipeVersionMandatories
    .recipeComponentsVersions?.map(c => c.componentId) || [];
  const latestReleasedVersion = (data?.recipeVersions as RecipeVersionData[])
    ?.filter((a) => a.status === 'RELEASED')
    ?.sort((a, b) => compare(a.recipeVersionName, b.recipeVersionName))?.[0];
  const recipeComponentsVersions: RecipeComponentVersion[] = latestReleasedVersion
    ?.recipeComponentsVersions
    ?.filter((component) => !mandatoryComponentIds.includes(component.componentId))
    ?.map((component, index) => ({
      ...component,
      order: index + INITIAL_ORDER_OFFSET,
    })) || [];
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { recipeVersionId, ...rest } = (latestReleasedVersion || {}) as any;
  const recipeVersion: RecipeVersion = {
    ...rest,
    recipeComponentsVersions: recipeComponentsVersions,
  } as RecipeVersion;
  const recipeComponents = getRecipeComponents(recipeVersion);

  return {
    recipeVersionMandatories,
    recipeVersion,
    recipeComponents,
  };
};
/* eslint-enable complexity */

export const useCreateRecipeVersion = ({
  recipeId,
  projectId,
}: Props) => {
  const serviceApi = packagingAPI;
  const [createRecipeVersionInProgress, setCreateRecipeVersionInProgress] =
    useState(false);
  const { showErrorNotification, showSuccessNotification } = useNotifications();
  const { navigateTo } = useNavigationPaths();

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

  const { data, isLoading } = useSwr(
    FETCH_KEY(projectId, recipeId),
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
  const [recipeVersion, setRecipeVersion] = useState<RecipeVersion | undefined>(undefined);
  const [recipeVersionMandatories, setRecipeVersionMandatories] = useState<
    RecipeVersion | undefined>(undefined);
  const { recipeResponse } = useRecipe({
    serviceApi,
    projectId,
    recipeId
  });
  const { mandatoryComponentsList } = useViewMandatoryComponentsList({
    serviceApi,
    projectId,
    platform: recipeResponse?.recipe?.recipePlatform || '',
    architecture: recipeResponse?.recipe?.recipeArchitecture || '',
    osVersion: recipeResponse?.recipe?.recipeOsVersion || '',
  });
  useEffect(() => {
    if (data && mandatoryComponentsList) {
      const {
        recipeVersionMandatories: mandatories,
        recipeVersion: version
      } = handleRecipeData(data, mandatoryComponentsList);
      setRecipeVersionMandatories(mandatories);
      setRecipeVersion(version);
    }
  }, [data, mandatoryComponentsList]);
  const recipeComponents = useMemo(() => {
    return recipeVersion ? getRecipeComponents(recipeVersion) : [];
  }, [recipeVersion]);

  function createRecipeVersion(
    recipeVersionDescription: string,
    recipeComponentsVersions: RecipeComponentVersion[],
    recipeVersionVolumeSize: string,
    recipeVersionReleaseType?: string,
    recipeVersionIntegrations?: string[],
  ) {
    if (projectId && recipeId) {
      setCreateRecipeVersionInProgress(true);
      serviceApi
        .createRecipeVersion(projectId, recipeId, {
          recipeVersionReleaseType: recipeVersionReleaseType || '',
          recipeVersionDescription,
          recipeComponentsVersions,
          recipeVersionVolumeSize,
          recipeVersionIntegrations,
        })
        .then(() => {
          showSuccessNotification({
            header: i18n.createSuccessMessageHeader,
            content: i18n.createSuccessMessageContent,
          });
          navigateTo(RouteNames.ViewRecipe, { ':recipeId': recipeId });
        })
        .catch(async (e) => {
          showErrorNotification({
            header: i18n.createFailMessageHeader,
            content: await extractErrorResponseMessage(e),
          });
        })
        .finally(() => setCreateRecipeVersionInProgress(false));
    }
  }

  return {
    createRecipeVersion,
    createRecipeVersionInProgress,
    recipeVersion,
    isRecipeVersionLoading: isLoading,
    recipeComponents,
    recipeVersionMandatories,
  };
};
