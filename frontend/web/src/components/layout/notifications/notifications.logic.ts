// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { FlashbarProps } from '@cloudscape-design/components';
import { ReactNode, useEffect, useState } from 'react';
import { useRecoilValue, useSetRecoilState } from 'recoil';
import { v4 as generateGuid } from 'uuid';
import { NotificationItem, notificationsState } from '../../../state';

const i18n = {
  dismissLabel: 'Dismiss'
};

type NotificationContents = {
  header: string,
  content: string | ReactNode,
  onDismiss?: () => void,
  manualDismissOnly?: boolean,
};

type NotificationsType = {
  notifications: NotificationItem[],
  showErrorNotification({ header, content }: NotificationContents): void,
  showSuccessNotification({ header, content }: NotificationContents): void,
  showWarningNotification({ header, content }: NotificationContents): void,
  showInfoNotification({ header, content }: NotificationContents): void,
  clearNotifications(): void,
};

function useNotifications(): NotificationsType {
  const notificationsGlobal = useRecoilValue(notificationsState);
  const setNotifications = useSetRecoilState(notificationsState);
  const [localNotifications, setLocalNotifications] = useState<NotificationItem[]>([]);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    if (isMounted) {
      setLocalNotifications([...notificationsGlobal]);
    }
  }, [notificationsGlobal, isMounted]);

  useEffect(() => {
    setIsMounted(true);
    return () => setIsMounted(false);
  }, []);

  return {
    notifications: localNotifications,
    showErrorNotification,
    showSuccessNotification,
    showWarningNotification,
    showInfoNotification,
    clearNotifications,
  };

  function showErrorNotification({
    header,
    content,
    onDismiss,
    manualDismissOnly
  }: NotificationContents): void {
    showNotification({ header, content, onDismiss, manualDismissOnly }, 'error');
  }

  function showSuccessNotification({
    header,
    content,
    onDismiss,
    manualDismissOnly
  }: NotificationContents): void {
    showNotification({ header, content, onDismiss, manualDismissOnly }, 'success');
  }

  function showWarningNotification({
    header,
    content,
    onDismiss,
    manualDismissOnly
  }: NotificationContents): void {
    showNotification({ header, content, onDismiss, manualDismissOnly }, 'warning');
  }

  function showInfoNotification({
    header,
    content,
    onDismiss,
    manualDismissOnly
  }: NotificationContents): void {
    showNotification({ header, content, onDismiss, manualDismissOnly }, 'info');
  }

  function showNotification({
    header,
    content,
    onDismiss,
    manualDismissOnly
  }: NotificationContents, type: FlashbarProps.Type): void {
    const id = generateGuid();
    setNotifications((oldNotifications) => [{
      header,
      type: type,
      content,
      dismissible: true,
      dismissLabel: i18n.dismissLabel,
      id,
      manualDismissOnly: manualDismissOnly || false,
      onDismiss: () => {
        removeNotification(id);
        onDismiss?.();
      },
    }, ...oldNotifications]);
  }

  function removeNotification(id: string): void {
    setNotifications((oldNotifications) => oldNotifications.filter(n => n.id !== id));
  }

  function clearNotifications(): void {
    setNotifications((oldNotifications) => oldNotifications.filter(n => n.manualDismissOnly));
  }
}

export { useNotifications };