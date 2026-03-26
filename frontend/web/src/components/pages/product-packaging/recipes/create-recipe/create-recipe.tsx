import {
  Box,
  Button,
  Container,
  Form,
  FormField,
  Header,
  HelpPanel,
  Input,
  RadioGroup,
  SpaceBetween,
  Spinner,
  Select,
} from '@cloudscape-design/components';
import { WorkbenchAppLayout } from '../../../../layout/workbench-app-layout/workbench-app-layout';
import { i18n } from './create-recipe.translations';
import { useRecoilValue } from 'recoil';
import { selectedProjectState } from '../../../../../state';
import { useCreateRecipe } from './create-recipe.logic';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../../../layout/navigation/navigation.static';

export const CreateRecipe = () => {
  const selectedProject = useRecoilValue(selectedProjectState);
  if (selectedProject.projectId === undefined) {
    return <Spinner />;
  }

  const {
    recipeName,
    setRecipeName,
    recipeDescription,
    setRecipeDescription,
    recipePlatform,
    setRecipePlatform,
    recipeOsVersion,
    setRecipeOsVersions,
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
  } = useCreateRecipe({ projectId: selectedProject.projectId });

  const { getPathFor, navigateTo } = useNavigationPaths();

  return (
    <>
      <WorkbenchAppLayout
        breadcrumbItems={[
          { path: i18n.breadcrumbLevel1, href: getPathFor(RouteNames.Recipes) },
          { path: i18n.breadcrumbLevel2, href: '#' },
        ]}
        content={renderContent()}
        customHeader={renderHeader()}
        tools={renderTools()}
      />
    </>
  );

  function renderHeader() {
    return <Header
      variant='awsui-h1-sticky'
      description={i18n.navHeaderDescription}
    >{i18n.infoHeader}</Header>;
  }

  function renderContent() {
    return <>
      <SpaceBetween size='l'>
        <Container header={
          <Header variant='h2'>
            {i18n.recipeDetailsHeaderLabel}
          </Header>
        }>
          {renderInputForm()}
        </Container>
        {renderButtons()}
      </SpaceBetween>
    </>;
  }

  function renderButtons() {
    return <>
      <Box float='right'>
        <SpaceBetween direction='horizontal' size='xs' alignItems='end'>
          <Button
            data-test='create-recipe-cancel-button'
            onClick={() => {
              navigateTo(RouteNames.Recipes);
            }}>
            {i18n.cancelButtonText}
          </Button>
          <Button
            onClick={saveRecipe}
            data-test='create-recipe-create-button'
            variant='primary'
            loading={isSaving}
          >
            {i18n.createButtonText}
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
    return <>
      <Form data-test='create-recipe-form'>
        <SpaceBetween direction='vertical' size='l'>
          <FormField label={i18n.productNameLabel}
            constraintText={displayConstraintText(
              i18n.recipeNameValidationMessage,
              isRecipeNameValid()
            )}
            errorText={displayErrorMessage(
              i18n.recipeNameValidationMessage,
              isRecipeNameValid()
            )}>
            <Input value={recipeName}
              onChange={({ detail: { value } }) => setRecipeName(value)}
              placeholder={i18n.recipeNamePlaceholder}
              data-test='create-recipe-name-field' />
          </FormField>
          <FormField label={i18n.productDescLabel}
            constraintText={displayConstraintText(
              i18n.recipeDescriptionValidationMessage,
              isRecipeDescriptionValid()
            )}
            errorText={displayErrorMessage(
              i18n.recipeDescriptionValidationMessage,
              isRecipeDescriptionValid()
            )}>
            <Input value={recipeDescription}
              onChange={({ detail: { value } }) => setRecipeDescription(value)}
              placeholder={i18n.recipeDescPlaceholder}
              data-test='create-recipe-description-field' />
          </FormField>
          <FormField
            label={i18n.inputPlatformLabel}
          >
            <RadioGroup
              onChange={({ detail }) => {
                setRecipePlatform(detail.value);
                setRecipeOsVersions({});
                setRecipeArchitecture({});
              }}
              value={recipePlatform}
              items={[
                {
                  value: 'Windows',
                  label: i18n.inputPlatformWindowsLabel,
                  description: i18n.inputPlatformWindowsDescription
                },
                {
                  value: 'Linux',
                  label: i18n.inputPlatformLinuxLabel,
                  description: i18n.inputPlatformLinuxDescription
                },
              ]}
              data-test="create-recipe-platform-radio"
            />
          </FormField>
          <FormField label={i18n.supportedArchitecturesLabel}
            errorText={displayErrorMessage(
              i18n.recipeArchitecturesValidationMessage,
              isRecipeArchitecturesValid()
            )}>
            <Select
              placeholder={i18n.architecturePlaceholder}
              options={availableRecipeSupportedArchitectures}
              selectedOption={recipeArchitecture!}
              onChange={({ detail }) => setRecipeArchitecture(detail.selectedOption)}
              data-test='create-recipe-architectures-field'
            />
          </FormField>
          <FormField label={i18n.osVersionsLabel}
            errorText={displayErrorMessage(
              i18n.recipeOsVersionsValidationMessage,
              isRecipeOsVersionsValid()
            )}>
            <Select
              placeholder={i18n.technologyPlaceholder}
              options={availableRecipeSupportedOsVersions}
              selectedOption={recipeOsVersion!}
              onChange={({ detail }) => setRecipeOsVersions(detail.selectedOption)}
              data-test='create-recipe-os-field'
            />
          </FormField>
        </SpaceBetween>
      </Form>
    </>;
  }

  function renderTools() {
    return (
      <HelpPanel header={<h2>{i18n.infoPanelHeader}</h2>}>
        <SpaceBetween size={'s'}>
          <Box variant="awsui-key-label">{i18n.infoPanelLabel1}</Box>
          <Box variant="p">{i18n.infoPanelMessage1}</Box>
          <Box variant="p">{i18n.infoPanelMessage2}</Box>
          <Box variant="p">{i18n.infoPanelMessage3}</Box>
        </SpaceBetween>
      </HelpPanel>
    );
  }
};
