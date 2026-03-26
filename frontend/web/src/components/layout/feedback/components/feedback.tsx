import { FC, Suspense, useEffect, useRef, useState } from 'react';
import styles from './feedback-trigger.module.scss';
import { FeedbackTrigger } from './feedback-trigger';
import React from 'react'; // eslint-disable-line
import { useLocalStorageNumber, useOutsideClickDetector } from '../../../../hooks';
import { FeedbackProps, i18n } from '../shared';

const FeedbackPopup = React.lazy(
  () => import('./feedback-popup')
);

const FEEDBACK_ASK_THRESHOLD_MONTHS = 1;

export const Feedback: FC<FeedbackProps> = ({ collector }) => {

  const [feedbackGiven, setFeedbackGiven] = useLocalStorageNumber('last-user-feedback-given-time');
  const [hidden, setHidden] = useState(!showFeedbackPopup(feedbackGiven));
  const [showCollectorDialogFunc, setShowCollectorDialogFunc] = useState<() => void>();

  const feedbackComponentDiv = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!!feedbackComponentDiv?.current && !hidden) {
      feedbackComponentDiv.current.focus();
    }
  }, [hidden]);

  useOutsideClickDetector(feedbackComponentDiv, () => {
    setHidden(true);
  });

  const escKeyHandler = (event: React.KeyboardEvent) => {
    if (event.key === 'Escape') {
      setHidden(true);
    }
  };

  return <>
    <div
      onKeyDown={escKeyHandler}
      className={`${styles.feedbackComponent} ${hidden ? styles.hidden : ''}`}
      ref={feedbackComponentDiv}
      tabIndex={-1}
    >
      {!hidden && <>
        <Suspense>
          <FeedbackPopup
            onCloseClick={() => setHidden(true)}
            onFeedbackButtonClick={feedbackGivenButtonClick}
            onIncidentButtonClick={feedbackGivenButtonClick}
            translations={i18n}
            showCollectorDialogFunc={showCollectorDialogFunc}
            setShowCollectorDialogFunc={setShowCollectorDialogFunc}
            collector={collector}
          />
        </Suspense>
      </>}
      <FeedbackTrigger onClick={() => setHidden(!hidden)} translations={i18n} feedbackPopupHidden={hidden}/>
    </div>
  </>;

  function feedbackGivenButtonClick() {
    setFeedbackGiven(+new Date());
  }

  function showFeedbackPopup(feedbackGiven?: number) {
    if (!feedbackGiven) {
      return true;
    }
    const feedbackGivenDate = new Date(feedbackGiven);
    const feedbackAskThreshold = new Date();
    feedbackAskThreshold.setMonth(feedbackAskThreshold.getMonth() - FEEDBACK_ASK_THRESHOLD_MONTHS);
    return +feedbackAskThreshold > +feedbackGivenDate;
  }
};
