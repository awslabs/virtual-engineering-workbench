import { FC, useState } from 'react';
import styles from './feedback-trigger.module.scss';
import { Box, Button } from '@cloudscape-design/components';
import { FeedbackTriggerProps } from '../shared';
import { GenericFeedbackIcon } from '../../vew-icons';

export const FeedbackTrigger: FC<FeedbackTriggerProps> = ({ onClick, translations, feedbackPopupHidden }) => {

  const [shouldExpand, setShouldExpand] = useState(false);

  return <>
    <div
      className={styles.feedbackButtonContent}
      onMouseEnter={() => setShouldExpand(true)}
      onMouseLeave={() => setShouldExpand(false)}
      onFocus={() => setShouldExpand(true)}
      onBlur={() => setShouldExpand(false)}
    >
      <Box float='right'>
        <Button
          iconSvg={<GenericFeedbackIcon/>}
          onClick={onClick}>
          {(!feedbackPopupHidden || shouldExpand) && translations.feedbackTriggerButtonText}
        </Button>
      </Box>
    </div>
  </>;
};