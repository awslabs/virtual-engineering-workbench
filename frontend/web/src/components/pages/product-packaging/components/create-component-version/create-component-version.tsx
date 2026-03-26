/* eslint-disable complexity */
import { useLocation, useParams } from 'react-router-dom';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../../../layout/navigation/navigation.static';
import { WorkbenchAppLayout } from '../../../../layout/workbench-app-layout/workbench-app-layout';
import { i18n } from './create-component-version.translations';
import { Box, HelpPanel, Icon, SpaceBetween, Spinner } from '@cloudscape-design/components';

import { useCreateComponentVersion } from './create-component-version.logic';
import { useRecoilValue } from 'recoil';
import { selectedProjectState } from '../../../../../state';
import { ComponentVersionWizard } from '../shared';
import { useState } from 'react';

const EMPTY_ARRAY_LENGTH = 0;
const STEP_1_INDEX = 0;
const STEP_2_INDEX = 1;
const STEP_3_INDEX = 2;
const STEP_4_INDEX = 3;

export const CreateComponentVersion = () => {
  const selectedProject = useRecoilValue(selectedProjectState);
  if (!selectedProject.projectId) {
    return <Spinner />;
  }

  const { getPathFor, navigateTo } = useNavigationPaths();

  const { componentId } = useParams();

  const { state } = useLocation();

  const componentName = state.componentName ? state.componentName : 'SampleComponent';
  const componentPlatform = state.componentPlatform ? state.componentPlatform : 'Linux';
  const componentStepAction =
    componentPlatform === 'Windows'
      ? 'ExecutePowerShell'
      : 'ExecuteBash'
  ;
  const componentStepCommand =
    componentPlatform === 'Windows'
      ? 'Write-Host \'Hello VEW!\''
      : 'echo \'Hello VEW!\''
  ;
  const sampleComponentDefinitionYaml = `name: ${componentName}
description: Component definition for ${componentName}.
schemaVersion: 1.0
phases:
  - name: build
    steps:
      - name: BuildStep
        action: ${componentStepAction}
        inputs:
          commands:
            - ${componentStepCommand}
  - name: validate
    steps:
      - name: ValidateStep
        action: ${componentStepAction}
        inputs:
          commands:
            - ${componentStepCommand}
  - name: test
    steps:
      - name: TestStep
        action: ${componentStepAction}
        inputs:
          commands:
            - ${componentStepCommand}
`;

  if (!componentId) {
    navigateTo(RouteNames.Components);
    return <></>;
  }

  const {
    latestComponentVersion,
    latestComponentVersionYamlDefinition,
    latestComponentYamlDefinitionIsLoading,
    versionCreateInProgress,
    createVersion,
    releasedVersions,
    fetchVersionYaml,
  } = useCreateComponentVersion({
    projectId: selectedProject.projectId || '',
    componentId,
  });

  const [activeStepIndex, setActiveStepIndex] = useState(EMPTY_ARRAY_LENGTH);

  return (
    <>
      <WorkbenchAppLayout
        breadcrumbItems={[
          {
            path: i18n.breadcrumbLevel1,
            href: getPathFor(RouteNames.Components),
          },
          {
            path: i18n.breadcrumbLevel2,
            href: getPathFor(RouteNames.ViewComponent, {
              ':componentId': componentId,
            }),
          },
          { path: i18n.breadcrumbLevel3, href: '#' },
        ]}
        content={renderContent()}
        contentType="default"
        tools={renderTools()}
      />
    </>
  );

  function renderComponentVersionWizard(key: string, componentVersionYamlDefinition: string) {
    if (!componentId || latestComponentYamlDefinitionIsLoading) {
      return <Spinner size="large" />;
    }

    return <ComponentVersionWizard
      key={key}
      projectId={selectedProject.projectId || ''}
      componentId={componentId}
      componentVersion={latestComponentVersion ? { ...latestComponentVersion, componentId: '' } : undefined}
      wizardCancelAction={() =>
        navigateTo(RouteNames.ViewComponent, {
          ':componentId': componentId,
        })
      }
      wizardSubmitAction={createVersion}
      wizardSubmitInProgress={versionCreateInProgress}
      componentVersionYamlDefinition={componentVersionYamlDefinition}
      originalYamlDefinition={latestComponentVersionYamlDefinition || undefined}
      releasedVersions={releasedVersions}
      fetchVersionYaml={fetchVersionYaml}
      activeStepIndex={activeStepIndex}
      setActiveStepIndex={setActiveStepIndex}
      componentVersionDependenciesList={latestComponentVersion?.componentVersionDependencies}
    />;
  }

  function renderContent() {
    return latestComponentVersionYamlDefinition === ''
      ? renderComponentVersionWizard('sampleYaml', sampleComponentDefinitionYaml)
      : renderComponentVersionWizard('latestYaml', latestComponentVersionYamlDefinition);
  }

  function renderTools() {
    return <>
      {activeStepIndex === STEP_1_INDEX && renderStep1InfoPanel()}
      {activeStepIndex === STEP_2_INDEX && renderStep2InfoPanel()}
      {activeStepIndex === STEP_3_INDEX && renderStep3InfoPanel()}
      {activeStepIndex === STEP_4_INDEX && renderStep4InfoPanel()}
    </>;

  }

  function renderStep1InfoPanel() {
    return <HelpPanel header={<h2>{i18n.step1infoPanelHeader}</h2>}><SpaceBetween size={'s'}>
      <Box variant="awsui-key-label">{i18n.step1infoPanelLabel1}</Box>
      <Box variant="p">{i18n.step1infoPanelMessage1}</Box>
      <Box variant="p">{i18n.step1infoPanelMessage2}</Box>
      <Box variant="p">{i18n.step1infoPanelMessage3}</Box>
      <Box>
        <p>{i18n.step1infoPanelMessage4}</p>
        <ul>
          <li>{i18n.step1infoPanelPoint1}</li>
          <li>{i18n.step1infoPanelPoint2}</li>
          <li>{i18n.step1infoPanelPoint3}</li>
        </ul>
      </Box>
    </SpaceBetween>
    </HelpPanel>;
  }

  /* eslint-disable @stylistic/max-len */
  function renderStep2InfoPanel() {
    return <HelpPanel header={<h2>{i18n.step2infoPanelHeader}</h2>}
      footer={<div>
        <h3>
          {i18n.step2LearnMoreLabel}<Icon name="external" />
        </h3>
        <a target="_blank" rel="noopener noreferrer" href="https://docs.aws.amazon.com/imagebuilder/latest/userguide/toe-use-documents.html#document-schema">
          {i18n.step2Link}</a>
      </div>}>
      <SpaceBetween size={'s'}>
        <Box variant="awsui-key-label">{i18n.step2infoPanelLabel1}</Box>
        <Box variant="p">{i18n.step2infoPanelMessage1}</Box>
        <Box variant="p">{i18n.step2infoPanelMessage2}</Box>
      </SpaceBetween>
    </HelpPanel>;
  }

  function renderStep3InfoPanel() {
    return <HelpPanel header={<h2>{i18n.step3infoPanelHeader}</h2>}><SpaceBetween size={'s'}>
      <Box variant="awsui-key-label">{i18n.step3infoPanelLabel1}</Box>
      <Box variant="p">{i18n.step3infoPanelMessage1}</Box>
      <Box variant="p">{i18n.step3infoPanelMessage2}</Box>
    </SpaceBetween>
    </HelpPanel>;
  }

  function renderStep4InfoPanel() {
    return <HelpPanel header={<h2>{i18n.step4infoPanelHeader}</h2>}><SpaceBetween size={'s'}>
      <Box variant="p">{i18n.step4infoPanelMessage1}</Box>
    </SpaceBetween>
    </HelpPanel>;
  }

};