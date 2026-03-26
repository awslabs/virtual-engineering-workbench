// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import React from 'react';
import { render, act, renderHook } from '@testing-library/react';
import { RecoilRoot, SetRecoilState } from 'recoil';
import { Notifications } from '.';
import { useNotifications } from './notifications.logic';
import { notificationsState } from '../../../state';
import { describe, it, expect } from 'vitest';

/* eslint-disable @typescript-eslint/no-empty-function */
describe('Notifications', () => {


  it('stores error notifications in memory', () => {
    // ARRANGE 
    const wrapper = ({ children }: { children: React.ReactNode }) => <RecoilRoot>{children}</RecoilRoot>;
    const { result } = renderHook(() => useNotifications(), {
      wrapper
    });

    // ACT
    act(() => {
      result.current.showErrorNotification({
        header: 'Error Header',
        content: 'Error Content',
      });
    });

    // ASSERT
    expect(result.current.notifications).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          header: 'Error Header',
          content: 'Error Content',
          dismissible: true,
          type: 'error'
        })]));
  });

  it('displays error notifications with header from memory', () => {
    // ARRANGE
    const initializeState = ({ set }: { set: SetRecoilState }) => {
      set(notificationsState, [{
        header: 'Error Header',
        content: 'Error Content',
        dismissible: true,
        type: 'error',
        id: 'test',
        manualDismissOnly: false,
        onDismiss: () => {},
      }]);
    };

    // ACT
    const { getByText } = render(<RecoilRoot initializeState={initializeState}><Notifications/></RecoilRoot>);

    // ASSERT
    const errorElement = getByText(/Error Header/iu);
    expect(errorElement).toBeInTheDocument();
  });

  it('displays error notifications with content from memory', () => {
    // ARRANGE
    const initializeState = ({ set }: { set: SetRecoilState }) => {
      set(notificationsState, [{
        header: 'Error Header',
        content: 'Error Content',
        dismissible: true,
        type: 'error',
        id: 'test',
        manualDismissOnly: false,
        onDismiss: () => {},
      }]);
    };

    // ACT
    const { getByText } = render(<RecoilRoot initializeState={initializeState}><Notifications/></RecoilRoot>);

    // ASSERT
    const errorElement = getByText(/Error Content/iu);
    expect(errorElement).toBeInTheDocument();
  });
});