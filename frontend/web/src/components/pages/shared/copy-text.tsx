import { Box, Button, Popover, StatusIndicator, StatusIndicatorProps } from '@cloudscape-design/components';
import { useState } from 'react';
import { copyToClipboard } from '../../../utils/clipboard';

const SUCCESS_STATUS: StatusIndicatorProps.Type = 'success';
const ERROR_STATUS: StatusIndicatorProps.Type = 'error';

type Variant = 'inline' | 'button';

type Props = {
  copyText: string,
  copyButtonLabel?: string,
  successText?: string,
  errorText?: string,
  variant?: Variant,
};

export function copyText({
  copyText,
  copyButtonLabel = 'Copy',
  successText = 'Copied to clipboard',
  errorText = 'Unable to copy',
  variant,
}: Props) {
  const [status, setStatus] = useState(SUCCESS_STATUS);
  const [message, setMessage] = useState(successText);
  return (
    <div className="custom-wrapping">
      <Box margin={{ right: 'xxs' }} display="inline-block">
        <Popover
          size="small"
          position="top"
          dismissButton={false}
          triggerType="custom"
          content={<StatusIndicator type={status}>{message}</StatusIndicator>}
        >
          <Button
            variant={variant === 'button' ? 'normal' : 'inline-icon'}
            iconName="copy"
            ariaLabel={copyButtonLabel}
            onClick={() => {
              copyToClipboard(copyText).then(
                () => {
                  setStatus(SUCCESS_STATUS);
                  setMessage(successText);
                },
                () => {
                  setStatus(ERROR_STATUS);
                  setMessage(errorText);
                }
              );
            }}
          >
            {variant === 'button' && copyButtonLabel}
          </Button>
        </Popover>
      </Box>
      {variant !== 'button' && copyText}
    </div>
  );
}

export { copyText as CopyText };