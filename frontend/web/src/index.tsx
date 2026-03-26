// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import React from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import { App } from './app';
import reportWebVitals from './reportWebVitals';
import { Amplify, type ResourcesConfig } from 'aws-amplify';
import { CookieStorage } from 'aws-amplify/utils';
import { cognitoUserPoolsTokenProvider } from 'aws-amplify/auth/cognito';
import awsExports from './aws-exports';
import { BrowserRouter } from 'react-router-dom';
import { RecoilRoot } from 'recoil';

Amplify.configure(awsExports as ResourcesConfig);
cognitoUserPoolsTokenProvider.setKeyValueStorage(new CookieStorage());

const container = document.getElementById('root');
const root = createRoot(container!);

root.render(
  <React.StrictMode>
    <BrowserRouter>
      <RecoilRoot>
        <App/>
      </RecoilRoot>
    </BrowserRouter>
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();