
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
import { Image } from '../../../../../../services/API/proserve-wb-packaging-api';
import { getBaseImageName } from '../recipe-version-base-image.helpers';

type Integration = { integrationId: string, name: string, type?: string, details?: string };

const EMPTY = 0;

type RecipeVersionBaseImageProps = {
  images: Image[],
  baseImages: Image[],
  isImagesLoading: boolean,
  parentImageId: string,
  setParentImageId: (parentImageId: string) => void,
};

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
} & RecipeVersionIntegrationsProps & RecipeVersionBaseImageProps;

const RecipeVersionIntegrations: FC<RecipeVersionIntegrationsProps> = () => {
  return <></>;
};

const RecipeVersionBaseImage: FC<RecipeVersionBaseImageProps> = ({
  images,
  baseImages,
  isImagesLoading,
  parentImageId,
  setParentImageId,
}) => {
  if (baseImages.length === EMPTY && !parentImageId) {
    return <></>;
  }

  const defaultBaseImageOption: SelectProps.Option = { label: i18n.step1BaseImageDefault, value: '' };
  const baseImageOptions: SelectProps.Option[] = [
    defaultBaseImageOption,
    ...baseImages.map(image => ({
      label: image.imageName || image.imageId,
      value: image.imageId,
      labelTag: image.imageId,
      description: image.osVersion,
    })),
  ];
  if (parentImageId && !baseImages.some(image => image.imageId === parentImageId)) {
    baseImageOptions.push({
      label: getBaseImageName(images, parentImageId),
      value: parentImageId,
      labelTag: parentImageId,
      description: isImagesLoading ? undefined : i18n.step1BaseImageUnavailable,
    });
  }

  return <FormField
    label={i18n.step1BaseImage}
    description={i18n.step1BaseImageDescription}
  >
    <Select
      selectedOption={
        baseImageOptions.find(option => option.value === parentImageId) || defaultBaseImageOption
      }
      onChange={({ detail }) => setParentImageId(detail.selectedOption.value || '')}
      options={baseImageOptions}
      statusType={isImagesLoading ? 'loading' : 'finished'}
      loadingText={i18n.step1BaseImageLoading}
      data-test="recipe-version-base-image"
    />
  </FormField>;
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
  images,
  baseImages,
  isImagesLoading,
  parentImageId,
  setParentImageId,
}) => {
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
        <RecipeVersionBaseImage
          images={images}
          baseImages={baseImages}
          isImagesLoading={isImagesLoading}
          parentImageId={parentImageId}
          setParentImageId={setParentImageId}
        />
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
