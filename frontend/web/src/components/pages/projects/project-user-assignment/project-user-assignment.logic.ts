import { useState } from 'react';
import { projectsAPI } from '../../../../services';
import { ProjectRoles } from '../../../../state';
import { useNotifications } from '../../../layout';
import { SelectProps } from '@cloudscape-design/components';
import { DEFAULT_SELECT_ROLE_OPTION } from './project-user-assignment-roles';

const i18n = {
  assignmentSuccessHeader: 'The user has been successfully onboarded to the program',

  assignmentSuccessContent: `The user will then be informed by email about their 
  onboarding and the roles assigned to them in the program. 
  Please refer to the table below to verify the status.`,
  assignmentSuccessError: 'Unable to assign user.'
};

type ProjectUserAssignmentProps = {
  projectId: string,
};


const useProjectUserAssignment = ({ projectId }: ProjectUserAssignmentProps) => {
  const [userId, setUserId] = useState<string>('');
  const [newMemberRoleLevel, setNewMemberRoleLevel] = useState<SelectProps.Option>(
    DEFAULT_SELECT_ROLE_OPTION
  );
  const [userAssignmentInProgress, setUserAssignmentInProgress] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const { showErrorNotification, showSuccessNotification } = useNotifications();

  const USER_ID = /^[A-Za-z0-9]{1,50}$/u;

  return {
    userId,
    setUserId,
    newMemberRoleLevel,
    setNewMemberRoleLevel,
    isFormValid,
    userAssignmentInProgress,
    assignUser,
    showErrorNotification,
    isUserIdValid,
    isSubmitted
  };

  function isUserIdValid() {
    return USER_ID.test(userId);
  }

  function isFormValid() {
    const emptyArrayCount = 0;
    return isUserIdValid() && getSelectedRoles().length > emptyArrayCount;
  }

  function assignUser() {
    if (!isFormValid()) {
      setIsSubmitted(true);
      return Promise.reject();
    }

    const assignedRole = getSelectedRoles();

    setUserAssignmentInProgress(true);

    return projectsAPI.assignProjectUser(projectId, {
      userId: userId.trim(),
      roles: assignedRole
    }).then(() => {
      showSuccessNotification({
        header: i18n.assignmentSuccessHeader,
        content: i18n.assignmentSuccessContent
      });
    }).finally(() => {
      setUserAssignmentInProgress(false);
      setIsSubmitted(false);
    });
  }

  // eslint-disable-next-line complexity
  function getSelectedRoles() {
    switch (newMemberRoleLevel.value) {
      case '1':
        return [ProjectRoles.PlatformUser];
      case '2':
        return [ProjectRoles.BetaUser];
      case '3':
        return [ProjectRoles.ProductContributor];
      case '4':
        return [ProjectRoles.PowerUser];
      case '5':
        return [ProjectRoles.ProgramOwner];
      case '6':
        return [ProjectRoles.Admin];
      default:
        return [];
    }
  }
};

export { useProjectUserAssignment };