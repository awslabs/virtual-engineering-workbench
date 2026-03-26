// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { signOut, signInWithRedirect, fetchAuthSession } from 'aws-amplify/auth';
import { useEffect } from 'react';
import { useRecoilState } from 'recoil';
import { LoggedInUserState, loggedInUserState } from './logged-user';
import awsExports from '../../aws-exports';
import { Hub } from 'aws-amplify/utils';

/* eslint @typescript-eslint/no-explicit-any: "off", complexity: "off" */

const initiateSignOut = async () => {
  await signOut({ global: true });
  // Redirect to Cognito logout URL for complete logout
  const logoutUrl = [
    'https://',
    awsExports.Auth.Cognito.loginWith.oauth.domain,
    '/logout?client_id=',
    awsExports.Auth.Cognito.userPoolClientId,
    '&logout_uri=',
    encodeURIComponent(awsExports.Auth.Cognito.loginWith.oauth.redirectSignOut[0])
  ].join('');

  window.location.href = logoutUrl;
};

const initiateAuth = () => {
  return signInWithRedirect();
};

type Authenticator = {
  user: LoggedInUserState | undefined,
  initiateAuth: () => Promise<void>,
  initiateSignOut: () => Promise<void>,
};

export const useAuthenticator = (): Authenticator => {
  const [user, setUser] = useRecoilState(loggedInUserState);

  useEffect(() => {
    const cancelListener = Hub.listen('auth', ({ payload: { event } }) => {
      switch (event) {
        case 'signedOut':
          setUser(undefined);
          break;
      }
    });

    fetchAuthSession().then((session) => {
      const idToken = session.tokens?.idToken;
      if (idToken) {
        const info = {
          userName: idToken.payload.email as string,
          userId: idToken.payload['custom:user_tid'] as string,
          firstName: idToken.payload.given_name as string,
          lastName: idToken.payload.family_name as string,
          email: idToken.payload.email as string,
        };
        const loggedInUser: LoggedInUserState = { user: info };
        setUser(loggedInUser);
      }
    }).catch(() => {
      // User not authenticated
    });

    return cancelListener;
  }, [setUser]);

  return {
    user,
    initiateAuth,
    initiateSignOut,
  };
};