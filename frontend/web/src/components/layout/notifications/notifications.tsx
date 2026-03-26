// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { Flashbar } from '@cloudscape-design/components';
import { useNotifications } from './notifications.logic';
import React from 'react';

export const Notifications = (): React.ReactNode => {

  const { notifications } = useNotifications();

  return (
    <Flashbar items={notifications} data-test="notifications" stackItems />
  );
};
