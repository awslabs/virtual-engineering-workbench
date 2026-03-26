/* eslint-disable complexity */
import { useParams } from 'react-router-dom';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../../../layout/navigation/navigation.static';
import { WorkbenchAppLayout } from '../../../../layout/workbench-app-layout/workbench-app-layout';
import { i18n } from './update-component-version.translations';
import { Box, HelpPanel, Icon, SpaceBetween, Spinner } from '@cloudscape-design/components';
import { useUpdateComponentVersion } from './update-component-version.logic';
import { useRecoilValue } from 'recoil';
import { selectedProjectState } from '../../../../../state';
import { ComponentVersionWizard } from '../shared';
import { useState } from 'react';

const EMPTY_ARRAY_LENGTH = 0;
const STEP_1_INDEX = 0;
const STEP_2_INDEX = 1;
const STEP_3_INDEX = 2;
const STEP_4_INDEX = 3;

export const UpdateComponentVersion = () => {
  const selectedProject = useRecoilValue(selectedProjectState);
  if (!selectedProject.projectId) {
    return <Spinner />;
  }

  const { getPathFor, navigateTo } = useNavigationPaths();
  const { componentId, versionId } = useParams();
  const [activeStepIndex, setActiveStepIndex] = useState(EMPTY_ARRAY_LENGTH);

  if (!componentId) {
    navigateTo(RouteNames.Components);
    return <></>;
  }

  const {
    yamlDefinition,
    componentVersion,
    isComponentVersionLoading,
    versionUpdateInProgress,
    updateVersion,
    releasedVersions,
    latestReleasedYamlDefinition,
    fetchVersionYaml,
  } = useUpdateComponentVersion({
    projectId: selectedProject.projectId,
    componentId: componentId,
    versionId: versionId || '',
  });

  function renderContent() {
    if (!componentVersion || isComponentVersionLoading) {
      return <Spinner />;
    }
    return <ComponentVersionWizard
      projectId={selectedProject.projectId || ''}
      componentId={componentId || ''}
      wizardCancelAction={() =>
        navigateTo(RouteNames.ViewComponentVersion, {
          ':componentId': componentId,
          ':versionId': versionId,
        })
      }
      wizardSubmitAction={updateVersion}
      wizardSubmitInProgress={versionUpdateInProgress}
      componentVersionYamlDefinition={yamlDefinition}
      componentVersion={componentVersion}
      originalYamlDefinition={latestReleasedYamlDefinition}
      releasedVersions={releasedVersions}
      fetchVersionYaml={fetchVersionYaml}
      activeStepIndex={activeStepIndex}
      setActiveStepIndex={setActiveStepIndex}
    />;
  }

  return (
    <>
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
        contentType='default'
        tools={renderTools()}
      />
    </>
  );

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
      <Box>
        <p>{i18n.step1infoPanelMessage3}</p>
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