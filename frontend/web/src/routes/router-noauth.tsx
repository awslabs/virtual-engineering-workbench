// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { Route, Routes } from 'react-router-dom';
import { HomePage } from '../components/pages';

const routerNoAuth = (): JSX.Element => {
  return (
    <Routes>
      <Route path="/"
        element={<HomePage />} />
    </Routes>
  );
};

export { routerNoAuth as RouterNoAuth };
