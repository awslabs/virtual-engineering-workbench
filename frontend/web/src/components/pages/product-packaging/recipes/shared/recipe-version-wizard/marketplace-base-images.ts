import {
  DiscoveredMarketplaceSubscription,
  Image,
} from '../../../../../../services/API/proserve-wb-packaging-api';

// Recipes, recipe testing and the product templates all map the root volume at this device.
const RECIPE_ROOT_DEVICE_NAME = '/dev/sda1';
const AWS_PUBLISHED_AMI = 'AWS_PUBLISHED_AMI';
const IMAGE_CREATED = 'CREATED';
const IMAGE_ID_PREFIX = 'image-';

export type MarketplaceBaseImage = DiscoveredMarketplaceSubscription & { productId: string };

/**
 * Subscribed AWS Marketplace products a recipe can build on: same platform and architecture as the
 * recipe, and a root volume on the device recipes size. The backend checks the choice again
 * (subscription, root volume, minimum volume size).
 */
export function getMarketplaceBaseImages(
  subscriptions: DiscoveredMarketplaceSubscription[] | undefined,
  recipePlatform: string | undefined,
  recipeArchitecture: string | undefined,
): MarketplaceBaseImage[] {
  if (!recipePlatform || !recipeArchitecture) {
    return [];
  }
  return (subscriptions || []).filter((subscription): subscription is MarketplaceBaseImage =>
    !!subscription.productId
    && subscription.platform === recipePlatform
    && subscription.architecture === recipeArchitecture
    && (!subscription.rootDeviceName || subscription.rootDeviceName === RECIPE_ROOT_DEVICE_NAME));
}

/**
 * AMIs that AWS publishes (Windows Server, RHEL, SUSE, Ubuntu Pro, ...) imported into the project, that a
 * recipe of this platform and architecture can build on. There is no subscription behind them: AWS is the
 * seller of record and the licence comes with the EC2 instance. The backend checks the root volume again.
 */
export function getAwsPublishedBaseImages(
  images: Image[] | undefined,
  recipePlatform: string | undefined,
  recipeArchitecture: string | undefined,
): Image[] {
  if (!recipePlatform || !recipeArchitecture) {
    return [];
  }
  return (images || []).filter(image =>
    image.imageSource === AWS_PUBLISHED_AMI
    && image.status === IMAGE_CREATED
    && image.platform === recipePlatform
    && image.architecture === recipeArchitecture);
}

/** The base image choice (product ID, imported image ID or '' for the default) as request fields. */
export function toBaseImageRequest(
  baseImage: string,
  isUpdate: boolean,
): { parentImageProductId?: string, parentImageId?: string } {
  if (baseImage.startsWith(IMAGE_ID_PREFIX)) {
    // On update '' clears a previous Marketplace product.
    return isUpdate ? { parentImageProductId: '', parentImageId: baseImage } : { parentImageId: baseImage };
  }
  if (baseImage) {
    return isUpdate
      ? { parentImageProductId: baseImage, parentImageId: '' }
      : { parentImageProductId: baseImage };
  }
  // Default image: on update '' switches back explicitly; leaving the fields out would keep the current one.
  return isUpdate ? { parentImageProductId: '', parentImageId: '' } : {};
}
