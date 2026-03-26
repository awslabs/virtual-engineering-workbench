import { useEffect, useCallback } from 'react';
import { useRecoilState, useRecoilValue, useSetRecoilState } from 'recoil';
import { useNotifications } from '../components/layout';
import { projectsAPI } from '../services';
import {
  Project,
  projectsState,
  enrolmentsState,
  assignmentsState,
  SelectedProject,
  selectedProjectState,
  projectsLoadingState,
  filteredProjectsWithAnyRole
} from '../state';
import {
  loggedInUserState
} from '../components/session-management/logged-user';
import { projectsInitialisedState } from '../state/projects-init-state';
import { projectsLoadedState } from '../state/projects-loaded-state';
import { extractErrorResponseMessage } from '../utils/api-helpers';
import { useLocalStorage } from './local-storage';

/* eslint complexity: "off" */

type ProjectsSwitch = {
  projects: Project[],
  userProjects: Project[],
  selectedProject: SelectedProject,
  switchToProject: (projectId: string) => void,
  loadingProjects: boolean,
  projectsLoaded: boolean,
  getProjects: () => void,
  projectsInitialised: boolean,
};

type Props = {
  skipFetch?: boolean,
};

function useProjectsSwitch({ skipFetch } : Props): ProjectsSwitch {
  const [user] = useRecoilState(loggedInUserState);
  const [projects, setProjects] = useRecoilState(projectsState);
  const userProjects = useRecoilValue(filteredProjectsWithAnyRole);
  const setEnrolments = useSetRecoilState(enrolmentsState);
  const setAssignments = useSetRecoilState(assignmentsState);
  const [selectedProject, setSelectedProject] = useRecoilState(selectedProjectState);
  const [loadingProjects, setLoadingProjects] = useRecoilState(projectsLoadingState);
  const [projectsLoaded, setProjectsLoaded] = useRecoilState(projectsLoadedState);
  const [projectsInitialised, setProjectsInitialised] = useRecoilState(projectsInitialisedState);
  const { showErrorNotification, clearNotifications } = useNotifications();

  const [lastSelectedProject, setLastSelectedProject] = useLocalStorage('projects#last-selected');

  const getProjects = useCallback(() => {
    setLoadingProjects(true);
    projectsAPI.getProjects().then(data => {
      setProjects(data.projects.map(p => ({
        id: p.projectId,
        name: p.projectName ?? '',
        description: p.projectDescription ?? '',
        isActive: p.isActive ?? false,
        roles: (data.assignments?.find(x =>
          x.projectId === p.projectId)?.roles || []).map(x => x.toUpperCase())
      })));
      setEnrolments(data?.enrolments ?? []);
      setAssignments(data?.assignments ?? []);
    }).catch(async e => {
      showErrorNotification({
        header: 'Unable to fetch projects.',
        content: await extractErrorResponseMessage(e)
      });
    }).finally(() => {
      setLoadingProjects(false);
      setProjectsLoaded(true);
    });
  }, [
    setLoadingProjects,
    setProjects,
    setEnrolments,
    setAssignments,
    setProjectsLoaded,
    showErrorNotification,
  ]);

  useEffect(() => {
    if (!projects.length && user?.user && !loadingProjects && !projectsLoaded && !skipFetch) {
      clearNotifications();
      getProjects();
    }
  }, [
    projects,
    user,
    loadingProjects,
    projectsLoaded,
    skipFetch,
    clearNotifications,
    getProjects
  ]);

  useEffect(() => {
    /* eslint @typescript-eslint/no-magic-numbers: "off" */
    if (userProjects.length >= 1) {
      const lastProject = userProjects.find(p => p.id === lastSelectedProject);
      if (lastProject !== undefined) {
        setSelectedProject({
          projectId: lastProject.id,
          projectName: lastProject.name,
          projectDescription: lastProject.description,
          isActive: lastProject.isActive,
          roles: lastProject.roles,
        });
      }
    }
    if (projectsLoaded) {
      setProjectsInitialised(true);
    }
  }, [userProjects, lastSelectedProject, setSelectedProject, projectsLoaded, setProjectsInitialised]);

  useEffect(() => {
    if (selectedProject?.projectId) {
      setLastSelectedProject(selectedProject.projectId);
    }
  }, [selectedProject, setLastSelectedProject]);

  return {
    projects,
    userProjects,
    selectedProject,
    switchToProject,
    loadingProjects,
    projectsLoaded,
    getProjects,
    projectsInitialised,
  };

  function switchToProject(projectId: string) {
    const project = projects.find(p => p.id === projectId);
    setSelectedProject({
      projectId: project?.id,
      projectName: project?.name,
      projectDescription: project?.description,
      isActive: project?.isActive,
      roles: project?.roles,
    });
  }
}

export { useProjectsSwitch };
