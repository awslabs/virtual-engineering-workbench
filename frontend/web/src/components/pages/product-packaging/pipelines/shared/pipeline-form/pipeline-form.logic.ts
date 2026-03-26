import { Dispatch, SetStateAction, useEffect, useState } from 'react';
import {
  GetPipelinesAllowedBuildTypesResponse,
  GetRecipesVersionsResponse,
  Pipeline,
  RecipeVersionSummary
} from '../../../../../../services/API/proserve-wb-packaging-api';
import cronstrue from 'cronstrue';
import useSwr from 'swr';
import { i18n } from './pipeline-form.translations';
import { useNotifications } from '../../../../../layout';
import { selectedProjectState } from '../../../../../../state';
import { useRecoilValue } from 'recoil';
import { MultiselectProps, SelectProps } from '@cloudscape-design/components';
import { publishingAPI } from '../../../../../../services';

const RECIPE_VERSION_STATUS_RELEASED = 'RELEASED';

interface ServiceAPI {
  getRecipesVersions: (
    projectId: string,
    status: string,
  ) => Promise<GetRecipesVersionsResponse>,
  getAllowedBuildTypes: (
    projectId: string,
    recipeId: string,
  ) => Promise<GetPipelinesAllowedBuildTypesResponse>,
}

const FETCH_KEY = (
  projectId: string,
  recipeStatus: string,
) => {
  if (!projectId) {
    return null;
  }
  return [
    `projects/${projectId}/${recipeStatus}`,
    projectId,
    recipeStatus,
  ];
};

const PIPELINE_NAME_REGEX = /^[-_A-Za-z-0-9][-_A-Za-z0-9 ]{1,126}[-_A-Za-z-0-9]$/u;
const PIPELINE_DESCRIPTION_REGEX = /^[A-Za-z0-9_ -]{0,100}$/u;

