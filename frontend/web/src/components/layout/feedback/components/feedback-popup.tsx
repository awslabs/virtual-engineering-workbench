import { FC } from 'react';
import styles from './feedback-trigger.module.scss';
import { Box, Button, Header, Icon } from '@cloudscape-design/components';
import { HelpUrls } from '../../../pages/help';
import { useRecoilValue } from 'recoil';
import { loggedUser } from '../../../session-management/logged-user';
import { useJiraCollector } from './jira-collector.logic';
import { FeedbackPopupProps, FeedbackPopupTextItem } from '../shared';
import { GenericFeedbackIcon } from '../../vew-icons';

const FeedbackPopup: FC<FeedbackPopupProps> = ({
  onCloseClick,
  onFeedbackButtonClick,
  onIncidentButtonClick,
  translations,
  showCollectorDialogFunc,
  setShowCollectorDialogFunc,
  collector,
}) => {

  const user = useRecoilValue(loggedUser);

  useJiraCollector({
    ...collector,
    setShowCollectorDialogFunc,
    username: user?.userId || '',
    email: user?.email || '',
  });

  return <>
    <div className={`${styles.popupRoot} awsui-dark-mode`}>
      <div className={styles.popupContent}>
        <div className={styles.header}>
          <Header actions={
            <Button
              iconName='close'
              variant='icon'
              formAction="none"
              onClick={onCloseClick}
            />
          }>
            <Icon size='big' variant='link' svg={<GenericFeedbackIcon/>} />
          </Header>
        </div>
        <div className={styles.content}>
          <Box variant='strong'>{translations.title}</Box>
          <Box>
            <ul>
              {translations.text.map(renderTextItem)}
            </ul>
          </Box>
        </div>
        <div className={styles.footer}>
          <Button
            iconName='suggestions'
            fullWidth
            onClick={onFeedbackClick}
            disabled={!setShowCollectorDialogFunc}
          >
            {translations.feedbackButtonText}
          </Button>
          <Button
            iconName='flag'
            fullWidth
            onClick={onIncidentClick}>
            {translations.incidentButtonText}
          </Button>
        </div>
      </div>
    </div>
  </>;

  function onFeedbackClick() {
    onFeedbackButtonClick?.();
    showCollectorDialog();
    onCloseClick?.();
  }

  function onIncidentClick() {
    onIncidentButtonClick?.();
    onCloseClick?.();
    window.open(
      HelpUrls.genericOpsRequestRaise,
      '_blank'
    );
  }

  function showCollectorDialog() {
    if (showCollectorDialogFunc) {
      showCollectorDialogFunc();
    }
  }

  function renderTextItem(item: FeedbackPopupTextItem) {
    return <li key={item.emp}>
      <strong>{item.emp}</strong>{item.text}
    </li>;
  }
};

export default FeedbackPopup;