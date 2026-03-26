import { ReactElement } from 'react';
import { Box, Button, SpaceBetween } from '@cloudscape-design/components';
import '@cloudscape-design/global-styles/dark-mode-utils.css';


export function EmptyGridNotification({
  title, subTitle, actionButtonText, actionButtonDisabled, actionButtonOnClick
}: {
  title: string,
  subTitle: string,
  actionButtonText?: string,
  actionButtonDisabled?: boolean,
  actionButtonOnClick?: () => void,
}): ReactElement {
  return (
    <Box textAlign="center" color="inherit">
      <SpaceBetween direction='vertical' size='xxxs'>
        <img className="awsui-util-hide-in-dark-mode" alt='empty' src='/empty-space.png'></img>
        <img className="awsui-util-show-in-dark-mode" alt='empty' src='/empty-space-dark-mode.png'></img>
        <Box variant='h3'>
          {title}
        </Box>
        <Box
          padding={{ bottom: 's' }}
          variant="p"
          color="inherit"
        >
          {subTitle}
        </Box>
        {!!actionButtonText &&
          <Button variant="primary"
            disabled={actionButtonDisabled}
            onClick={actionButtonOnClick}>
            {actionButtonText}
          </Button>
        }
      </SpaceBetween>
    </Box>);
}
