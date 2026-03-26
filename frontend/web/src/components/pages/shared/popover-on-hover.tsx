import { Popover, Button } from '@cloudscape-design/components';
import { useState } from 'react';

type Props = {
  popoverHeader?: string,
  popoverContent?: string,
  popoverSize?: 'small' | 'medium' | 'large',
  popoverPosition?: 'top' | 'right' | 'bottom' | 'left',
  popoverTriggerType?: 'text' | 'custom',
  buttonLabel?: string,
  buttonOnClick?: () => any,
  buttonDisabled?: boolean,
};

export function PopoverOnHover({
  popoverHeader,
  popoverContent,
  popoverSize,
  popoverPosition,
  popoverTriggerType,
  buttonLabel,
  buttonOnClick,
  buttonDisabled
}: Props) {
  const POPOVER_DELAY = 500;
  const [popoverOpened, setPopoverOpened] = useState(false);

  function openPopover() {
    setPopoverOpened(true);
    setTimeout(() => {
      document.getElementById('button')?.click();
    }, POPOVER_DELAY);
  }

  function closePopover() {
    setPopoverOpened(false);
  }

  return <>
    {popoverOpened && <div
      onMouseEnter={() => openPopover()}
      onMouseLeave={() => closePopover()}
    >
      <Popover
        triggerType={popoverTriggerType}
        position={popoverPosition}
        size={popoverSize}
        header={popoverHeader}
        content={popoverContent}
        dismissButton={false}
      >
        <div id="button" style={{
          border: 'none',
          background: 'transparent',
          margin: '0',
          padding: '0'
        }}>
          <Button
            onClick={buttonOnClick}
            disabled={buttonDisabled}
            data-test="popover-button"
          >
            {buttonLabel}
          </Button>
        </div>
      </Popover>
    </div>}
    {!popoverOpened && <div onMouseEnter={() => openPopover()}>
      <Button
        onClick={buttonOnClick}
        disabled={buttonDisabled}
        data-test="popover-button"
      >
        {buttonLabel}
      </Button></div>}</>;
}