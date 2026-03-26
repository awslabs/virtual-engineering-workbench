// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { atom, selector } from 'recoil';

export type UserType = {
  userName: string,
  userId: string,
  firstName: string,
  lastName: string,
  email: string,
};

export type LoggedInUserState = {
  user?: UserType,
};

const loggedInUserState = atom<LoggedInUserState | undefined>({
  key: 'loggedUserState',
  default: {},
});

const loggedUser = selector<UserType | undefined>({
  key: 'loggedUser',
  get: ({ get }) => {
    const lus = get(loggedInUserState);
    return lus?.user;
  },
});

export { loggedInUserState, loggedUser };