export const usePipelineForm = ({
  serviceAPI,
  pipeline,
  onSubmit,
}: {
  serviceAPI: ServiceAPI,
  pipeline: Pipeline,
  setPipeline: Dispatch<SetStateAction<Pipeline>>,
  onSubmit: () => void,
}) => {
  const { showErrorNotification } = useNotifications();
  const selectedProject = useRecoilValue(selectedProjectState);
  const [recipesVersions, setRecipeVersions] = useState<RecipeVersionSummary[]>();
  const [isRecipesVersionsValid, setIsRecipesVersionsValid] = useState(true);
  const [isPipelineValid, setIsPipelineValid] = useState(true);
  const [buildTypeOptions, setBuildTypeOptions] = useState<MultiselectProps.Options>([]);
  const [buildTypeOptionsLoading, setBuildTypeOptionsLoading] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [productOptions, setProductOptions] = useState<SelectProps.Options>([]);
  const [productOptionsLoading, setProductOptionsLoading] = useState(false);
  const isProductAssociationEnabled = false;
  const EMPTY = 0;

  const fetcher = ([
    ,
    projectId,
    recipeStatus,
  ]: [
      url: string,
      projectId: string,
      recipeStatus: string,
  ]) => {
    return serviceAPI.getRecipesVersions(
      projectId,
      recipeStatus,
    );
  };

  const { data, isLoading } = useSwr(
    FETCH_KEY(
      selectedProject.projectId || '',
      RECIPE_VERSION_STATUS_RELEASED,
    ),
    fetcher, {
      shouldRetryOnError: false,
      onError: (err) => {
        showErrorNotification({
          header: i18n.fetchRecipesVersionsError,
          content: err.message
        });
      }
    }
  );

  useEffect(() => {
    setRecipeVersions(data?.recipesVersionsSummary);
    setIsRecipesVersionsValid(
      // eslint-disable-next-line @typescript-eslint/no-magic-numbers
      !!data?.recipesVersionsSummary && data?.recipesVersionsSummary.length > 0
    );
  }, [data]);

  const getPipelineAllowedBuildTypes = () => {
    setBuildTypeOptionsLoading(true);
    serviceAPI.getAllowedBuildTypes(
      selectedProject.projectId || '',
      pipeline.recipeId
    ).then((response) => {
      setBuildTypeOptions(response?.pipelinesAllowedBuildTypes?.map((x) => ({ label: x, value: x })));
    }).catch((err) => {
      showErrorNotification({
        header: i18n.fetchBuildTypesError,
        content: err.message
      });
    }).finally(() => setBuildTypeOptionsLoading(false));
  };

  useEffect(() => {
    if (pipeline?.recipeId) {
      getPipelineAllowedBuildTypes();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pipeline.recipeId]);

  useEffect(() => {
    const loadProducts = async () => {
      setProductOptionsLoading(true);
      try {
        const response = await publishingAPI.getProducts(selectedProject.projectId || '');
        const createdProducts = response.products?.filter(product => product.status === 'CREATED') || [];
        const options = createdProducts.map(product => ({
          label: product.productName || '',
          value: product.productId || '',
          description: product.productDescription,
        }));
        setProductOptions(options);
      } catch (err) {
        showErrorNotification({
          header: i18n.fetchProductsError,
          content: (err as Error).message
        });
      } finally {
        setProductOptionsLoading(false);
      }
    };

    if (isProductAssociationEnabled && selectedProject.projectId) {
      loadProducts();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isProductAssociationEnabled, selectedProject.projectId]);

  const isUpdate = !!pipeline && !!pipeline.pipelineId;

  function getRecipesSelectOptions() {
    const recipes = [...new Set(recipesVersions?.map(item => item.recipeId))];
    return recipes.map((item) => ({
      label: recipesVersions?.find(x => x.recipeId === item)?.recipeName,
      value: item,
    }));
  }

  function getRecipeVersionsSelectOptions() {
    return recipesVersions
      ?.filter((item) => item.recipeId === pipeline.recipeId)
      ?.map((item) => ({
        label: item.recipeVersionName,
        value: item.recipeVersionId,
      }));
  }

  function isPipelineNameValid(): boolean {
    return !!pipeline.pipelineName
      && PIPELINE_NAME_REGEX.test(pipeline.pipelineName);
  }

  function isPipelineDescriptionValid(): boolean {
    return !!pipeline.pipelineDescription
      && PIPELINE_DESCRIPTION_REGEX.test(pipeline.pipelineDescription?.trim());
  }

  function isPipelineScheduleValid() {
    try {
      cronstrue.toString(pipeline.pipelineSchedule);
      return true;
    } catch {
      return false;
    }
  }

  function isPipelineBuildTypesValid(): boolean {
    return pipeline.buildInstanceTypes && pipeline.buildInstanceTypes.length !== EMPTY;
  }

  // eslint-disable-next-line complexity
  function isPipelineFormValid() {
    const isFormValid = isPipelineNameValid() &&
      isPipelineDescriptionValid() &&
      isPipelineScheduleValid() &&
      // eslint-disable-next-line @typescript-eslint/no-magic-numbers
      pipeline?.buildInstanceTypes?.length > 0 &&
      !!pipeline.recipeId &&
      !!pipeline.recipeVersionId;

    setIsPipelineValid(isFormValid);

    return isFormValid;
  }

  function onFormSubmit() {
    if (isPipelineFormValid()) {
      onSubmit();
    } else {
      setIsSubmitted(true);
    }
  }

  return {
    isUpdate,
    isPipelineNameValid,
    isPipelineDescriptionValid,
    isPipelineScheduleValid,
    isRecipesVersionsValid,
    isRecipesVersionsLoading: isLoading,
    getRecipesSelectOptions,
    getRecipeVersionsSelectOptions,
    isPipelineValid,
    onFormSubmit,
    buildTypeOptions,
    buildTypeOptionsLoading,
    isSubmitted,
    isPipelineBuildTypesValid,
    productOptions,
    productOptionsLoading,
    isProductAssociationEnabled,
  };
};
