// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { Route, Routes } from 'react-router-dom';
import { HomePageDisabled } from '../components/pages/home/home-disabled';

const routerNoAuth = (): JSX.Element => {

  return (
    <Routes>
      <Route path="*" element={<HomePageDisabled />} />
    </Routes>
  );
};

export { routerNoAuth as RouterDisabled };
