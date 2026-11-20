import { Image, Recipe } from '../../../../../services/API/proserve-wb-packaging-api';

const MARKETPLACE_IMAGE_SOURCE = 'MARKETPLACE_PRODUCT';
const CREATED_IMAGE_STATUS = 'CREATED';

/**
 * The images a version of the recipe can build on instead of the default base image: AWS Marketplace
 * images imported into the project's image catalog, available, and of the recipe's platform and architecture.
 */
export function getBaseImages(
  images: Image[],
  recipe?: Pick<Recipe, 'recipePlatform' | 'recipeArchitecture'>,
): Image[] {
  if (!recipe?.recipePlatform || !recipe?.recipeArchitecture) {
    return [];
  }
  return images.filter(image =>
    image.imageSource === MARKETPLACE_IMAGE_SOURCE
    && image.status === CREATED_IMAGE_STATUS
    && image.platform === recipe.recipePlatform
    && image.architecture === recipe.recipeArchitecture
  );
}

/**
 * The name to show for a base image, its ID when the image is not in the catalog listing.
 */
export function getBaseImageName(images: Image[], imageId: string): string {
  return images.find(image => image.imageId === imageId)?.imageName || imageId;
}
