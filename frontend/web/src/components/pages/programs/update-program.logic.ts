import { useEffect, useState } from 'react';
import { projectsAPI } from '../../../services';
import { useNotifications } from '../../layout';
import { i18n } from './update-program.translations';
import { extractErrorResponseMessage } from '../../../utils/api-helpers';
import { useNavigationPaths } from '../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../layout/navigation/navigation.static';
import { selectedProjectState } from '../../../state';
import { useRecoilValue } from 'recoil';
import { useProjectsSwitch } from '../../../hooks';



export function useUpdateProgram() {
  const {
    showErrorNotification,
    showSuccessNotification,
    clearNotifications
  } = useNotifications();
  const { navigateTo } = useNavigationPaths();
  const selectedProject = useRecoilValue(selectedProjectState);
  const { getProjects } = useProjectsSwitch({ skipFetch: true });

  const [isLoading, setIsLoading] = useState(false);
  const [isFetchSuccessful, setIsFetchSuccessful] = useState(false);
  const [programName, setProgramName] = useState<string>('');
  const [programDescription, setProgramDescription] = useState<string>('');
  const [isProgramActive, setIsProgramActive] = useState<boolean>(true);

  useEffect(() => {
    clearNotifications();
    setIsLoading(true);

    if (selectedProject.projectId) {
      projectsAPI.getProject(selectedProject.projectId).then(data => {
        setProgramName(data.project.projectName ? data.project.projectName : '');
        setProgramDescription(data.project.projectDescription ? data.project.projectDescription : '');
        setIsProgramActive(data.project.isActive !== undefined ? data.project.isActive : true);
        setIsFetchSuccessful(true);
      }).catch(async e => {
        showErrorNotification({
          header: i18n.errorFetchProgram,
          content: await extractErrorResponseMessage(e),
        });
        setIsFetchSuccessful(false);
      }).finally(() => {
        setIsLoading(false);
      });
    }
  }, []);

  return {
    isLoading,
    programName,
    setProgramName,
    programDescription,
    setProgramDescription,
    isProgramActive,
    setIsProgramActive,
    isFormValid,
    updateProgram
  };

  function isFormValid(): boolean {
    return !!programName.trim() && isFetchSuccessful;
  }

  function updateProgram(): Promise<void> {
    if (!isFormValid() || !selectedProject.projectId) {
      return Promise.resolve();
    }

    clearNotifications();
    setIsLoading(true);

    return projectsAPI.updateProject(
      selectedProject.projectId,
      programName.trim(),
      programDescription.trim(),
      isProgramActive
    ).then(() => {
      showSuccessNotification({
        header: i18n.successUpdateProgramHeader,
        content: i18n.successUpdateProgramContent
      });
      getProjects();
      navigateTo(RouteNames.Programs);
    }
    ).catch(async e => {
      showErrorNotification({
        header: i18n.errorUpdateProgramHeader,
        content: await extractErrorResponseMessage(e)
      });
    }).finally(() => {
      setIsLoading(false);
    });
  }
}