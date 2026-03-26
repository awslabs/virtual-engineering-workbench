import { ColumnLayout, Container, Header, SpaceBetween, Spinner } from '@cloudscape-design/components';
import { RecipeVersion } from '../../../../../services/API/proserve-wb-packaging-api';
import { ValueWithLabel } from '../../../shared/value-with-label';
import { i18n } from './view-recipe-version.translations';
import { CopyText, UserDate } from '../../../shared';
import { RecipeVersionStatus } from '../shared/recipe-version-status';

export const ViewRecipeVersionOverview = ({
  recipeVersion,
  recipeVersionLoading,
}: { recipeVersion?: RecipeVersion, recipeVersionLoading: boolean }) => {

  if (recipeVersionLoading) { return <Spinner />; }
  if (!recipeVersion) { return <></>; }

  return (
    <Container header={<Header>{i18n.detailsHeader}</Header>} data-test="recipe-details">
      <ColumnLayout columns={4} variant="text-grid">
        <SpaceBetween size="l">
          <ValueWithLabel label={i18n.detailsRecipeId} data-test="recipe-id">
            <CopyText
              copyButtonLabel={i18n.detailsRecipeId}
              copyText={recipeVersion.recipeId}
              successText={i18n.recipeIdIdCopySuccess}
              errorText={i18n.recipeIdIdCopyError}
            />
          </ValueWithLabel>
        </SpaceBetween>
        <SpaceBetween size="l">
          <ValueWithLabel label={i18n.detailsVersionId} data-test="version-id">
            <CopyText
              copyButtonLabel={i18n.detailsVersionId}
              copyText={recipeVersion.recipeVersionId}
              successText={i18n.versionIdCopySuccess}
              errorText={i18n.versionIdCopyError}
            />
          </ValueWithLabel>
        </SpaceBetween>
        <SpaceBetween size="l">
          <ValueWithLabel label={i18n.detailsStatus} data-test="status">
            <RecipeVersionStatus status={recipeVersion.status} />
          </ValueWithLabel>
        </SpaceBetween>
        <SpaceBetween size="l">
          <ValueWithLabel label={i18n.detailsVolumeSize} data-test="volume-size">
            {recipeVersion.recipeVersionVolumeSize} GB
          </ValueWithLabel>
        </SpaceBetween>
        <SpaceBetween size="l">
          <ValueWithLabel label={i18n.detailsAuthor} data-test="created-by">
            {recipeVersion.createdBy}
          </ValueWithLabel>
        </SpaceBetween>
        <SpaceBetween size="l">
          <ValueWithLabel label={i18n.detailsLastContributor} data-test="last-updated-by">
            {recipeVersion.lastUpdatedBy}
          </ValueWithLabel>
        </SpaceBetween>
        <SpaceBetween size="l">
          <ValueWithLabel label={i18n.detailsLastUpdate} data-test="last-update-date">
            <UserDate date={recipeVersion.lastUpdateDate} />
          </ValueWithLabel>
        </SpaceBetween>
      </ColumnLayout>
    </Container>
  );
};