import { RoleBasedFeature, roleAccessToggleState, selectedProjectState } from '../state';
import { useRecoilState, useRecoilValue } from 'recoil';

export function useRoleAccessToggle(): (projectId: RoleBasedFeature) => boolean {
  const accessibleFeatures = useRecoilValue(roleAccessToggleState);

  const selectedProject = useRecoilState(selectedProjectState);
  const assignedRoles = selectedProject[0].roles;

  function isFeatureAccessible(feature: RoleBasedFeature): boolean {
    let doRoleArraysOverlap = false;
    accessibleFeatures.forEach((feat) => {
      if (feat.feature === feature) {
        const accessRolesForFeature = feat.rolesWithAccess;
        if (assignedRoles) {
          doRoleArraysOverlap = accessRolesForFeature.some(role => assignedRoles.includes(role));
        }
      }
    });

    return doRoleArraysOverlap;
  }
  return isFeatureAccessible;
}
