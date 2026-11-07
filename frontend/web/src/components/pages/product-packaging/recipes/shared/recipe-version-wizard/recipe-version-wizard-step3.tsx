import { Button, ColumnLayout, Container, Header, SpaceBetween } from '@cloudscape-design/components';
import { FC } from 'react';
import { i18n } from './recipe-version-wizard.translations';
import {
  RecipeComponentVersion,
  ComponentVersionEntry,
  MarketplaceImage,
} from '../../../../../../services/API/proserve-wb-packaging-api';
import { ValueWithLabel } from '../../../../shared/value-with-label';
import { ComponentVersionEntriesView } from '../../../shared';

type Integration = { integrationId: string, name: string, type?: string, details?: string };

export interface RecipeVersionWizardStep3Props {
  setActiveStepIndex: (index: number) => void,
  description: string,
  versionReleaseType: string,
  recipeComponentsVersions: RecipeComponentVersion[],
  volumeSize: number,
  recipeMandatoriesComponentsVersions: ComponentVersionEntry[],
  integrationComponentsVersions: ComponentVersionEntry[],
  availableIntegrations: Integration[],
  selectedIntegrations: string[],
  parentImageProductId: string,
  marketplaceImages: MarketplaceImage[],
}


const EMPTY = 0;
const COL_COUNT_NO_INTEGRATIONS = 3;
const COL_COUNT_WITH_INTEGRATIONS = 4;

export const RecipeVersionWizardStep3: FC<RecipeVersionWizardStep3Props> = ({
  setActiveStepIndex,
  description,
  versionReleaseType,
  recipeComponentsVersions,
  volumeSize,
  recipeMandatoriesComponentsVersions,
  integrationComponentsVersions,
  selectedIntegrations,
  availableIntegrations,
  parentImageProductId,
  marketplaceImages,
}) => {
  const selectedMarketplaceImage = marketplaceImages.find(image => image.productId === parentImageProductId);
  return <SpaceBetween direction='vertical' size='l'>
    <SpaceBetween direction='vertical' size='xs'>
      <Header
        variant='h3'
        actions={
          // eslint-disable-next-line @typescript-eslint/no-magic-numbers
          <Button onClick={() => setActiveStepIndex(0)}>
            {i18n.step3ButtonEdit}
          </Button>
        }
      >
        {i18n.step3Step1Header}
      </Header>
      <Container
        header={<Header variant="h2">
          {i18n.step3DetailsHeader}
        </Header>}
      >
        <ColumnLayout columns={getReviewColumnCount()}>
          <ValueWithLabel label={i18n.step1InputDescription} data-test="recipe-description">
            {description}
          </ValueWithLabel>
          <ValueWithLabel label={i18n.step1VolumeSize} data-test="recipe-volume-size">
            {volumeSize}
          </ValueWithLabel>
          <ValueWithLabel label={i18n.step1InputReleaseType} data-test="recipe-release-type">
            {versionReleaseType}
          </ValueWithLabel>
          {getBaseImageReviewColumn()}
          {getIntegrationsReviewColumn()}
        </ColumnLayout>
      </Container>
    </SpaceBetween>
    <SpaceBetween direction='vertical' size='xs'>
      <Header
        variant='h3'
        actions={
          // eslint-disable-next-line @typescript-eslint/no-magic-numbers
          <Button onClick={() => setActiveStepIndex(1)}>
            {i18n.step3ButtonEdit}
          </Button>
        }
      >
        {i18n.step3Step2Header}
      </Header>
      <ComponentVersionEntriesView
        componentVersionEntries=
          {[
            ...recipeMandatoriesComponentsVersions,
            ...integrationComponentsVersions,
            ...recipeComponentsVersions
          ]}
        typeColumnEnabled
      />
    </SpaceBetween>
  </SpaceBetween>;

  function getReviewColumnCount() {
    if (selectedIntegrations.length > EMPTY || parentImageProductId) {
      return COL_COUNT_WITH_INTEGRATIONS;
    }
    return COL_COUNT_NO_INTEGRATIONS;
  }

  function getBaseImageReviewColumn() {
    if (!parentImageProductId) {
      return <></>;
    }
    return <ValueWithLabel label={i18n.step1BaseImage} data-test="recipe-base-image">
      {selectedMarketplaceImage
        ? selectedMarketplaceImage.name
        : parentImageProductId}
    </ValueWithLabel>;
  }

  function getIntegrationsReviewColumn() {
    if (selectedIntegrations.length === EMPTY) {
      return <></>;
    }
    return <ValueWithLabel label={i18n.step1Integrations} data-test="recipe-integrations">
      <SpaceBetween direction='vertical' size='m'>
        {selectedIntegrations.map(i =>
          <div key={i}>{availableIntegrations.find(x => x.integrationId === i)?.type || i}</div>
        )}
      </SpaceBetween>
    </ValueWithLabel>;
  }
};
