import { Box, Button, Header, SpaceBetween } from '@cloudscape-design/components';
import { RecipeVersion } from '../../../../../services/API/proserve-wb-packaging-api';
import { i18n } from './view-recipe-version.translations';
import {
  RECIPE_VERSION_STATES_FOR_FORCE_RELEASE,
  RECIPE_VERSION_STATES_FOR_RELEASE,
  RECIPE_VERSION_STATES_FOR_UPDATE,
  RECIPE_VERSION_STATES_FOR_RETIRE,
  RecipeVersionState
} from '../shared/recipe-version.static';
import { useRoleAccessToggle } from '../../../../../hooks/role-access-toggle';
import { RoleBasedFeature } from '../../../../../state';

export const ViewRecipeVersionHeader = ({
  recipeVersion,
  viewRecipe,
  updateRecipeVersion,
  openReleaseRecipeVersionModal,
  openRetireRecipeVersionModal,
}: {
  recipeVersion?: RecipeVersion,
  viewRecipe: () => void,
  updateRecipeVersion: () => void,
  openReleaseRecipeVersionModal: () => void,
  openRetireRecipeVersionModal: () => void,
}) => {

  const isFeatureAccessible = useRoleAccessToggle();

  function preventRetire() {
    return !recipeVersion?.status ||
      !RECIPE_VERSION_STATES_FOR_RETIRE.has(recipeVersion.status as RecipeVersionState);
  }

  function preventUpdate() {
    return !recipeVersion?.status ||
      !RECIPE_VERSION_STATES_FOR_UPDATE.has(recipeVersion.status as RecipeVersionState);
  }

  function preventRelease() {
    let acceptedStatuses = RECIPE_VERSION_STATES_FOR_RELEASE;
    if (isFeatureAccessible(RoleBasedFeature.ProductPackagingForceReleaseRecipe)) {
      acceptedStatuses = RECIPE_VERSION_STATES_FOR_FORCE_RELEASE;
    }
    return !recipeVersion?.status ||
      !acceptedStatuses.has(recipeVersion.status as RecipeVersionState);
  }

  function renderActions() {
    return <Box float='right'>
      <SpaceBetween size='s' direction='horizontal'>
        <Button
          variant="link"
          onClick={viewRecipe}>
          {i18n.headerActionReturn}
        </Button>
        <Button
          onClick={openRetireRecipeVersionModal}
          disabled= {preventRetire()}>
          {i18n.headerActionRetire}
        </Button>
        <Button
          onClick={updateRecipeVersion}
          disabled= {preventUpdate()}>
          {i18n.headerActionUpdate}
        </Button>
        <Button
          variant='primary'
          onClick={openReleaseRecipeVersionModal}
          disabled= {preventRelease()}>
          {i18n.headerActionRelease}
        </Button>
      </SpaceBetween>
    </Box>;
  }

  return <Header
    variant='awsui-h1-sticky'
    description={
      recipeVersion?.recipeVersionDescription
    }
    actions = {renderActions()}
  >{recipeVersion?.recipeVersionName || '...'}</Header>;
};