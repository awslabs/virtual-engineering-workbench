// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { WorkbenchAppLayout } from '../../layout/workbench-app-layout/workbench-app-layout';
import {
  Button,
  Checkbox,
  Container,
  FormField,
  Header,
  HelpPanel,
  Input,
  SpaceBetween
} from '@cloudscape-design/components';
import { BreadcrumbItem } from '../../layout';
import { useRoleAccessToggle } from '../../../hooks/role-access-toggle';
import { RoleBasedFeature } from '../../../state';
import { useNavigationPaths } from '../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../layout/navigation/navigation.static';
import { i18n } from './create-program.translations';
import { useCreateProgram } from './create-program.logic';

const createProgram = () => {
  const isFeatureAccessible = useRoleAccessToggle();
  const { navigateTo, getPathFor } = useNavigationPaths();

  const {
    isLoading,
    programName,
    setProgramName,
    programDescription,
    setProgramDescription,
    isProgramActive,
    setIsProgramActive,
    createProgram,
    isSubmitted,
    isProgramNameValid
  } = useCreateProgram();

  return (
    <>
      <WorkbenchAppLayout
        breadcrumbItems={getBreadcrumbItems()}
        content={isFeatureAccessible(RoleBasedFeature.ProgramAdministration) ? renderContent() : null}
        contentType="default"
        tools={renderTools()}
        customHeader={renderHeader()}
        navigationHide
      />
    </>
  );

  function getBreadcrumbItems(): BreadcrumbItem[] {
    return [
      { path: i18n.breadCrumbItem1, href: getPathFor(RouteNames.Programs) },
      { path: i18n.breadCrumbItem2, href: '#' }
    ];
  }

  function renderHeader() {
    return <Header
      variant='awsui-h1-sticky'
      actions={
        <SpaceBetween direction="horizontal" size="xs">
          <Button onClick={() => {
            navigateTo(RouteNames.Programs);
          }}>
            {i18n.cancelButtonText}
          </Button>
          <Button
            onClick={createProgram}
            variant='primary'
            loading={isLoading}
            data-test="create-continue"
          >
            {i18n.createButtonText}
          </Button>
        </SpaceBetween>
      }
    >{i18n.infoHeader}</Header>;
  }

  function renderContent() {
    return <>
      <Container
        header={<Header variant="h2">{i18n.detailsContainerTitle}</Header>}
      >
        <SpaceBetween size="l">
          {renderProgramNameInput()}
          {renderProgramDescriptionInput()}
          {renderProgramIsActiveCheckbox()}
        </SpaceBetween>
      </Container>
    </>;
  }

  function renderTools() {
    return (
      <HelpPanel
        header={<h2>{i18n.infoHeader}</h2>}
      >
        <p>{i18n.infoDescription}</p>
      </HelpPanel>
    );
  }

  function displayConstraintText(message: string, isValid: boolean) {
    return (!isSubmitted || isSubmitted && isValid) && message;
  }

  function displayErrorMessage(message: string, isValid: boolean) {
    return isSubmitted && !isValid && message;
  }

  function renderProgramNameInput() {
    return <>
      <FormField
        constraintText={displayConstraintText(
          i18n.programNameValidationMessage,
          isProgramNameValid()
        )}
        errorText={displayErrorMessage(
          i18n.programNameValidationMessage,
          isProgramNameValid()
        )}
        label={i18n.inputName}
      >
        <Input
          value={programName}
          onChange={({ detail: { value } }) => setProgramName(value)}
          data-test="program-name"
        />
      </FormField>
    </>;
  }

  function renderProgramDescriptionInput() {
    return <>
      <FormField
        constraintText=''
        label={i18n.inputDescription}
      >
        <Input
          value={programDescription}
          onChange={({ detail: { value } }) => setProgramDescription(value)}
          data-test="program-description"
        />
      </FormField>
    </>;
  }

  function renderProgramIsActiveCheckbox() {
    return <>
      <Checkbox
        checked={isProgramActive}
        onChange={({ detail }) => setIsProgramActive(detail.checked)}
        data-test="program-is-active"
      >
        {i18n.checkboxIsActive}
      </Checkbox>
    </>;
  }

};

export { createProgram as CreateProgram };