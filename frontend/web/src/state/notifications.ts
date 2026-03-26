// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { FlashbarProps } from '@cloudscape-design/components';
import { atom } from 'recoil';


export type NotificationItem = FlashbarProps.MessageDefinition & {
  id: string,
  manualDismissOnly: boolean,
};

const notificationsState = atom<NotificationItem[]>({
  key: 'notifications',
  default: []
});

export { notificationsState };
