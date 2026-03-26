import {
  USER_ROLE_DESCRIPTION,
  USER_ROLE_LEVEL_MAP, USER_ROLE_MAP
} from '../components/pages/projects/project-details/project-users.static';
import { ProjectRoles } from '../state';

interface GetRolesInformationReturnValue {
  description: string,
  name: string,
  lvl: string,
}

export function getRoleInformation(role: ProjectRoles): GetRolesInformationReturnValue {
  return {
    name: USER_ROLE_MAP[role],
    lvl: USER_ROLE_LEVEL_MAP[role],
    description: USER_ROLE_DESCRIPTION[role],
  };
}

export class ProjectRole {
  name!: string;
  lvl!: string;
  description!: string;
  constructor(role: ProjectRoles) {
    this.name = USER_ROLE_MAP[role];
    this.lvl = USER_ROLE_LEVEL_MAP[role];
    this.description = USER_ROLE_DESCRIPTION[role];
  }

  toString() {
    return `Lvl ${this.lvl} - ${this.name}`;
  }
}
