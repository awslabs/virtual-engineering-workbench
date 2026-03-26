import {
  Box,
  Button,
  Container,
  Form,
  FormField,
  Header,
  HelpPanel,
  Multiselect,
  Input,
  RadioGroup,
  SpaceBetween,
  Spinner,
} from '@cloudscape-design/components';
import { WorkbenchAppLayout } from '../../../layout/workbench-app-layout/workbench-app-layout';
import { i18n } from './create-component.translations';
import { useRecoilValue } from 'recoil';
import { selectedProjectState } from '../../../../state';
import { useCreateComponent } from './create-component.logic';
import { useNavigationPaths } from '../../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../../layout/navigation/navigation.static';

export const CreateComponent = () => {
  const selectedProject = useRecoilValue(selectedProjectState);
  if (selectedProject.projectId === undefined) {
    return <Spinner />;
  }

  const {
    componentName,
    setComponentName,
    componentDescription,
    setComponentDescription,
    componentPlatform,
    setComponentPlatform,
    componentSupportedOsVersions,
    setComponentSupportedOsVersions,
    availableComponentSupportedOsVersions,
    componentSupportedArchitectures,
    setComponentSupportedArchitectures,
    availableComponentSupportedArchitectures,
    saveComponent,
    isSaving,
    isSubmitted,
    isComponentNameValid,
    isComponentDescriptionValid,
    isComponentArchitecturesValid,
    isComponentOsVersionsValid
  } = useCreateComponent({ projectId: selectedProject.projectId });

  const { getPathFor, navigateTo } = useNavigationPaths();

  return (
    <>
      <WorkbenchAppLayout
        breadcrumbItems={[
          { path: i18n.breadcrumbLevel1, href: getPathFor(RouteNames.Components) },
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
            {i18n.componentDetailsHeaderLabel}
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
            data-test='create-component-cancel-button'
            onClick={() => {
              navigateTo(RouteNames.Components);
            }}>
            {i18n.cancelButtonText}
          </Button>
          <Button
            onClick={saveComponent}
            data-test='create-component-create-button'
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
      <Form data-test='create-component-form'>
        <SpaceBetween direction='vertical' size='l'>
          <FormField label={i18n.productNameLabel}
            constraintText={displayConstraintText(
              i18n.componentNameValidationMessage,
              isComponentNameValid()
            )}
            errorText={displayErrorMessage(
              i18n.componentNameValidationMessage,
              isComponentNameValid()
            )}>
            <Input value={componentName}
              onChange={({ detail: { value } }) => setComponentName(value)}
              placeholder={i18n.componentNamePlaceholder}
              data-test='create-component-name-field' />
          </FormField>
          <FormField label={i18n.productDescLabel}
            constraintText={displayConstraintText(
              i18n.componentDescriptionValidationMessage,
              isComponentDescriptionValid()
            )}
            errorText={displayErrorMessage(
              i18n.componentDescriptionValidationMessage,
              isComponentDescriptionValid()
            )}>
            <Input value={componentDescription}
              onChange={({ detail: { value } }) => setComponentDescription(value)}
              placeholder={i18n.componentDescPlaceholder}
              data-test='create-component-description-field' />
          </FormField>
          <FormField
            label={i18n.inputPlatformLabel}
          >
            <RadioGroup
              onChange={({ detail }) => {
                setComponentPlatform(detail.value);
                setComponentSupportedOsVersions([]);
                setComponentSupportedArchitectures([]);
              }}
              value={componentPlatform}
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
              data-test="create-component-platform-radio"
            />
          </FormField>
          <FormField
            label={i18n.supportedArchitecturesLabel}
            errorText={displayErrorMessage(
              i18n.componentArchitecturesValidationMessage,
              isComponentArchitecturesValid())
            }>
            <Multiselect
              options={availableComponentSupportedArchitectures}
              selectedOptions={componentSupportedArchitectures}
              filteringType="auto"
              placeholder={i18n.architecturesPlaceholder}
              onChange={({ detail }) => {
                const selectedArchitectures = detail.selectedOptions.map((value) => { return value; });
                setComponentSupportedArchitectures(selectedArchitectures);
              }}
              data-test='create-component-architectures-field'
            />
          </FormField>
          <FormField label={i18n.osVersionsLabel}
            errorText={displayErrorMessage(
              i18n.componentOsVersionsValidationMessage,
              isComponentOsVersionsValid())
            }>
            <Multiselect
              options={availableComponentSupportedOsVersions}
              selectedOptions={componentSupportedOsVersions}
              filteringType="auto"
              placeholder={i18n.osVersionsPlaceholder}
              onChange={({ detail }) => {
                const selectedOsVersions = detail.selectedOptions.map((value) => { return value; });
                setComponentSupportedOsVersions(selectedOsVersions);
              }}
              data-test='create-component-os-field'
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
