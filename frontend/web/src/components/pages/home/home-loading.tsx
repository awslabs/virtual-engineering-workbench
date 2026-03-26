// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { AppLayout, Spinner } from '@cloudscape-design/components';
import './home.scss';
import { FC } from 'react';

/* eslint @typescript-eslint/no-magic-numbers: "off" */
// eslint-disable-next-line @typescript-eslint/no-empty-object-type
interface HomeProps {
}

const homePage: FC<HomeProps> = () => {
  return (
    <AppLayout
      content={renderContent()}
      navigationHide
      toolsHide
      onNavigationChange={() => {}} // eslint-disable-line
      headerSelector='#h'
    />
  );

  function renderContent() {
    return (
      <Spinner size='large'/>
    );
  }

};

export { homePage as HomePageLoading };
