/* eslint-disable @typescript-eslint/no-magic-numbers */
/* eslint-disable complexity */
import {
  GetRecipeResponse,
  Recipe,
  RecipeComponentVersion,
  RecipeVersion,
  ComponentVersionEntry
} from '../../../../../../services/API/proserve-wb-packaging-api';
import { RECIPE_VERSION_RELEASE_TYPE_MAP } from '../recipe-version-release-type-map';
import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { WizardProps } from '@cloudscape-design/components';
import { useNotifications } from '../../../../../layout';
import { i18n } from './recipe-version-wizard.translations';
import useSwr from 'swr';
type GetIntegrationsResponse = { integrations?: Array<{ integrationId: string, name: string }> };

const STEP_1_INDEX = 1;
const STEP_2_INDEX = 2;
const MIN_RECIPE_COMPONENT_VERSIONS = 1;
const MAX_VOLUME_SIZE = 500;

interface ServiceAPI {
  getRecipe: (projectId: string, recipeId: string) => Promise<GetRecipeResponse>,
  getIntegrations?: (projectId: string) => Promise<GetIntegrationsResponse>,
  getIntegrationComponentList?: (
    projectId: string,
    integrationId: string,
    platform: string,
    architecture: string,
    osVersion: string
  ) => Promise<any>,
}

const FETCH_KEY = (
  projectId: string,
  recipeId: string,
) => {
  if (!projectId || !recipeId) {
    return null;
  }
  return [
    `recipes/${recipeId}`,
    projectId,
    recipeId,
  ];
};

const FETCH_INTEGRATIONS_KEY = (
  projectId: string,
) => {
  if (!projectId) {
    return null;
  }
  return [
    'integrations',
    projectId,
  ];
};

