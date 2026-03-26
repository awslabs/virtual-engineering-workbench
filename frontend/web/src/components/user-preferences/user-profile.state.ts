import { FeatureToggleConfigItem } from '../feature-toggles/features';
import { MaintenanceWindow } from '../../services/API/proserve-wb-provisioning-api';
import { DEFAULT_MAINTENANCE_WINDOWS } from '../../utils/maintenance-windows';

export type UserProfile = {
  preferredRegionSet: boolean,
  preferredRegion: string,
  preferredNetwork: string,
  enabledRegions: string[],
  enabledFeatures: FeatureToggleConfigItem[],
  enabledNetworks: string[],
  applicationVersion: string,
  applicationVersionFrontend: string,
  applicationVersionBackend: string,
  preferredMaintenanceWindows: MaintenanceWindow[],
};

export const DEFAULT_USER_PROFILE_REGION = 'us-east-1';
export const DEFAULT_USER_PROFILE_NETWORK = 'NetworkA';


export const DEFAULT_USER_PROFILE = {
  preferredRegionSet: false,
  preferredRegion: DEFAULT_USER_PROFILE_REGION,
  preferredNetwork: DEFAULT_USER_PROFILE_NETWORK,
  enabledRegions: [],
  enabledFeatures: [],
  enabledNetworks: ['NetworkA', 'NetworkB'],
  applicationVersion: '',
  applicationVersionFrontend: '',
  applicationVersionBackend: '',
  preferredMaintenanceWindows: DEFAULT_MAINTENANCE_WINDOWS,
};
