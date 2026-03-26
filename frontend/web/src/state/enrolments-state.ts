import { atom } from 'recoil';
import { GetProjectEnrolmentsResponseItem } from '../services/API/proserve-wb-projects-api';

export const enrolmentsState = atom<GetProjectEnrolmentsResponseItem[]>({
  key: 'enrolments',
  default: []
});
