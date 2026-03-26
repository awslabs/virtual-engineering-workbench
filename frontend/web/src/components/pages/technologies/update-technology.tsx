import {
  Box,
  Button,
  Container,
  FormField,
  Header,
  HelpPanel,
  Input,
  SpaceBetween
} from '@cloudscape-design/components';
import { FC } from 'react';
import { useLocation } from 'react-router-dom';
import { useRecoilValue } from 'recoil';
import { BreadcrumbItem } from '../../layout';
import { WorkbenchAppLayout } from '../../layout/workbench-app-layout/workbench-app-layout';
import { i18n } from './update-technology.translations';
import { useUpdateTechnology } from './update-technology.logic';
import { extractErrorResponseMessage } from '../../../utils/api-helpers';
import { selectedProjectState } from '../../../state';
import { useNavigationPaths } from '../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../layout/navigation/navigation.static';

// eslint-disable-next-line @typescript-eslint/no-empty-object-type
interface Params {}

// eslint-disable-next-line complexity
const updateTechnology: FC<Params> = () => {
  const selectedProject = useRecoilValue(selectedProjectState);
  const { navigateTo, getPathFor } = useNavigationPaths();
  const { state } = useLocation();

  const {
    technologyName,
    setTechnologyName,
    technologyDescription,
    setTechnologyDescription,
    isFormValid,
    technologyCreationInProgress,
    updateTechnology,
    showErrorNotification
  } = useUpdateTechnology({
    projectId: selectedProject.projectId || '',
    techId: state.technologyId || '',
    techName: state.technologyName || '',
    techDescription: state.technologyDescription || ''
  });

  const handleUpdateTechnology = async () => {
    try {
      await updateTechnology();
      navigateTo(RouteNames.Technologies);
    } catch (e) {
      showErrorNotification({
        header: i18n.technologyUpdateHandlerError,
        content: await extractErrorResponseMessage(e)
      });
    }
  };

  return <>
    <WorkbenchAppLayout
      breadcrumbItems={getBreadcrumbItems()}
      content={renderContent()}
      contentType="default"
      tools={renderTools()}
      customHeader={renderHeader()}
    />
  </>;

  function renderHeader() {
    return <Header
      variant='awsui-h1-sticky'
      actions={
        <SpaceBetween direction="horizontal" size="xs">
          <Button onClick={() => {
            navigateTo(RouteNames.Technologies);
          }}>
            {i18n.buttonCancel}
          </Button>
          <Button
            variant="primary"
            disabled={!isFormValid()}
            onClick={handleUpdateTechnology}
            loading={technologyCreationInProgress}
            data-test="execute-update-technology-btn"
          >
            {i18n.buttonUpdateTechnology}
          </Button>
        </SpaceBetween>
      }
    >{i18n.pageHeader}</Header>;
  }

  function renderContent() {
    return <>
      <Container
        header={<Header variant="h2">{i18n.detailsContainerTitle}</Header>}
      >
        <SpaceBetween size="l">
          {renderTechnologyIdInput()}
          {renderTechnologyNameInput()}
          {renderTechnologyDescriptionInput()}
        </SpaceBetween>
      </Container>
    </>;
  }


  function getBreadcrumbItems(): BreadcrumbItem[] {
    return [
      { path: i18n.breadcrumbLevel1, href: getPathFor(RouteNames.Technologies) },
      { path: i18n.breadcrumbLevel2, href: '#' },
    ];
  }

  function renderTools() {
    return (
      <HelpPanel header={<h2>{i18n.infoPanelHeader}</h2>}>
        <SpaceBetween size={'s'}>
          <Box variant="awsui-key-label">{i18n.infoPanelLabel1}</Box>
          <Box variant="p">{i18n.infoPanelMessage1}</Box>
        </SpaceBetween>
      </HelpPanel>
    );
  }

  function renderTechnologyIdInput() {
    return <>
      <FormField
        constraintText=''
        label={i18n.inputId}
      >
        <Input
          value={state.technologyId}
          disabled
        />
      </FormField>
    </>;
  }

  function renderTechnologyNameInput() {
    return <>
      <FormField
        constraintText=''
        label={i18n.inputName}
      >
        <Input
          value={technologyName}
          onChange={({ detail: { value } }) => setTechnologyName(value)}
          data-test="technology-name-input"
        />
      </FormField>
    </>;
  }

  function renderTechnologyDescriptionInput() {
    return <>
      <FormField
        constraintText=''
        label={i18n.inputDescription}
      >
        <Input
          value={technologyDescription}
          onChange={({ detail: { value } }) => setTechnologyDescription(value)}
          data-test="technology-description-input"
        />
      </FormField>
    </>;
  }
};



export { updateTechnology as UpdateTechnology };
