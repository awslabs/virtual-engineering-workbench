import { useEffect, useState } from 'react';
import { projectsAPI } from '../../../../services';
import { GetProjectAssignmentsResponseItem } from '../../../../services/API/proserve-wb-projects-api';
import { extractErrorResponseMessage } from '../../../../utils/api-helpers';
import { useNotifications } from '../../../layout';

const i18n = {
  userFetchErrorHeader: 'Unable to fetch project users.',
  userUnassignSuccess: 'The user has been successfully offboarded from the program',
  userUnassignError: 'Unable to unassign users',
  // eslint-disable-next-line @stylistic/max-len
  userUnassignSuccessContent: 'The user will then be informed by email about their offboarding from the program. Please refer to the table below to verify the status.'
};

type ProjectUsersProps = {
  projectId: string,
};

const useProjectUsers = ({ projectId }: ProjectUsersProps) => {
  const [projectUsers, setProjectUsers] = useState<GetProjectAssignmentsResponseItem[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [userUnassignInProgress, setUserUnassignInProgress] = useState(false);

  const { showErrorNotification, showSuccessNotification } = useNotifications();

  useEffect(() => {
    loadProjectUsers();
  }, []);

  return {
    projectUsers,
    usersLoading: usersLoading,
    loadProjectUsers,
    unassignUsers,
    userUnassignInProgress,
  };

  function loadProjectUsers() {
    setUsersLoading(true);

    projectsAPI.
      getProjectUsers(projectId).
      then(response => {
        setProjectUsers(response.assignments || []);
      }).catch(async e => {
        showErrorNotification({
          header: i18n.userFetchErrorHeader,
          content: await extractErrorResponseMessage(e)
        });
      }).finally(() => {
        setUsersLoading(false);
      });
  }

  function unassignUsers(userIds: string[]) {

    setUserUnassignInProgress(true);

    projectsAPI.removeProjectUsers(projectId, { userIds: userIds })
      .then(() => {
        showSuccessNotification({
          header: i18n.userUnassignSuccess,
          content: i18n.userUnassignSuccessContent,
        });
      })
      .then(() => {
        loadProjectUsers();
      })
      .catch(async (e) => {
        showErrorNotification({
          header: i18n.userUnassignError,
          content: await extractErrorResponseMessage(e)
        });
      })
      .finally(() => {
        setUserUnassignInProgress(false);
      });
  }
};

export { useProjectUsers };