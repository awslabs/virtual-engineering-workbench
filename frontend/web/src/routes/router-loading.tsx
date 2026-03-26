// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { Route, Routes } from 'react-router-dom';
import { HomePageLoading } from '../components/pages/home/home-loading';

const routerNoAuth = (): JSX.Element => {

  return (
    <Routes>
      <Route path="*" element={<HomePageLoading />} />
    </Routes>
  );
};

export { routerNoAuth as RouterLoading };
