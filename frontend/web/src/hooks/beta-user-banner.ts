import { useEffect, useState } from 'react';
import { useRecoilState } from 'recoil';
import { useLocalStorage } from '.';
import { useNotifications } from '../components/layout';
import { loggedInUserState } from '../components/session-management/logged-user';
import { useFeatureToggles } from './../components/feature-toggles/feature-toggle.hook';
import { Feature } from '../components/feature-toggles/feature-toggle.state';


const i18n = {
  betaUserWarning: `Warning! 
This environment is intended for testing purposes and is not a production environment. 
Please take care not to upload proprietary intellectual property.`
};

const useBetaUserNotification = () => {

  const { isFeatureEnabled } = useFeatureToggles();

  const { showErrorNotification } = useNotifications();
  const [user] = useRecoilState(loggedInUserState);
  const [notificationShown, setNotificationShown] = useState(false);
  const [
    notificationDismissed,
    setNotificationDismissed
  ] = useLocalStorage('beta-user-notification-dismissed');
  const [isMounted, setIsMounted] = useState(false);


  useEffect(() => {
    setIsMounted(true);
    return () => setIsMounted(false);
  }, []);

  useEffect(() => {
    if (isFeatureEnabled(Feature.BetaUserInfoText) && needsToShowBetaUserNotification() && isMounted) {
      setNotificationShown(true);

      showErrorNotification({
        header: '',
        content: i18n.betaUserWarning,
        onDismiss: () => setNotificationDismissed('true'),
        manualDismissOnly: true,
      });
    }
  }, [user, isMounted]);

  return { notificationDismissed };

  function needsToShowBetaUserNotification() {
    return !!user && !notificationShown && notificationDismissed !== 'true';
  }
};

export { useBetaUserNotification };