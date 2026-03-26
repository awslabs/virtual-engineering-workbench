import { useState } from 'react';
import { projectsAPI } from '../../../../services';
import { ProjectRoles } from '../../../../state';
import { extractErrorResponseMessage } from '../../../../utils/api-helpers';
import { useNotifications } from '../../../layout';
import { SelectProps } from '@cloudscape-design/components';
import { DEFAULT_SELECT_ROLE_OPTION } from '../project-user-assignment/project-user-assignment-roles';

const i18n = {
  reAssignmentSuccessHeader: 'The user roles have been successfully updated',
  // eslint-disable-next-line @stylistic/max-len
  reAssignmentSuccessContent: 'The user will then be informed by email about the update. Please refer to the table below to verify the roles.',
  reAssignmentSuccessError: 'Unable to reassign user.',
  rolesFetchError: 'Unable to fetch user roles.'
};

type ProjectUserAssignmentProps = {
  projectId: string,
  loadProjectUsers: () => void,
};


const useProjectUserReAssignment = ({ projectId, loadProjectUsers }: ProjectUserAssignmentProps) => {
  const [memberRoleLevel, setMemberRoleLevel] = useState<SelectProps.Option>(DEFAULT_SELECT_ROLE_OPTION);
  const [userReAssignmentInProgress, setUserReAssignmentInProgress] = useState(false);

  const { showErrorNotification, showSuccessNotification } = useNotifications();

  return {
    isFormValid,
    userReAssignmentInProgress,
    reAssignUsers,
    showErrorNotification,
    memberRoleLevel,
    setMemberRoleLevel
  };


  function isFormValid() {
    const emptyArrayCount = 0;
    return getSelectedRoles().length > emptyArrayCount;
  }


  function reAssignUsers(userIds: string[]): Promise<void> {
    if (!isFormValid()) {
      return Promise.resolve();
    }

    const assignedRole = getSelectedRoles();

    setUserReAssignmentInProgress(true);
    return projectsAPI.reassignProjectUsers(projectId, {
      roles: assignedRole, userIds: userIds
    }).then(() => {
      showSuccessNotification({
        header: i18n.reAssignmentSuccessHeader,
        content: i18n.reAssignmentSuccessContent
      });
      loadProjectUsers();
    }).catch(async e => {
      showErrorNotification({
        header: i18n.reAssignmentSuccessError,
        content: await extractErrorResponseMessage(e)
      });
    }).finally(() => {
      setUserReAssignmentInProgress(false);
    });
  }

  // eslint-disable-next-line complexity
  function getSelectedRoles() {
    switch (memberRoleLevel.value) {
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
        return [ProjectRoles.PlatformUser];
    }
  }
};

export { useProjectUserReAssignment };