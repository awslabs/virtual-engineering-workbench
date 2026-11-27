
import {
  Container,
  Form,
  FormField,
  Header,
  Input,
  RadioGroup,
  Select,
  SelectProps,
  SpaceBetween,
} from '@cloudscape-design/components';
import { FC } from 'react';
import { i18n } from './recipe-version-wizard.translations';
import { RECIPE_VERSION_RELEASE_TYPE_MAP } from '../recipe-version-release-type-map';
import {
  DiscoveredMarketplaceSubscription,
  Image,
} from '../../../../../../services/API/proserve-wb-packaging-api';

type Integration = { integrationId: string, name: string, type?: string, details?: string };

const EMPTY = 0;

type RecipeVersionIntegrationsProps = {
  availableIntegrations: Integration[],
  selectedIntegrations: string[],
  setSelectedIntegrations: (integrations: string[]) => void,
  isIntegrationsLoading: boolean,
};

export type RecipeVersionWizardStep1Props = {
  isUpdate: boolean,
  description: string,
  setDescription: (description: string) => void,
  isDescriptionValid: boolean,
  volumeSize: number,
  setVolumeSize: (volumeSize: number) => void,
  isVolumeSizeValid: boolean,
  minVolumeSize: number,
  maxVolumeSize: number,
  versionReleaseTypes: string[],
  versionReleaseType: string,
  setVersionReleaseType: (versionReleaseType: string) => void,
  isVersionReleaseTypeValid: boolean,
  marketplaceImages: DiscoveredMarketplaceSubscription[],
  awsPublishedImages: Image[],
  isMarketplaceImagesLoading: boolean,
  baseImage: string,
  setBaseImage: (baseImage: string) => void,
} & RecipeVersionIntegrationsProps;

const RecipeVersionIntegrations: FC<RecipeVersionIntegrationsProps> = () => {
  return <></>;
};

export const RecipeVersionWizardStep1: FC<RecipeVersionWizardStep1Props> = ({
  isUpdate,
  description,
  setDescription,
  isDescriptionValid,
  volumeSize,
  setVolumeSize,
  isVolumeSizeValid,
  minVolumeSize,
  maxVolumeSize,
  versionReleaseTypes,
  versionReleaseType,
  setVersionReleaseType,
  isVersionReleaseTypeValid,
  availableIntegrations,
  isIntegrationsLoading,
  selectedIntegrations,
  setSelectedIntegrations,
  marketplaceImages,
  awsPublishedImages,
  isMarketplaceImagesLoading,
  baseImage,
  setBaseImage,
}) => {
  const defaultBaseImageOption: SelectProps.Option = { label: i18n.step1BaseImageDefault, value: '' };
  const marketplaceOptions: SelectProps.Option[] = marketplaceImages.map(image => ({
    label: image.productName || image.productId,
    value: image.productId,
    description: image.productId,
  }));
  const awsPublishedOptions: SelectProps.Option[] = awsPublishedImages.map(image => ({
    label: image.imageName || image.imageId,
    value: image.imageId,
    description: `${image.imageId} · ${image.imageUpstreamId || ''}`,
  }));
  const knownOptions = [defaultBaseImageOption, ...marketplaceOptions, ...awsPublishedOptions];
  const baseImageOptions: (SelectProps.Option | SelectProps.OptionGroup)[] = [
    defaultBaseImageOption,
    ...marketplaceOptions.length > EMPTY
      ? [{ label: i18n.step1BaseImageGroupMarketplace, options: marketplaceOptions }]
      : [],
    ...awsPublishedOptions.length > EMPTY
      ? [{ label: i18n.step1BaseImageGroupAwsPublished, options: awsPublishedOptions }]
      : [],
  ];
  if (baseImage && !knownOptions.some(option => option.value === baseImage)) {
    const unavailable = { label: baseImage, value: baseImage, description: i18n.step1BaseImageUnavailable };
    knownOptions.push(unavailable);
    baseImageOptions.push(unavailable);
  }

  function getReleaseTypeOption(prodType: string) {
    return {
      label: RECIPE_VERSION_RELEASE_TYPE_MAP[prodType],
      value: prodType
    };
  }

  function getDescriptionError() {
    return !isDescriptionValid && description.trim() === '' ? i18n.step1InputDescriptionError : '';
  }

  function getReleaseTypeError() {
    return !isVersionReleaseTypeValid && versionReleaseType === '' ? i18n.step1InputReleaseTypeError : '';
  }

  function getVolumeSizeError() {
    return !isVolumeSizeValid && (volumeSize < minVolumeSize || volumeSize > maxVolumeSize)
      ? `Volume size should be between (${minVolumeSize} - ${maxVolumeSize}) GB.` : '';
  }


  return <Container
    header={<Header variant="h2">
      {i18n.step1Header}
    </Header>}
  >
    <Form>
      <SpaceBetween direction="vertical" size="l">
        <FormField
          label={i18n.step1InputDescription}
          errorText={ getDescriptionError() }
        >
          <Input
            value={description}
            onChange={({ detail: { value } }) => setDescription(value)}
            placeholder={i18n.step1InputDescriptionPlaceholder}
            data-test="recipe-version-description"
          />
        </FormField>
        <FormField
          label={i18n.step1VolumeSize}
          errorText={ getVolumeSizeError() }
        >
          <Input
            value={volumeSize.toString()}
            onChange={({ detail: { value } }) => setVolumeSize(parseInt(value, 10))}
            type="number"
            data-test="recipe-version-volume-size"
            inputMode='numeric'
          />
        </FormField>
        {(marketplaceImages.length > EMPTY || awsPublishedImages.length > EMPTY || !!baseImage) &&
          <FormField
            label={i18n.step1BaseImage}
            description={i18n.step1BaseImageDescription}
          >
            <Select
              selectedOption={
                knownOptions.find(option => option.value === baseImage)
                || defaultBaseImageOption
              }
              onChange={({ detail }) => setBaseImage(detail.selectedOption.value || '')}
              options={baseImageOptions}
              statusType={isMarketplaceImagesLoading ? 'loading' : 'finished'}
              loadingText={i18n.step1BaseImageLoading}
              data-test="recipe-version-base-image"
            />
          </FormField>}
        {!isUpdate &&
          <FormField
            label={i18n.step1InputReleaseType}
            errorText={ getReleaseTypeError() }
          >
            <RadioGroup
              onChange={({ detail }) => setVersionReleaseType ? setVersionReleaseType(detail.value) : null}
              value={versionReleaseType ? versionReleaseType : ''}
              items={versionReleaseTypes.map(getReleaseTypeOption)}
              data-test="recipe-version-release-type"
            />
          </FormField>}
        <RecipeVersionIntegrations
          availableIntegrations={availableIntegrations}
          selectedIntegrations={selectedIntegrations}
          isIntegrationsLoading={isIntegrationsLoading}
          setSelectedIntegrations={setSelectedIntegrations}
        />
      </SpaceBetween>
    </Form>
  </Container>;
};
