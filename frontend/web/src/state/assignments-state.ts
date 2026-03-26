import { atom, selector } from 'recoil';
import { selectedProjectState } from '.';
import { GetProjectAssignmentsResponseItem } from '../services/API/proserve-wb-projects-api';
import { ProjectAssignment } from '../services/API/proserve-wb-projects-api/models';

const assignmentsState = atom<GetProjectAssignmentsResponseItem[]>({
  key: 'assignments',
  default: []
});

const filteredAssignmentsForSelectedProjectState = selector<GetProjectAssignmentsResponseItem[]>({
  key: 'filteredAssignmentsForSelectedProject',
  get: ({ get }) => {
    const list = get(assignmentsState);
    const selectedProject = get(selectedProjectState);
    return list.filter(
      (assignment: ProjectAssignment) => assignment.projectId === selectedProject.projectId
    );
  },
});

export { assignmentsState, filteredAssignmentsForSelectedProjectState };
