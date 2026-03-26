import {
  Box,
  Header,
  HelpPanel,
  Icon,
  SpaceBetween,
  Spinner,
} from '@cloudscape-design/components';
import { WorkbenchAppLayout } from '../../../../layout/workbench-app-layout/workbench-app-layout';
import { i18n } from './create-pipeline.translations';
import { useRecoilValue } from 'recoil';
import { selectedProjectState } from '../../../../../state';
import { useCreatePipeline } from './create-pipeline.logic';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../../../layout/navigation/navigation.static';
import { PipelineForm } from '../shared/pipeline-form/pipeline-form';

export const CreatePipeline = () => {
  const selectedProject = useRecoilValue(selectedProjectState);
  if (selectedProject.projectId === undefined) {
    return <Spinner />;
  }

  const {
    pipeline,
    setPipeline,
    createPipeline,
    isCreateInProgress,
  } = useCreatePipeline({ projectId: selectedProject.projectId });

  const { getPathFor } = useNavigationPaths();

  return (
    <>
      <WorkbenchAppLayout
        breadcrumbItems={[
          { path: i18n.breadcrumbLevel1, href: getPathFor(RouteNames.Pipelines) },
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
    return <PipelineForm
      pipeline={pipeline}
      setPipeline={setPipeline}
      onSubmit={createPipeline}
      isSubmitInProgress={isCreateInProgress}
    />
    ;
  }

  function renderTools() {
    return (
      <HelpPanel header={<h2>{i18n.infoPanelHeader}</h2>}
        footer={<div>
          <h3>
            {i18n.infoPanelLearnMore}<Icon name="external" />
          </h3>
          <a href="https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-cron-expressions.html">
            {i18n.infoPanelLink}</a>
        </div>}>
        <SpaceBetween size={'s'}>
          <Box variant="awsui-key-label">{i18n.infoPanelLabel1}</Box>
          <Box variant="p">{i18n.infoPanelMessage1}</Box>
          <Box variant="p">{i18n.infoPanelMessage2}</Box>
          <Box variant="p">{i18n.infoPanelMessage3}</Box>
          <Box variant="p">{i18n.infoPanelMessage4}</Box>
          <Box variant="p">{i18n.infoPanelMessage5}</Box>
          <Box variant="p">{i18n.infoPanelMessage6}</Box>
          <Box variant="p">{i18n.infoPanelMessage7}</Box>
        </SpaceBetween>
      </HelpPanel>
    );
  }
};
