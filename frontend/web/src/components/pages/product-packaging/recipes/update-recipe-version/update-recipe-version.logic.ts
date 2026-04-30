import {
  GetRecipeVersionResponse,
  RecipeComponentVersion,
  RecipeVersion,
} from '../../../../../services/API/proserve-wb-packaging-api';
import { useNotifications } from '../../../../layout';
import { useState, useEffect, useMemo } from 'react';
import { i18n } from './update-recipe-version.translations';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../../../layout/navigation/navigation.static';
import { extractErrorResponseMessage } from '../../../../../utils/api-helpers';
import useSwr from 'swr';
import { useRecipe } from '../view-recipe/view-recipe.logic';
import { packagingAPI } from '../../../../../services';
import { useViewMandatoryComponentsList }
  from '../../mandatory-components-lists/view-mandatory-components-list/view-mandatory-components-list.logic';

interface Props {
  recipeId: string,
  recipeVersionId: string,
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
interface RecipeComponent {
  componentId: string,
  componentVersionType?: string,
  componentVersionName?: string,
  componentName?: string,
  componentVersionId?: string,
  order?: number,
}

const FETCH_KEY = (
  projectId?: string,
  recipeId?: string,
  recipeVersionId?: string,
) => {
  if (!projectId || !recipeId || !recipeVersionId) {
    return null;
  }
  return [
    `recipes/${recipeId}/versions/${recipeVersionId}`,
    projectId,
    recipeId,
    recipeVersionId,
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
// eslint-disable-next-line complexity
const handleRecipeData = (
  data: GetRecipeVersionResponse | undefined,
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
  const recipeComponentsVersion: RecipeComponent[] = (data?.recipeVersion.recipeComponentsVersions || [])
    .filter((component: RecipeComponent) => !mandatoryComponentIds.includes(component.componentId))
    .map((component: RecipeComponent, index: number) => ({
      ...component,
      order: index + INITIAL_ORDER_OFFSET,
    }));
  const recipeVersion: RecipeVersion = {
    ...data?.recipeVersion,
    recipeComponentsVersions: recipeComponentsVersion,
  } as RecipeVersion;
  const recipeComponents = getRecipeComponents(recipeVersion);
  return {
    recipeVersionMandatories,
    recipeVersion,
    recipeComponents,
  };
};

export const useUpdateRecipeVersion = ({
  recipeId,
  recipeVersionId,
  projectId,
}: Props) => {
  const serviceApi = packagingAPI;
  const [updateRecipeVersionInProgress, setUpdateRecipeVersionInProgress] =
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
    return serviceApi.getRecipeVersion(projectId, recipeId, recipeVersionId);
  };

  const { data, isLoading } = useSwr(
    FETCH_KEY(projectId, recipeId, recipeVersionId),
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

  function updateRecipeVersion(
    recipeVersionDescription: string,
    recipeComponentsVersions: RecipeComponentVersion[],
    recipeVersionVolumeSize: string,
    versionReleaseType?: string,
    integrations?: string[],
  ) {
    if (projectId && recipeId && recipeVersionId) {
      setUpdateRecipeVersionInProgress(true);

      serviceApi.updateRecipeVersion(
        projectId,
        recipeId,
        recipeVersionId,
        {
          recipeVersionDescription,
          recipeComponentsVersions,
          recipeVersionVolumeSize,
          recipeVersionIntegrations: integrations,
        }
      ).then(() => {
        showSuccessNotification({
          header: i18n.updateSuccessMessageHeader,
          content: i18n.updateSuccessMessageContent
        });
        navigateTo(RouteNames.ViewRecipe, { ':recipeId': recipeId });
      }).catch(async e => {
        showErrorNotification({
          header: i18n.updateFailMessageHeader,
          content: await extractErrorResponseMessage(e)
        });
      }).finally(() => setUpdateRecipeVersionInProgress(false));
    }
  }

  return {
    projectId,
    recipeVersion,
    isRecipeVersionLoading: isLoading,
    updateRecipeVersion,
    updateRecipeVersionInProgress,
    recipeVersionMandatories,
    recipeComponents,
  };
};