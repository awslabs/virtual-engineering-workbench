import { describe, expect, it } from 'vitest';
import { buildMarketplaceMetadata } from './import-image-wizard.logic';

describe('buildMarketplaceMetadata', () => {
  it('sends only the server-side subscription selector', () => {
    expect(buildMarketplaceMetadata({
      productCode: 'prodcode1234567',
      subscriptionOwnership: 'VEW_MANAGED',
      licenseGrantAllowed: true,
      regionalAmiIds: Object.fromEntries([
        ['us-east-1', 'ami-forged'],
      ]),
      licenseConfigurationArn: 'arn:aws:license-manager::license:forged',
      homeRegion: 'ap-southeast-2',
    })).toEqual({ productCode: 'prodcode1234567' });
  });
});
