import { atom } from 'recoil';

export type SelectedProject = {
  projectId?: string,
  projectName?: string,
  projectDescription?: string,
  isActive?: boolean,
  roles?: string[],
};


const selectedProjectState = atom<SelectedProject>({
  key: 'selected-project',
  default: {}
});

export { selectedProjectState };
