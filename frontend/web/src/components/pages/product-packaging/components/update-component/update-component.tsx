import { useState } from 'react';
import {
  Box,
  Container,
  FormField,
  Header,
  HelpPanel,
  Input,
  SpaceBetween,
  Spinner,
  Textarea,
  Wizard,
} from '@cloudscape-design/components';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic.ts';
import { RouteNames } from '../../../../layout/navigation/navigation.static.ts';
import { WorkbenchAppLayout } from '../../../../layout/workbench-app-layout/workbench-app-layout.tsx';
import { i18n } from './update-component.translations';
import { packagingAPI } from '../../../../../services/API/packaging-api.ts';
import { useUpdateComponent } from './update-component.logic.ts';
import { useRecoilValue } from 'recoil';
import { selectedProjectState } from '../../../../../state/index.ts';
import { useParams } from 'react-router-dom';

const STEP_1_INDEX = 0;
const STEP_2_INDEX = 1;

export const UpdateComponent = () => {
  const { getPathFor, navigateTo } = useNavigationPaths();
  const selectedProject = useRecoilValue(selectedProjectState);
  const { componentId } = useParams();
  const [activeStepIndex, setActiveStepIndex] = useState(STEP_1_INDEX);

  if (!componentId) {
    navigateTo(RouteNames.Components);
    return <></>;
  }
  if (!selectedProject.projectId) {
    return <></>;
  }

  const {
    component,
    componentLoading,
    formData,
    formErrors,
    isSubmitting,
    handleInputChange,
    handleSubmit,
    handleCancel,
  } = useUpdateComponent({
    serviceApi: packagingAPI,
    projectId: selectedProject.projectId,
    componentId,
  });

  return (
    <WorkbenchAppLayout
      breadcrumbItems={[
        { path: i18n.breadcrumbLevel1, href: getPathFor(RouteNames.Components) },
        {
          path: i18n.breadcrumbLevel2,
          href: getPathFor(RouteNames.ViewComponent, { ':componentId': componentId })
        },
        { path: i18n.breadcrumbLevel3, href: '#' },
      ]}
      content={renderContent()}
      contentType="default"
      tools={renderTools()}
    />
  );

  function renderContent() {
    if (componentLoading || !component) {
      return <Spinner size="large" />;
    }

    const handleWizardSubmit = () => {
      handleSubmit();
    };

    return (
      <Wizard
        i18nStrings={{
          stepNumberLabel: (stepNumber) => `Step ${stepNumber}`,
          collapsedStepsLabel: (stepNumber, stepsCount) =>
            `Step ${stepNumber} of ${stepsCount}`,
          cancelButton: i18n.cancelButton,
          previousButton: i18n.previousButton,
          nextButton: i18n.nextButton,
          submitButton: i18n.updateButton,
          optional: i18n.optional,
        }}
        onCancel={handleCancel}
        onSubmit={handleWizardSubmit}
        activeStepIndex={activeStepIndex}
        onNavigate={({ detail }) => setActiveStepIndex(detail.requestedStepIndex)}
        isLoadingNextStep={isSubmitting}
        steps={[
          {
            title: i18n.step1Title,
            description: i18n.step1Description,
            content: renderStep1Content(),
          },
          {
            title: i18n.step2Title,
            description: i18n.step2Description,
            content: renderStep2Content(),
          },
        ]}
      />
    );
  }

  function renderStep1Content() {
    return (
      <Container header={<Header variant="h2">{i18n.step1Header}</Header>}>
        <SpaceBetween size="l">
          <FormField
            label={i18n.componentNameLabel}
            description={i18n.componentNameReadOnlyDescription}
          >
            <Input
              value={component?.componentName || ''}
              disabled={true}
              readOnly={true}
            />
          </FormField>
          <FormField
            label={i18n.componentDescriptionLabel}
            description={i18n.componentDescriptionDescription}
            errorText={formErrors.componentDescription}
          >
            <Box>
              <style>{`
                textarea[class*="awsui_textarea"] {
                  resize: none !important;
                }
              `}</style>
              <Textarea
                value={formData.componentDescription}
                onChange={({ detail }) =>
                  handleInputChange('componentDescription', detail.value)
                }
                placeholder={i18n.componentDescriptionPlaceholder}
                rows={3}
                disabled={isSubmitting}
                disableBrowserAutocorrect={true}
              />
            </Box>
          </FormField>
        </SpaceBetween>
      </Container>
    );
  }

  function renderStep2Content() {
    return (
      <Container header={<Header variant="h2">{i18n.step2Header}</Header>}>
        <SpaceBetween size="l">
          <Box>
            <Box variant="awsui-key-label">{i18n.componentNameLabel}</Box>
            <Box>{component?.componentName}</Box>
          </Box>
          <Box>
            <Box variant="awsui-key-label">{i18n.componentDescriptionLabel}</Box>
            <Box>{formData.componentDescription || i18n.noDescription}</Box>
          </Box>
        </SpaceBetween>
      </Container>
    );
  }

  function renderTools() {
    return (
      <>
        {activeStepIndex === STEP_1_INDEX && renderStep1InfoPanel()}
        {activeStepIndex === STEP_2_INDEX && renderStep2InfoPanel()}
      </>
    );
  }

  function renderStep1InfoPanel() {
    return (
      <HelpPanel header={<h2>{i18n.step1infoPanelHeader}</h2>}>
        <SpaceBetween size={'s'}>
          <Box variant="awsui-key-label">{i18n.step1infoPanelLabel1}</Box>
          <Box variant="p">{i18n.step1infoPanelMessage1}</Box>
          <Box variant="p">{i18n.step1infoPanelMessage2}</Box>
        </SpaceBetween>
      </HelpPanel>
    );
  }

  function renderStep2InfoPanel() {
    return (
      <HelpPanel header={<h2>{i18n.step2infoPanelHeader}</h2>}>
        <SpaceBetween size={'s'}>
          <Box variant="p">{i18n.step2infoPanelMessage1}</Box>
        </SpaceBetween>
      </HelpPanel>
    );
  }
};