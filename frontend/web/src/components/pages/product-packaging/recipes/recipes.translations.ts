import { StatusIndicatorProps } from '@cloudscape-design/components';

export const i18n = {
  breadcrumbLevel1: 'Product management: Recipes',
  navHeader: 'Recipes',
  navHeaderDescription:
    'View all recipes that are available in the selected program for product packaging.',
  navHeaderInfo: 'Info',
  infoHeader: 'Recipes',
  createButtonText: 'Create recipe',
  emptyRecipes: 'No recipes',
  emptyRecipesSubTitle: 'No available recipes',
  emptyRecipesResolve: 'Create recipe',
  tableFilterNoResultTitle: 'No recipes',
  tableFilterNoResultActionText: 'Clear filter',
  tableFilterNoResultSubtitle: 'No recipes were found using your search criteria.',
  header: 'Overview',
  something: 'Something',
  infoDescription: 'In this screen you can list recipes.',
  findRecipesPlaceholder: 'Find recipes',
  recipeArchive: 'Archive',
  recipeCreate: 'Create',
  recipeUpdate: 'Update',
  recipeRelease: 'Release',
  recipesFetchErrorTitle: 'Unable to fetch recipes',
  tableHeaderRecipeName: 'Name',
  tableHeaderRecipeDescription: 'Description',
  tableHeaderRecipePlatform: 'Platform',
  tableHeaderRecipeLastUpdate: 'Last Update',
  tableHeader: 'Recipes',
  buttonActions: 'Actions',
  buttonViewRecipe: 'View',
  infoPanelHeader: 'Recipes',
  infoPanelLabel1: 'What is a recipe?',
  infoPanelMessage1: `A recipe, also known as Image Builder Recipe, is an ordered collection of
  components that describes how the Amazon Machine Image (AMI) for a specific workbench instance
  must be built and validated i.e. recipe defines how an image is configured, tested, and assessed.`,
  infoPanelLabel2: 'What can I accomplish here?',
  infoPanelMessage2: 'Browse existing recipes categorized by platform and start creating new ones.',
  createSuccessMessageHeader: 'Request successful',
  createArchiveSuccessMessageContent: 'Recipe has been successfully archived',
  statusFirstOptionValue: 'CREATED',
  createFailMessageHeader: 'Failed to create component',
  tableHeaderStatus: 'Status'
};

export const RECIPE_STATUS_COLOR_MAP: { [key: string]: StatusIndicatorProps.Type } = {
  CREATED: 'success',
  FAILED: 'error',
  RETIRED: 'stopped',
  PROCESSING: 'pending',
};