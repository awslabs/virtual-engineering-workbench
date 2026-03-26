
import {
  UserProfile,
  DEFAULT_USER_PROFILE,
} from './user-profile.state';
import {
  GetUserProfileResponse as GetProvisioningUserProfileResponse,
  GetUserProfileResponseFeature,
  MaintenanceWindow,
  UpdateUserProfileRequest as UpdateUserProfileRequestProvisioning
} from '../../services/API/proserve-wb-provisioning-api';
import useSWR from 'swr';


type ProvisioningServiceAPI = {
  getUserProfile: () => Promise<GetProvisioningUserProfileResponse>,
  updateUserProfile: (updateUserProfileRequest: UpdateUserProfileRequestProvisioning) => Promise<object>,
};


type ServiceAPIs = {
  provisioningAPI: ProvisioningServiceAPI,
};

const FETCH_KEY = 'users/profiles';

function prepareFeatures(features?: GetUserProfileResponseFeature[]) {
  return features?.map(f => ({
    version: f.version || 'v0.0.0',
    feature: f.feature || 'undefined',
    description: 'Some description',
    enabled: f.enabled || false,
  })) || [];
}

// eslint-disable-next-line complexity
function prepareUserProfile(
  rawData: GetProvisioningUserProfileResponse
): UserProfile {
  const profile: UserProfile = { ...DEFAULT_USER_PROFILE };

  if (rawData.preferredRegion) {
    profile.preferredRegion = rawData.preferredRegion;
  }

  if (rawData.preferredNetwork) {
    profile.preferredNetwork = rawData.preferredNetwork;
  }

  if (rawData.applicationVersion) {
    profile.applicationVersion = rawData.applicationVersion;
  }

  if (rawData.enabledRegions) {
    profile.enabledRegions = rawData.enabledRegions;
  }

  if (rawData.preferredMaintenanceWindows) {
    profile.preferredMaintenanceWindows = rawData.preferredMaintenanceWindows;
  }

  profile.preferredRegionSet = !!rawData.preferredRegion;
  profile.enabledFeatures = prepareFeatures(rawData.enabledFeatures);

  if (rawData.applicationVersionBackend) {
    profile.applicationVersionBackend = rawData.applicationVersionBackend;
  }

  if (rawData.applicationVersionFrontend) {
    profile.applicationVersionFrontend = rawData.applicationVersionFrontend;
  }

  return profile;
}

type UserProfileProps = {
  serviceAPIs: ServiceAPIs,
};

export function useUserProfile({ serviceAPIs }: UserProfileProps) {
  const fetcherFactory = () => async (): Promise<UserProfile> => {
    const provisioningRes = await serviceAPIs.provisioningAPI.getUserProfile();
    const profile = prepareUserProfile(provisioningRes);

    if (!provisioningRes.preferredMaintenanceWindows) {
      updateUserProfile(
        profile.preferredRegion,
        profile.preferredNetwork,
        profile.preferredMaintenanceWindows,
      );
    }

    return profile;
  };

  const { data, error, isLoading, mutate } = useSWR(
    FETCH_KEY,
    fetcherFactory(),
    {
      shouldRetryOnError: false,
    });

  return {
    userProfile: data || DEFAULT_USER_PROFILE,
    updateUserProfile,
    getUserProfile: mutate,
    error,
    userProfileLoading: isLoading,
    userProfileLoaded: !!data
  };
  async function updateUserProfile(
    preferredRegion: string,
    preferredNetwork: string,
    preferredMaintenanceWindows: MaintenanceWindow[],

  ) {
    await serviceAPIs.provisioningAPI.updateUserProfile({
      preferredRegion,
      preferredNetwork,
      preferredMaintenanceWindows
    });

    await mutate(profile => {
      const p = profile as UserProfile;
      if (p) {
        p.preferredNetwork = preferredNetwork;
        p.preferredRegion = preferredRegion;
        p.preferredMaintenanceWindows = preferredMaintenanceWindows;
      }
      return p;
    }, { revalidate: false });
  }
}