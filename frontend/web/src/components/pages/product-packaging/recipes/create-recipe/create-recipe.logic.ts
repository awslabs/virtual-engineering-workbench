import { useState } from 'react';
import { SelectProps } from '@cloudscape-design/components';
import { useNotifications } from '../../../../layout';
import { packagingAPI } from '../../../../../services/API/packaging-api';
import { extractErrorResponseMessage } from '../../../../../utils/api-helpers';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../../../layout/navigation/navigation.static';
import { i18n } from './create-recipe.translations';
import { PACKAGING_OS_VERSIONS, PACKAGING_SUPPORTED_ARCHITECTURES } from '../../shared';

const RECIPE_NAME_REGEX = /^[A-Za-z0-9_ -]{1,50}$/u;
const RECIPE_DESCRIPTION_REGEX = /^[A-Za-z0-9_ -]{0,100}$/u;

type CreateRecipeProps = {
  projectId: string,
};

export const useCreateRecipe = ({ projectId }: CreateRecipeProps) => {

  const { showErrorNotification, showSuccessNotification } = useNotifications();

  const [recipeName, setRecipeName] = useState<string>('');
  const [recipeDescription, setRecipeDescription] = useState<string>('');
  const [recipePlatform, setRecipePlatform] = useState<string>('Windows');
  const [recipeOsVersion, setRecipeOsVersions] = useState<SelectProps.Option>();
  const [recipeArchitecture, setRecipeArchitecture] = useState<SelectProps.Option>();
  const availableRecipeSupportedOsVersions = PACKAGING_OS_VERSIONS[recipePlatform] || [];
  const availableRecipeSupportedArchitectures = PACKAGING_SUPPORTED_ARCHITECTURES[recipePlatform] || [];
  const [isSaving, setIsSaving] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const { navigateTo } = useNavigationPaths();


  function isFormValid(): boolean {
    return isRecipeNameValid() && isRecipeDescriptionValid() && isRecipeValid();
  }

  function isRecipeValid(): boolean {
    return !!recipePlatform && !!recipeOsVersion && !!recipeArchitecture;
  }

  function isRecipeNameValid(): boolean {
    return RECIPE_NAME_REGEX.test(recipeName.trim());
  }

  function isRecipeDescriptionValid(): boolean {
    return RECIPE_DESCRIPTION_REGEX.test(recipeDescription.trim());
  }

  function isRecipeArchitecturesValid(): boolean {
    return recipeArchitecture !== undefined;
  }

  function isRecipeOsVersionsValid(): boolean {
    return recipeOsVersion !== undefined;
  }

  function saveRecipe() {
    if (!isFormValid()) {
      setIsSubmitted(true);
      return;
    }
    setIsSaving(true);
    packagingAPI.createRecipe(projectId, {
      recipeName: recipeName.trim(),
      recipeDescription: recipeDescription.trim(),
      recipePlatform: recipePlatform,
      recipeOsVersion: recipeOsVersion?.value || '',
      recipeArchitecture: recipeArchitecture?.value || '',
    }).then(() => {
      showSuccessNotification({
        header: i18n.createSuccessMessageHeader,
        content: i18n.createSuccessMessageContent
      });
      navigateTo(RouteNames.Recipes);
    }).catch(async e => {
      showErrorNotification({
        header: i18n.createFailMessageHeader,
        content: await extractErrorResponseMessage(e)
      });
    }).finally(() => {
      setIsSaving(false);
      setIsSubmitted(false);
    });
  }

  return {
    recipeName,
    setRecipeName,
    recipeDescription,
    setRecipeDescription,
    recipePlatform,
    setRecipePlatform,
    setRecipeOsVersions,
    recipeOsVersion,
    availableRecipeSupportedOsVersions,
    recipeArchitecture,
    setRecipeArchitecture,
    availableRecipeSupportedArchitectures,
    saveRecipe,
    isSaving,
    isRecipeNameValid,
    isRecipeDescriptionValid,
    isRecipeArchitecturesValid,
    isRecipeOsVersionsValid,
    isSubmitted
  };
};