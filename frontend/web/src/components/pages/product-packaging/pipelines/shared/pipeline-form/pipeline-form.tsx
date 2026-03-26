/* eslint-disable complexity */
import { Dispatch, FC, SetStateAction } from 'react';
import { Pipeline } from '../../../../../../services/API/proserve-wb-packaging-api';
import { usePipelineForm } from './pipeline-form.logic';
import {
  Box,
  Button,
  Container,
  Form,
  FormField,
  Header,
  Input,
  Multiselect,
  Select,
  SpaceBetween
} from '@cloudscape-design/components';
import { i18n } from './pipeline-form.translations';
import { packagingAPI } from '../../../../../../services';
import { useNavigationPaths } from '../../../../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../../../../layout/navigation/navigation.static';

interface PipelineFormProps {
  pipeline: Pipeline,
  setPipeline: Dispatch<SetStateAction<Pipeline>>,
  onSubmit: () => void,
  isSubmitInProgress: boolean,
}

export const PipelineForm: FC<PipelineFormProps> = ({
  pipeline,
  setPipeline,
  onSubmit,
  isSubmitInProgress
}) => {
  const { navigateTo } = useNavigationPaths();
  const {
    isUpdate,
    isPipelineNameValid,
    isPipelineDescriptionValid,
    isPipelineScheduleValid,
    getRecipesSelectOptions,
    getRecipeVersionsSelectOptions,
    isRecipesVersionsLoading,
    isRecipesVersionsValid,
    isPipelineValid,
    onFormSubmit,
    buildTypeOptions,
    buildTypeOptionsLoading,
    isSubmitted,
    isPipelineBuildTypesValid,
    productOptions,
    productOptionsLoading,
    isProductAssociationEnabled,
  } = usePipelineForm({
    serviceAPI: packagingAPI,
    pipeline,
    setPipeline,
    onSubmit,
  });

  function renderButtons() {
    return <>
      <Box float='right'>
        <SpaceBetween direction='horizontal' size='xs' alignItems='end'>
          <Button
            data-test='create-pipeline-cancel-button'
            onClick={() => {
              navigateTo(RouteNames.Pipelines);
            }}>
            {i18n.cancelButtonText}
          </Button>
          <Button
            onClick={onFormSubmit}
            data-test='create-pipeline-create-button'
            variant='primary'
            loading={isSubmitInProgress}
          >
            {i18n.submitButtonText(isUpdate)}
          </Button>
        </SpaceBetween>
      </Box>
    </>;
  }

  function displayConstraintText(message: string, isValid: boolean) {
    return (!isSubmitted || isSubmitted && isValid) && message;
  }

  function displayErrorMessage(message: string, isValid: boolean) {
    return isSubmitted && !isValid && message;
  }

  function renderInputForm() {
    return <Form data-test='create-pipeline-form'>
      <SpaceBetween direction='vertical' size='l'>
        <FormField
          label={i18n.labelPipelineName}
          constraintText={displayConstraintText(
            i18n.pipelineNameValidationMessage,
            isPipelineNameValid()
          )}
          errorText={displayErrorMessage(
            i18n.pipelineNameValidationMessage,
            isPipelineNameValid()
          )}>
          <Input value={pipeline?.pipelineName}
            onChange={({ detail: { value } }) => setPipeline({ ...pipeline, pipelineName: value })}
            placeholder={i18n.placeholderPipelineName}
            data-test='pipeline-form-name-field'
            disabled={isUpdate}
            autoComplete={false}
          />
        </FormField>
        <FormField
          label={i18n.labelPipelineDesc}
          constraintText={displayConstraintText(
            i18n.pipelineDescriptionValidationMessage,
            isPipelineDescriptionValid()
          )}
          errorText={displayErrorMessage(
            i18n.pipelineDescriptionValidationMessage,
            isPipelineDescriptionValid()
          )}
        >
          <Input value={pipeline?.pipelineDescription}
            onChange={({ detail: { value } }) => setPipeline({ ...pipeline, pipelineDescription: value })}
            placeholder={i18n.placeholderPipelineDesc}
            data-test='pipeline-form-description-field'
            disabled={isUpdate}
            autoComplete={false}
          />
        </FormField>
        <FormField
          label={i18n.labelPipelineSchedule}
          constraintText={displayConstraintText(
            i18n.pipelineScheduleValidationMessage,
            isPipelineScheduleValid()
          )}
          errorText={displayErrorMessage(
            i18n.pipelineScheduleValidationMessage,
            isPipelineScheduleValid()
          )}
        >
          <Input value={pipeline?.pipelineSchedule}
            onChange={({ detail: { value } }) => setPipeline({ ...pipeline, pipelineSchedule: value })}
            placeholder={i18n.placeholderPipelineSchedule}
            data-test='pipeline-form-schedule-field'
            autoComplete={false}
          />
        </FormField>
        <FormField
          label={i18n.labelRecipe}
          errorText={!isPipelineValid && !pipeline.recipeId && i18n.pipelineRecipeValidationMessage}
        >
          <Select
            selectedOption={getRecipesSelectOptions().find(x => x.value === pipeline.recipeId) || null}
            options={getRecipesSelectOptions()}
            onChange={({ detail }) =>
              setPipeline({ ...pipeline, recipeId: detail.selectedOption.value || '' })}
            placeholder={i18n.placeholderRecipe}
            data-test='pipeline-form-recipe-field'
            loadingText={isRecipesVersionsLoading ? i18n.loadingRecipe : ''}
            errorText={!isRecipesVersionsValid ? i18n.errorFetchingRecipe : ''}
            disabled={isUpdate}
          />
        </FormField>
        <FormField
          label={i18n.labelRecipeVersion}
          errorText={!isPipelineValid && !pipeline.recipeVersionId &&
            i18n.pipelineRecipeVersionValidationMessage}
        >
          <Select
            selectedOption={
              getRecipeVersionsSelectOptions()?.find(x => x.value === pipeline.recipeVersionId) || null
            }
            options={getRecipeVersionsSelectOptions()}
            onChange={({ detail }) =>
              setPipeline({ ...pipeline, recipeVersionId: detail.selectedOption.value || '' })}
            placeholder={i18n.placeholderRecipeVersion}
            data-test='pipeline-form-recipe-version-field'
            loadingText={isRecipesVersionsLoading ? i18n.loadingRecipe : ''}
            errorText={!isRecipesVersionsValid ? i18n.errorFetchingRecipe : ''}
          />
        </FormField>
        <FormField
          label={i18n.labelBuildInstanceTypes}
          errorText={displayErrorMessage(
            i18n.pipelineBuildInstanceTypesValidationMessage,
            isPipelineBuildTypesValid()
          )}
        >
          <Multiselect
            options={buildTypeOptions}
            selectedOptions={pipeline.buildInstanceTypes?.map((x) => ({ label: x, value: x }))}
            placeholder={i18n.placeholderBuildInstanceTypes}
            onChange={({ detail }) => {
              setPipeline({
                ...pipeline,
                buildInstanceTypes: detail.selectedOptions.map(x => x.value || '')
              });
            }}
            loadingText={buildTypeOptionsLoading ? i18n.loadingBuildInstanceTypes : ''}
            data-test='pipeline-form-build-instance-field'
          />
        </FormField>
        {isProductAssociationEnabled &&
          <FormField
            label={i18n.labelProduct}
            description={i18n.productDescription}
          >
            <Select
              selectedOption={productOptions.find(x => x.value === pipeline.productId) || null}
              options={[{ label: i18n.noProductOption, value: '' }, ...productOptions]}
              onChange={({ detail }) =>
                setPipeline({ ...pipeline, productId: detail.selectedOption?.value })}
              placeholder={i18n.placeholderProduct}
              data-test='pipeline-form-product-field'
              statusType={productOptionsLoading ? 'loading' : 'finished'}
              filteringType='auto'
            />
          </FormField>
        }
      </SpaceBetween>
    </Form>
    ;
  }

  return <>
    <SpaceBetween size='l'>
      <Container header={
        <Header variant='h2'>
          {i18n.formHeader}
        </Header>
      }>
        {renderInputForm()}
      </Container>
      {renderButtons()}
    </SpaceBetween>
  </>;
};