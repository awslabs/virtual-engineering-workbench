import { getWorkbenchFeatureToggles } from './feature-toggle-workbench.hook';
import { Feature } from './feature-toggle.state';

describe('useWOrkbenchFeatureToggles', () => {

  it('should transform workbench outputs to feature toggle items', () => {
    // ARRANGE
    const workbenchOutputParams = [{
      outputKey: 'FeatureToggles',
      outputValue: `[{
        "feature": "DCVConnectionOptions",
        "enabled": false,
        "userOverrides": ["T0037SK"]
      }]`,
      description: 'some test toggles',
    }];

    // ACT
    const featureToggles = getWorkbenchFeatureToggles(workbenchOutputParams);

    // ASSERT
    expect(featureToggles).toEqual([{
      enabled: false,
      version: '1.0.0',
      feature: Feature.DCVConnectionOptions,
    }]);
  });

  it('should ignore unknown feature names from workbench feature toggles', () => {
    // ARRANGE
    const workbenchOutputParams = [{
      outputKey: 'FeatureToggles',
      outputValue: `[{
        "feature": "EvilUnknownFeatures",
        "enabled": false,
        "userOverrides": ["T0037SK"]
      }]`,
      description: 'some test toggles',
    }];

    // ACT
    const featureToggles = getWorkbenchFeatureToggles(workbenchOutputParams);

    // ASSERT
    expect(featureToggles).toEqual([]);
  });

});