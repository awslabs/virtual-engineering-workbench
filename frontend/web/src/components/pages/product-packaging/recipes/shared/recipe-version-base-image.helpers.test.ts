import { describe, expect, it } from 'vitest';
import { Image } from '../../../../../services/API/proserve-wb-packaging-api';
import { getBaseImageName, getBaseImages } from './recipe-version-base-image.helpers';

const image = (imageId: string, overrides: Partial<Image> = {}): Image => ({
  imageId,
  imageBuildVersion: 'None',
  status: 'CREATED',
  imageSource: 'MARKETPLACE_PRODUCT',
  imageName: `Image ${imageId}`,
  platform: 'Linux',
  architecture: 'amd64',
  createDate: '2026-01-01T00:00:00+00:00',
  lastUpdateDate: '2026-01-01T00:00:00+00:00',
  ...overrides,
});

const recipe = { recipePlatform: 'Linux', recipeArchitecture: 'amd64' };

describe('getBaseImages', () => {
  it('offers available Marketplace images of the recipe platform and architecture', () => {
    const images = [
      image('image-mkt00001'),
      image('image-mkt00002', { status: 'RETIRED' }),
      image('image-mkt00003', { imageSource: 'EXISTING_AMI' }),
      image('image-mkt00004', { imageSource: 'PIPELINE' }),
      image('image-mkt00005', { imageSource: undefined }),
      image('image-mkt00006', { platform: 'Windows' }),
      image('image-mkt00007', { architecture: 'arm64' }),
    ];

    expect(getBaseImages(images, recipe).map(i => i.imageId)).toEqual(['image-mkt00001']);
  });

  it('offers nothing before the recipe is loaded', () => {
    expect(getBaseImages([image('image-mkt00001')], undefined)).toEqual([]);
    expect(getBaseImages([image('image-mkt00001')], { recipePlatform: '', recipeArchitecture: '' }))
      .toEqual([]);
  });
});

describe('getBaseImageName', () => {
  it('names the image from the catalog', () => {
    expect(getBaseImageName([image('image-mkt00001')], 'image-mkt00001')).toBe('Image image-mkt00001');
  });

  it('falls back to the image ID', () => {
    expect(getBaseImageName([], 'image-mkt00001')).toBe('image-mkt00001');
    expect(getBaseImageName([image('image-mkt00001', { imageName: undefined })], 'image-mkt00001'))
      .toBe('image-mkt00001');
  });
});
