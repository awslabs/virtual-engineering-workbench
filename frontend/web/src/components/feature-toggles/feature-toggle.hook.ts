import {
  Feature,
  featuresToggleState,
  FeatureToggleItem,
  featureTogglesInitialised,
} from './feature-toggle.state';
import { useRecoilState } from 'recoil';
import { useUserProfile } from '../user-preferences/user-profile.hook';
import { useCallback, useEffect, useMemo } from 'react';
import { FeatureToggleConfigItem } from './features';
import { getApis } from '../../utils/api-helpers.ts';

export function getUserProfileFeatureToggles(toggles: FeatureToggleConfigItem[]): FeatureToggleItem[] {
  return toggles
    .filter(uf => {
      return Object.values<string>(Feature).includes(uf.feature);
    })
    .map(uf => {
      return {
        enabled: uf.enabled,
        feature: Feature[uf.feature as keyof typeof Feature],
        version: uf.version
      } as FeatureToggleItem;
    });
}

export function mergeFeatureToggles(
  userFeatureToggles: FeatureToggleItem[],
  baseFeatureToggles: FeatureToggleItem[]): FeatureToggleItem[] {
  const allFeatureToggles = [...userFeatureToggles, ...baseFeatureToggles];
  return allFeatureToggles
    .filter((f, index) => {
      return allFeatureToggles.findIndex((ft) => ft.feature === f.feature) === index;
    });
}

type FeatureToggleResponse = {
  isFeatureEnabled: (feature: Feature) => boolean,
  featuresInitialised: boolean,
};

export function useFeatureToggles(): FeatureToggleResponse {
  const [baseFeatureToggles] = useRecoilState(featuresToggleState);
  const [featuresInitialised, setFeaturesInitialised] = useRecoilState(featureTogglesInitialised);

  const { userProfile, userProfileLoaded } = useUserProfile({
    serviceAPIs: getApis()
  });

  const activeFeatureToggles = useMemo(() => {
    const userFeatureToggles = getUserProfileFeatureToggles(userProfile.enabledFeatures);
    return mergeFeatureToggles(
      userFeatureToggles,
      baseFeatureToggles
    );
  }, [baseFeatureToggles, userProfile]);

  useEffect(() => {
    if (userProfileLoaded) {
      setFeaturesInitialised(true);
    }
  }, [userProfileLoaded, setFeaturesInitialised]);

  const isFeatureEnabled = useCallback((feature: Feature) => {
    return activeFeatureToggles
      .find(x => x.feature === feature && x.enabled) !== undefined;
  }, [activeFeatureToggles]);

  return {
    isFeatureEnabled,
    featuresInitialised,
  };
}