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
import { useRecoilValue } from 'recoil';
import { BreadcrumbItem } from '../../layout';
import { WorkbenchAppLayout } from '../../layout/workbench-app-layout/workbench-app-layout';
import { i18n } from './add-technology.translations';
import { useAddTechnology } from './add-technology.logic';
import { extractErrorResponseMessage } from '../../../utils/api-helpers';
import { selectedProjectState } from '../../../state';
import { useNavigationPaths } from '../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../layout/navigation/navigation.static';

// eslint-disable-next-line @typescript-eslint/no-empty-object-type
interface Params { }

const addTechnology: FC<Params> = () => {
  const selectedProject = useRecoilValue(selectedProjectState);
  const { navigateTo, getPathFor } = useNavigationPaths();

  const {
    technologyName,
    setTechnologyName,
    technologyDescription,
    setTechnologyDescription,
    isFormValid,
    technologyCreationInProgress,
    addTechnology,
    showErrorNotification,
    isSubmitted,
    isTechnologyNameValid
  } = useAddTechnology({ projectId: selectedProject.projectId || '' });

  const handleAddTechnology = async () => {
    try {
      await addTechnology();
      if (isFormValid()) {
        navigateTo(RouteNames.Technologies);
      }
    } catch (e) {
      showErrorNotification({
        header: i18n.technologyCreationHandlerError,
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
            onClick={handleAddTechnology}
            loading={technologyCreationInProgress}
            data-test="execute-create-technology-btn"
          >
            {i18n.buttonAddTechnology}
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
          <Box variant="p">{i18n.infoPanelMessage2}</Box>
          <Box variant="p">{i18n.infoPanelMessage3}</Box>
        </SpaceBetween>
      </HelpPanel>
    );
  }

  function displayConstraintText(message: string, isValid: boolean) {
    return (!isSubmitted || isSubmitted && isValid) && message;
  }

  function displayErrorMessage(message: string, isValid: boolean) {
    return isSubmitted && !isValid && message;
  }

  function renderTechnologyNameInput() {
    return <>
      <FormField
        constraintText={displayConstraintText(i18n.technologyNameValidationMessage, isTechnologyNameValid())}
        errorText={displayErrorMessage(i18n.technologyNameValidationMessage, isTechnologyNameValid())}
        label={i18n.inputName}
      >
        <Input
          placeholder={i18n.technologyNamePlaceholder}
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
        label={i18n.inputDescription}
      >
        <Input
          placeholder={i18n.technologyDescriptionPlaceholder}
          value={technologyDescription}
          onChange={({ detail: { value } }) => setTechnologyDescription(value)}
          data-test="technology-description-input"
        />
      </FormField>
    </>;
  }
};



export { addTechnology as AddTechnology };
