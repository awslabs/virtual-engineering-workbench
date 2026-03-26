import { packagingAPI } from '../../../../services/API/packaging-api';
import { selectedProjectState } from '../../../../state';
import { useRecoilValue } from 'recoil';
import { useNotifications } from '../../../layout';
import { i18n } from './recipes.translations';
import useSWR, { useSWRConfig } from 'swr';
import { RECIPE_STATUS_MAP } from './recipes-status';
import { RecipeState } from './recipe.static';
import { SelectProps } from '@cloudscape-design/components';
import { useState } from 'react';
import { Recipe } from '../../../../services/API/proserve-wb-packaging-api';


const FETCHER = ([, projectId, ]: [url: string, projectId: string]) => {
  return packagingAPI.getRecipes(projectId);
};

const RECIPE_FETCH_KEY = (projectId?: string,) => {
  if (!projectId) {
    return null;
  }
  return [
    `projects/${projectId}/recipes`,
    projectId,
  ];
};

export const useRecipes = () => {
  const { cache } = useSWRConfig();
  const { showErrorNotification } = useNotifications();
  const selectedProject = useRecoilValue(selectedProjectState);
  const statusFirstOption = {
    value: i18n.statusFirstOptionValue,
    label: RECIPE_STATUS_MAP[('CREATED') as RecipeState],
  };
  const [status, setStatus] = useState<SelectProps.Option>(statusFirstOption);

  const { data, isLoading, mutate } = useSWR(
    RECIPE_FETCH_KEY(selectedProject.projectId),
    FETCHER,
    {
      shouldRetryOnError: false,
      onError: (err) => {
        showErrorNotification({
          header: i18n.recipesFetchErrorTitle,
          content: err.message,
        });
      }
    }
  );

  const fetchData = () => {
    cache.delete(`projects/${selectedProject.projectId}/recipes`);
    mutate(undefined);
  };

  const filteredConfigurations: Recipe[] = data ?
    data.recipes.filter(recipe => recipe.status === status?.value) : [];
  const statuses = data?.recipes.map(recipe => {
    return recipe.status;
  });
  const statusOptions = [...new Set(statuses)].map((status) => {
    return {
      value: status,
      label: RECIPE_STATUS_MAP[(status || 'UNKNOWN') as RecipeState]
    } as SelectProps.Option;
  });

  return {
    recipes: filteredConfigurations || [],
    isLoading,
    loadRecipes: fetchData,
    setStatus,
    status,
    statusFirstOption,
    statusOptions,
  };
};

