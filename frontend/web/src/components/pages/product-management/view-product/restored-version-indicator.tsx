import { Badge, Box, Icon, Link, Popover, SpaceBetween } from '@cloudscape-design/components';
import { VersionSummary } from '../../../../services/API/proserve-wb-publishing-api';
import { i18n } from './view-product.translations';

export function restoredVersionIndicator({ productVersion }:
{ productVersion: VersionSummary }) {

  if (productVersion && productVersion.restoredFromVersionName !== undefined) {
    return (
      <SpaceBetween size='xs' direction='horizontal'>
        <Box textAlign='center'>
          <Badge color={'blue'}>
            {i18n.restoredVersionIndicator}
          </Badge>
        </Box>
        <Box color="text-status-info" display="inline">
          <Popover
            header={i18n.popoverHeader}
            size="medium"
            triggerType='custom'
            content={i18n.popoverContent + productVersion.restoredFromVersionName + '.'}
          >
            <Link>
              <Icon name="status-info"></Icon>
            </Link>
          </Popover>
        </Box>
      </SpaceBetween>
    );
  }
  return null;
}

export { restoredVersionIndicator as RestoredVersionIndicator };