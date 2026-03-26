import {
  getUserProfileFeatureToggles,
  mergeFeatureToggles
} from './feature-toggle.hook';
import { Feature } from './feature-toggle.state';

describe('useFeatureToggles', () => {

  it('should ignore unknown feature names from user profile', () => {
    // ARRANGE
    const featureToggleConfig = [{
      version: '1.0.0',
      feature: 'EvilUnknownFeatures',
      enabled: true,
      environmentOverride: { dev: false },
    }];

    // ACT
    const featureToggles = getUserProfileFeatureToggles(featureToggleConfig);

    // ASSERT
    expect(featureToggles).toEqual([]);
  });

  it('should transform user profile feature toggle configs to feature toggles', () => {
    // ARRANGE
    const featureToggleConfig = [{
      version: '1.0.0',
      feature: Feature.DCVConnectionOptions,
      enabled: true,
      environmentOverride: { dev: false },
    }];

    // ACT
    const featureToggles = getUserProfileFeatureToggles(featureToggleConfig);

    // ASSERT
    expect(featureToggles).toEqual([{
      version: '1.0.0',
      feature: Feature.DCVConnectionOptions,
      enabled: true,
    }]);
  });

  it('should merge workbench, user profile and base feature toggles', () => {
    // ARRANGE
    const userProfileFeatureToggles = [{
      enabled: false,
      version: '1.0.0',
      feature: Feature.BetaUserInfoText,
    }];

    const baseFeatureToggles = [{
      enabled: false,
      version: '1.0.0',
      feature: Feature.ProductMetadata,
    }];

    // ACT
    const featureToggles = mergeFeatureToggles(
      userProfileFeatureToggles,
      baseFeatureToggles
    );

    // ASSERT
    expect(featureToggles).toEqual([{
      enabled: false,
      version: '1.0.0',
      feature: Feature.BetaUserInfoText,
    }, {
      enabled: false,
      version: '1.0.0',
      feature: Feature.ProductMetadata,
    }]);
  });

  it('should prioritize user profile feature toggles over base feature toggles', () => {
    // ARRANGE
    const userProfileFeatureToggles = [{
      enabled: true,
      version: '1.0.0',
      feature: Feature.ProductMetadata,
    }];

    const baseFeatureToggles = [{
      enabled: false,
      version: '1.0.0',
      feature: Feature.ProductMetadata,
    }, {
      enabled: true,
      version: '1.0.0',
      feature: Feature.ExperimentalWorkbench,
    }];

    // ACT
    const featureToggles = mergeFeatureToggles(
      userProfileFeatureToggles,
      baseFeatureToggles
    );

    // ASSERT
    expect(featureToggles).toEqual([{
      enabled: true,
      version: '1.0.0',
      feature: Feature.ProductMetadata,
    }, {
      enabled: true,
      version: '1.0.0',
      feature: Feature.ExperimentalWorkbench,
    }]);
  });

});
