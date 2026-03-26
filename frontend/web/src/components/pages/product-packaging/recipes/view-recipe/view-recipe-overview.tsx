import { ColumnLayout, Container, Header, SpaceBetween, Spinner } from '@cloudscape-design/components';
import { Recipe } from '../../../../../services/API/proserve-wb-packaging-api';
import { ValueWithLabel } from '../../../shared/value-with-label';
import { CopyText, UserDate } from '../../../shared';
import { i18n } from './view-recipe.translations';
import { PACKAGING_OS_TRANSLATIONS } from '../../shared';

export const ViewRecipeOverview = ({
  recipe,
  recipeLoading
}: { recipe?: Recipe, recipeLoading: boolean }) => {

  if (recipeLoading) { return <Spinner />; }
  if (!recipe) { return <></>; }

  return (
    <Container header={<Header>{i18n.detailsHeader}</Header>} data-test="recipe-details">
      <ColumnLayout columns={3} variant="text-grid">
        <SpaceBetween size="l">
          <ValueWithLabel label={i18n.detailsRecipeId} data-test="recipe-id">
            <CopyText
              copyText={recipe.recipeId}
              copyButtonLabel={i18n.copy}
              successText={i18n.copySuccess}
              errorText={i18n.copyError} />
          </ValueWithLabel>
        </SpaceBetween>
        <SpaceBetween size="l">
          <ValueWithLabel label={i18n.detailsPlatform} data-test="platform">
            {recipe.recipePlatform}
          </ValueWithLabel>
          <ValueWithLabel label={i18n.detailsArchitecture} data-test="supported-architecture">
            <SpaceBetween size="xxxs">
              {recipe.recipeArchitecture}
            </SpaceBetween>
          </ValueWithLabel>
          <ValueWithLabel label={i18n.detailsOS} data-test="supported-os">
            <SpaceBetween size="xxxs">
              {PACKAGING_OS_TRANSLATIONS[recipe.recipeOsVersion] || recipe.recipeOsVersion}
            </SpaceBetween>
          </ValueWithLabel>
        </SpaceBetween>
        <SpaceBetween size="l">
          <ValueWithLabel label={i18n.detailsAuthor} data-test="author">
            {recipe.createdBy}
          </ValueWithLabel>
          <ValueWithLabel label={i18n.detailsCreateDate} data-test="create-date">
            <UserDate date={recipe.createDate} />
          </ValueWithLabel>
        </SpaceBetween>
      </ColumnLayout>
    </Container>
  );
};