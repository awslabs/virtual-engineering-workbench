/* eslint complexity: "off" */

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
import { BreadcrumbItem } from '../../../layout';
import { WorkbenchAppLayout } from '../../../layout/workbench-app-layout/workbench-app-layout';
import { useProjectUserAssignment } from './project-user-assignment.logic';
import { extractErrorResponseMessage } from '../../../../utils/api-helpers';
import { ProjectUserAssignmentRoles } from './project-user-assignment-roles';
import { selectedProjectState } from '../../../../state';
import { useNavigationPaths } from '../../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../../layout/navigation/navigation.static';

// eslint-disable-next-line @typescript-eslint/no-empty-object-type
interface Params { }

const i18n = {
  breadcrumbLevel1: 'Administration: Members',
  breadcrumbLevel2: 'Onboard member',
  breadcrumbProjectUnknown: '(...)',
  buttonCancel: 'Cancel',
  buttonAssign: 'Continue',
  detailsContainerTitle: 'Settings',
  detailsInputUserId: 'User ID',
  checkboxFieldLabel: 'Roles',
  userCheckbox: 'User',
  userCheckboxDescription: 'Users with this role will be able to provision workbenches.',
  adminCheckbox: 'Admin',
  adminCheckboxDescription: 'Users with this role will be able to onboard AWS accounts and manage users.',
  assignmentHandlerError: 'Unable to assign user.',
  pageHeader: 'Onboard member',
  userIdValidationMessage:
    'User ID should be between 1 and 50 characters in alphanumeric, without spaces and special characters.',
  userIdPlaceholder: 'Enter user ID',
  infoPanelHeader: 'Onboard member',
  infoPanelLabel1: 'What can I accomplish here?',
  infoPanelMessage1: 'Enter a User ID for the member you’d like to add.',
  infoPanelMessage2: 'Select a role for the user. The role can be upgraded or downgraded at a later time.',
};

const projectUserAssignment: FC<Params> = () => {
  const selectedProject = useRecoilValue(selectedProjectState);
  const { navigateTo, getPathFor } = useNavigationPaths();

  if (!selectedProject) {
    navigateTo(RouteNames.Programs);
  }

  const {
    userId,
    setUserId,
    newMemberRoleLevel,
    setNewMemberRoleLevel,
    userAssignmentInProgress,
    assignUser,
    showErrorNotification,
    isUserIdValid,
    isSubmitted,
    isFormValid
  } = useProjectUserAssignment({ projectId: selectedProject.projectId || '' });

  const handleAssignUser = async () => {
    try {
      await assignUser();
      if (isFormValid()) {
        navigateTo(RouteNames.ProjectMembers);
      }
    } catch (e) {
      showErrorNotification({
        header: i18n.assignmentHandlerError,
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
            navigateTo(RouteNames.ProjectMembers);
          }}>
            {i18n.buttonCancel}
          </Button>
          <Button
            variant="primary"
            onClick={handleAssignUser}
            loading={userAssignmentInProgress}
            data-test="continue-onboarding-button"
          >
            {i18n.buttonAssign}
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
          {renderUserIdInput()}
          {renderUserRoleCheckboxes()}
        </SpaceBetween>
      </Container>
    </>;
  }


  function getBreadcrumbItems(): BreadcrumbItem[] {
    return [
      { path: i18n.breadcrumbLevel1, href: getPathFor(RouteNames.ProjectMembers) },
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
        </SpaceBetween>
      </HelpPanel>
    );
  }

  function renderUserIdInput() {
    return <>
      <FormField
        constraintText={(!isSubmitted || isSubmitted && isUserIdValid()) && i18n.userIdValidationMessage}
        errorText={isSubmitted && !isUserIdValid() && i18n.userIdValidationMessage}
        label={i18n.detailsInputUserId}
      >
        <Input
          data-test="user-id-input"
          value={userId}
          placeholder={i18n.userIdPlaceholder}
          onChange={({ detail: { value } }) => setUserId(value)}
        />
      </FormField>
    </>;
  }

  function renderUserRoleCheckboxes() {
    return <ProjectUserAssignmentRoles
      memberRoleLevel={newMemberRoleLevel}
      setMemberRoleLevel={setNewMemberRoleLevel}
    />;
  }

};



export { projectUserAssignment as ProjectUserAssignment };