export const useRecipeVersionWizard = ({
  projectId,
  recipeId,
  recipeVersion,
  serviceApi,
  activeStepIndex,
  setActiveStepIndex
}: {
  projectId: string,
  recipeId: string,
  recipeVersion?: RecipeVersion,
  serviceApi: ServiceAPI,
  activeStepIndex: number,
  setActiveStepIndex: (step: number) => void,
}) => {

  const isUpdate = !!(recipeVersion && recipeVersion.recipeVersionId);
  const versionReleaseTypes = Object.keys(RECIPE_VERSION_RELEASE_TYPE_MAP);
  const [description, setDescription] = useState(recipeVersion?.recipeVersionDescription || '');

  const [isDescriptionValid, setIsDescriptionValid] = useState(true);
  const [volumeSize, setVolumeSize]
    = useState(parseInt(recipeVersion?.recipeVersionVolumeSize || '', 10) || 100);
  const [isVolumeSizeValid, setIsVolumeSizeValid] = useState(true);
  const [versionReleaseType, setVersionReleaseType] = useState(versionReleaseTypes[0]);
  const [isVersionReleaseTypeValid, setIsVersionReleaseTypeValid] = useState(true);
  const [
    recipeComponentsVersions,
    setRecipeComponentsVersions
  ] = useState<RecipeComponentVersion[]>([]);

  const [selectedIntegrations, setSelectedIntegrations] = useState<string[]>(
    recipeVersion?.recipeVersionIntegrations || []
  );

  useEffect(() => {
    if (recipeVersion?.recipeVersionDescription) {
      setDescription(recipeVersion.recipeVersionDescription);
    }
    if (recipeVersion?.recipeVersionVolumeSize) {
      setVolumeSize(parseInt(recipeVersion.recipeVersionVolumeSize, 10) || 100);
    }
    if (recipeVersion?.recipeVersionIntegrations) {
      setSelectedIntegrations(recipeVersion.recipeVersionIntegrations);
    }
  }, [recipeVersion]);
  const [integrationComponents, setIntegrationComponents] = useState<ComponentVersionEntry[]>([]);
  const [isLoadingIntegrationComponents, setIsLoadingIntegrationComponents] = useState(false);

  // Track all component IDs that have ever been integration components
  const allIntegrationComponentIds = useRef<Set<string>>(new Set());

  const initialRecipeComponentsVersions = useMemo(() => {
    const components = recipeVersion?.recipeComponentsVersions || [];
    const integrationComponentIds = new Set(
      integrationComponents.map(ic => ic.componentId)
    );
    return components.filter(comp =>
      !integrationComponentIds.has(comp.componentId)
    );
  }, [recipeVersion, integrationComponents]);

  useEffect(() => {
    setRecipeComponentsVersions(initialRecipeComponentsVersions);
  }, [initialRecipeComponentsVersions]);

  // Track integration component IDs and remove them from editable list
  useEffect(() => {
    // Add current integration component IDs to the tracking set
    integrationComponents.forEach(ic => {
      allIntegrationComponentIds.current.add(ic.componentId);
    });

    // Remove any tracked integration components from the editable list
    setRecipeComponentsVersions(prev =>
      prev.filter(comp => !allIntegrationComponentIds.current.has(comp.componentId))
    );
  }, [integrationComponents]);

  const updateRecipeComponentsVersions = useCallback((versions: RecipeComponentVersion[]) => {
    setRecipeComponentsVersions(versions);
  }, []);
  const [isRecipeComponentsVersionsValid, setIsRecipeComponentsVersionsValid] = useState(true);
  const [cancelConfirmVisible, setCancelConfirmVisible] = useState(false);

  const { showErrorNotification } = useNotifications();

  const fetcher = ([
    ,
    projectId,
    recipeId,
  ]: [
      url: string,
      projectId: string,
      recipeId: string,
  ]) => {
    return serviceApi.getRecipe(projectId, recipeId);
  };

  const integrationsFetcher = ([
    ,
    projectId,
  ]: [
      url: string,
      projectId: string,
  ]) => {
    if (!serviceApi.getIntegrations) {
      return Promise.resolve({ integrations: [] });
    }
    return serviceApi.getIntegrations(projectId);
  };

  const { data, isLoading } = useSwr(
    FETCH_KEY(projectId, recipeId),
    fetcher, {
      shouldRetryOnError: false,
      onError: (err) => {
        showErrorNotification({
          header: i18n.fetchRecipeError,
          content: err.message
        });
      }
    }
  );

  const { data: integrations, isLoading: isIntegrationsLoading } = useSwr(
    FETCH_INTEGRATIONS_KEY(projectId),
    integrationsFetcher, {
      shouldRetryOnError: false,
      onError: (err) => {
        showErrorNotification({
          header: 'Error fetching integrations',
          content: err.message
        });
      }
    }
  );

  useEffect(() => {
    const fetchIntegrationComponents = async () => {
      if (!selectedIntegrations.length || !data?.recipe) {
        setIntegrationComponents([]);
        setIsLoadingIntegrationComponents(false);
        return;
      }

      setIsLoadingIntegrationComponents(true);
      try {
        const promises = selectedIntegrations.map(integrationId =>
          serviceApi.getIntegrationComponentList?.(
            projectId,
            integrationId,
            data.recipe.recipePlatform,
            data.recipe.recipeArchitecture,
            data.recipe.recipeOsVersion
          ) ?? Promise.resolve(undefined)
        );

        const responses = await Promise.all(promises);
        const allComponents: ComponentVersionEntry[] = [];

        for (const response of responses) {
          if (response?.componentsList?.components) {
            allComponents.push(...response.componentsList.components);
          }
        }

        setIntegrationComponents(allComponents);
      } catch (err: any) {
        showErrorNotification({
          header: 'Error fetching integration components',
          content: err.message
        });
        setIntegrationComponents([]);
      } finally {
        setIsLoadingIntegrationComponents(false);
      }
    };

    fetchIntegrationComponents();
  }, [
    selectedIntegrations,
    data?.recipe?.recipePlatform,
    data?.recipe?.recipeOsVersion,
    data?.recipe?.recipeArchitecture,
    projectId
  ]);

  const minVolumeSize = data?.recipe?.recipePlatform === 'Windows' ? 30 : 8;

  function isStep1Valid() {
    setIsDescriptionValid(!!description);
    setIsVersionReleaseTypeValid(isUpdate || !!versionReleaseType);
    setIsVolumeSizeValid(volumeSize >= minVolumeSize && volumeSize <= MAX_VOLUME_SIZE);
    return !!description.trim()
      && (isUpdate || !!versionReleaseType)
      && (volumeSize >= minVolumeSize && volumeSize <= MAX_VOLUME_SIZE);
  }

  function isRecipeComponentsVersionValid(items: RecipeComponentVersion[]) {
    for (const item of items) {
      if (!item.componentId || !item.componentVersionId) {
        setIsRecipeComponentsVersionsValid(false);
        return false;
      }
    }
    setIsRecipeComponentsVersionsValid(true);
    return true;
  }

  function isStep2Valid(items: RecipeComponentVersion[]) {
    return (
      items.length >= MIN_RECIPE_COMPONENT_VERSIONS &&
      isRecipeComponentsVersionValid(items)
    );
  }

  function isStepValid(index: number) {
    if (index === STEP_1_INDEX) {
      return isStep1Valid();
    }

    if (index === STEP_2_INDEX) {
      return isStep2Valid(recipeComponentsVersions || []);
    }
    return true;
  }

  function requiresValidation(reason: string) {
    return reason === 'next';
  }

  const handleOnNavigate = useCallback((detail: WizardProps.NavigateDetail) => {
    if (requiresValidation(detail.reason) && !isStepValid(detail.requestedStepIndex)) {
      return;
    }
    setActiveStepIndex(detail.requestedStepIndex);
  }, [requiresValidation, isStepValid, setActiveStepIndex]);

  return {
    recipe: data?.recipe || {} as Recipe,
    isRecipeLoading: isLoading,
    isUpdate,
    activeStepIndex,
    description,
    setDescription,
    isDescriptionValid,
    volumeSize,
    setVolumeSize,
    isVolumeSizeValid,
    versionReleaseTypes,
    versionReleaseType,
    setVersionReleaseType,
    isVersionReleaseTypeValid,
    recipeComponentsVersions,
    setRecipeComponentsVersions,
    isRecipeComponentsVersionsValid,
    handleOnNavigate,
    cancelConfirmVisible,
    setCancelConfirmVisible,
    setActiveStepIndex,
    minRecipeComponentsVersions: MIN_RECIPE_COMPONENT_VERSIONS,
    minVolumeSize,
    maxVolumeSize: MAX_VOLUME_SIZE,
    updateRecipeComponentsVersions,
    integrations: integrations?.integrations || [],
    isIntegrationsLoading,
    selectedIntegrations,
    setSelectedIntegrations,
    integrationComponents,
    isLoadingIntegrationComponents,
  };
};
