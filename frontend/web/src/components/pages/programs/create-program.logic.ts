import { useState } from 'react';
import { projectsAPI } from '../../../services';
import { useNotifications } from '../../layout';
import { i18n } from './create-program.translations';
import { extractErrorResponseMessage } from '../../../utils/api-helpers';
import { useNavigationPaths } from '../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../layout/navigation/navigation.static';
import { useProjectsSwitch } from '../../../hooks';

const PROGRAM_NAME = /^[A-Za-z0-9_ -]{1,50}$/u;

export function useCreateProgram() {
  const {
    showErrorNotification,
    showSuccessNotification,
    clearNotifications
  } = useNotifications();
  const { navigateTo } = useNavigationPaths();
  const { getProjects } = useProjectsSwitch({ skipFetch: true });

  const [isLoading, setIsLoading] = useState(false);
  const [programName, setProgramName] = useState<string>('');
  const [programDescription, setProgramDescription] = useState<string>('');
  const [isProgramActive, setIsProgramActive] = useState<boolean>(true);
  const [isSubmitted, setIsSubmitted] = useState(false);

  return {
    isLoading,
    programName,
    setProgramName,
    programDescription,
    setProgramDescription,
    isProgramActive,
    setIsProgramActive,
    isFormValid,
    createProgram,
    isSubmitted,
    isProgramNameValid
  };

  function isFormValid(): boolean {
    return !!programName.trim();
  }

  function isProgramNameValid() {
    return PROGRAM_NAME.test(programName);
  }

  function createProgram(): Promise<void> {
    if (!isFormValid()) {
      setIsSubmitted(true);
      return Promise.resolve();
    }

    clearNotifications();
    setIsLoading(true);

    return projectsAPI.createProject(
      programName.trim(),
      programDescription.trim(),
      isProgramActive
    ).then(() => {
      showSuccessNotification({
        header: i18n.successCreateProgramHeader,
        content: i18n.successCreateProgramContent
      });
      getProjects();
      navigateTo(RouteNames.Programs);
    }
    ).catch(async e => {
      showErrorNotification({
        header: i18n.errorCreateProgramHeader,
        content: await extractErrorResponseMessage(e)
      });
    }).finally(() => {
      setIsLoading(false);
      setIsSubmitted(false);
    });
  }
}