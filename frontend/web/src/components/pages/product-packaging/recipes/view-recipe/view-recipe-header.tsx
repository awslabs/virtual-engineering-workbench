import { Button, Header, SpaceBetween } from '@cloudscape-design/components';
import { RouteNames } from '../../../../layout/navigation/navigation.static';
import { i18n } from './view-recipe.translations';
import { Recipe } from '../../../../../services/API/proserve-wb-packaging-api';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic';

export const ViewRecipeHeader = ({
  recipe,
  setArchivePromptVisible
}: {
  recipe?: Recipe,
  setArchivePromptVisible: (value: boolean) => void,
}) => {
  // label value description

  const { navigateTo } = useNavigationPaths();

  return (
    <Header
      variant="awsui-h1-sticky"
      description={recipe?.recipeDescription || '...'}
      actions={
        <>
          <SpaceBetween size="xs" direction="horizontal">
            <Button
              onClick={() => history.back()}
              variant="normal"
              data-test="back-btn"
              disabled={!recipe}
            >
              {i18n.returnButtonText}
            </Button>
            <Button
              onClick={() => setArchivePromptVisible(true)}
              variant="normal"
              data-test="archive-recipe-btn"
              disabled={recipe?.status === 'ARCHIVED'}
            >
              {i18n.archiveButtonText}
            </Button>
            <Button
              onClick={() => {
                navigateTo(RouteNames.CreateRecipeVersion, {
                  ':recipeId': recipe?.recipeId,
                }, {
                  recipeName: recipe?.recipeName,
                  recipePlatform: recipe?.recipePlatform,
                }
                );
              }}
              variant="primary"
              data-test="create-recipe-version-btn"
              disabled={recipe?.status === 'ARCHIVED'}
            >
              {i18n.createButtonText}
            </Button>
          </SpaceBetween>
        </>
      }
    >
      {recipe?.recipeName || '...'}
    </Header>
  );
};
