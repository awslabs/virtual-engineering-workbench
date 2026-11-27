import {
  getAwsPublishedBaseImages,
  getMarketplaceBaseImages,
  toBaseImageRequest,
} from './marketplace-base-images';
import { Image } from '../../../../../../services/API/proserve-wb-packaging-api';

describe('getMarketplaceBaseImages', () => {
  const ubuntuAmd64 = {
    productId: 'prod-ib2w5aw4ynhey', productName: 'Ubuntu 24.04', platform: 'Linux', architecture: 'amd64',
  };
  const ubuntuArm64 = {
    productId: 'prod-armarmarmarm', productName: 'Ubuntu 24.04 arm', platform: 'Linux', architecture: 'arm64',
  };
  const windows = {
    productId: 'prod-windowswin', productName: 'Windows Server', platform: 'Windows', architecture: 'amd64',
  };
  const withoutProductId = { productName: 'Unknown', platform: 'Linux', architecture: 'amd64' };

  it('should offer only products matching the recipe platform and architecture', () => {
    // ACT
    const images = getMarketplaceBaseImages([ubuntuAmd64, ubuntuArm64, windows], 'Linux', 'amd64');

    // ASSERT
    expect(images).toEqual([ubuntuAmd64]);
  });

  it('should skip subscriptions without a product ID', () => {
    // ACT
    const images = getMarketplaceBaseImages([withoutProductId, ubuntuAmd64], 'Linux', 'amd64');

    // ASSERT
    expect(images).toEqual([ubuntuAmd64]);
  });

  it('should skip products whose root volume is not on the device recipes size', () => {
    // ARRANGE
    const amazonLinux = { ...ubuntuAmd64, productId: 'prod-amazonlinux', rootDeviceName: '/dev/xvda' };
    const ubuntuWithDevice = { ...ubuntuAmd64, rootDeviceName: '/dev/sda1' };

    // ACT
    const images = getMarketplaceBaseImages([amazonLinux, ubuntuWithDevice], 'Linux', 'amd64');

    // ASSERT
    expect(images).toEqual([ubuntuWithDevice]);
  });

  it('should offer nothing until the recipe and subscriptions are loaded', () => {
    expect(getMarketplaceBaseImages(undefined, 'Linux', 'amd64')).toEqual([]);
    expect(getMarketplaceBaseImages([ubuntuAmd64], undefined, undefined)).toEqual([]);
  });
});


describe('getAwsPublishedBaseImages', () => {
  const image = (overrides: Partial<Image>): Image => ({
    imageId: 'image-rhel9abc', imageBuildVersion: '1', status: 'CREATED', imageSource: 'AWS_PUBLISHED_AMI',
    platform: 'Linux', architecture: 'amd64', imageName: 'RHEL 9', imageUpstreamId: 'ami-0b07d2bc8152a1d84',
    createDate: '2026-11-12', lastUpdateDate: '2026-11-12', ...overrides,
  });

  it('should offer created AWS-published imports matching the recipe', () => {
    // ARRANGE
    const rhel = image({});
    const images = [
      rhel,
      image({ imageId: 'image-pipeline1', imageSource: 'PIPELINE' }),
      image({ imageId: 'image-mpimport', imageSource: 'MARKETPLACE_PRODUCT' }),
      image({ imageId: 'image-retired01', status: 'RETIRED' }),
      image({ imageId: 'image-windows01', platform: 'Windows' }),
      image({ imageId: 'image-graviton1', architecture: 'arm64' }),
    ];

    // ACT / ASSERT
    expect(getAwsPublishedBaseImages(images, 'Linux', 'amd64')).toEqual([rhel]);
  });

  it('should offer nothing until the recipe and images are loaded', () => {
    expect(getAwsPublishedBaseImages(undefined, 'Linux', 'amd64')).toEqual([]);
    expect(getAwsPublishedBaseImages([image({})], undefined, undefined)).toEqual([]);
  });
});

describe('toBaseImageRequest', () => {
  it('should send the chosen kind of base image on create', () => {
    expect(toBaseImageRequest('prod-ib2w5aw4ynhey', false))
      .toEqual({ parentImageProductId: 'prod-ib2w5aw4ynhey' });
    expect(toBaseImageRequest('image-rhel9abc', false)).toEqual({ parentImageId: 'image-rhel9abc' });
    expect(toBaseImageRequest('', false)).toEqual({});
  });

  it('should clear the other kind on update and send "" for the default', () => {
    expect(toBaseImageRequest('prod-ib2w5aw4ynhey', true))
      .toEqual({ parentImageProductId: 'prod-ib2w5aw4ynhey', parentImageId: '' });
    expect(toBaseImageRequest('image-rhel9abc', true))
      .toEqual({ parentImageProductId: '', parentImageId: 'image-rhel9abc' });
    expect(toBaseImageRequest('', true)).toEqual({ parentImageProductId: '', parentImageId: '' });
  });
});
