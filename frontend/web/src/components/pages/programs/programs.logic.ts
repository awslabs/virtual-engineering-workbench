import { useState } from 'react';
import { useNotifications } from '../../layout';
import { projectsAPI } from '../../../services';
import { extractErrorResponseMessage } from '../../../utils/api-helpers';
import { i18n } from './programs.translations';
import { useProjectsSwitch } from '../../../hooks';

export const usePrograms = () => {
  const [isLoading, setIsLoading] = useState<string | null >(null);
  const [disabledProjectId, setDisabledProjectId] = useState<string | null>(null);
  const { showErrorNotification, showSuccessNotification } = useNotifications();

  const {
    getProjects
  } = useProjectsSwitch({ skipFetch: true });

  const handleEnrolProgram = async (projectId: string) => {
    try {
      setIsLoading(projectId);
      await projectsAPI.enrolUser(projectId, {});
      showSuccessNotification({
        header: i18n.enrolmentsSuccessTitle,
        content: i18n.enrolmentsSuccessContent
      });
      getProjects();
      setDisabledProjectId(projectId);
    } catch (error) {
      showErrorNotification({
        header: i18n.enrolmentsErrorTitle,
        content: await extractErrorResponseMessage(error)
      });
    } finally {
      setIsLoading(null);
      setDisabledProjectId(null);
    }
  };

  return { handleEnrolProgram, isLoading, disabledProjectId };
};