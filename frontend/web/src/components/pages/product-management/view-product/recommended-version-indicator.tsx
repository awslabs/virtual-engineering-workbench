import { Badge } from '@cloudscape-design/components';
import { i18n } from './view-product.translations';

export function recommendedVersionIndicator({ isRecommendedVersion }: { isRecommendedVersion: boolean }) {
  if (isRecommendedVersion) {
    return (
      <Badge color={'blue'}>
        {i18n.recommendedVersionIndicator}
      </Badge>
    );
  }
  return null;
}

export { recommendedVersionIndicator as RecommendedVersionIndicator };