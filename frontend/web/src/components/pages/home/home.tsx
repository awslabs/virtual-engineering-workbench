// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { AppLayout, Box, Grid } from '@cloudscape-design/components';
import './home.scss';
import { Navigation } from '../../layout';
import { FC } from 'react';
import { useRecoilValue } from 'recoil';
import { loggedUser } from '../../session-management/logged-user';

/* eslint @typescript-eslint/no-magic-numbers: "off" */
// eslint-disable-next-line @typescript-eslint/no-empty-object-type
interface HomeProps {
}

export const HomePage: FC<HomeProps> = () => {
  const loggedInUser = useRecoilValue(loggedUser);

  return (
    <AppLayout
      content={renderContent()}
      navigation={<Navigation user={loggedInUser}/>}
      navigationOpen={false}
      toolsHide={true}
      onNavigationChange={() => {}} // eslint-disable-line
      headerSelector='#h'
    />
  );

  function renderContent() {
    return (
      <>
        <Box margin={{ bottom: 'l' }}>
          <div className="custom-home__header">
            <Box padding={{ vertical: 'xxl', horizontal: 's' }}>
              <Grid
                gridDefinition={[
                  { offset: { l: 2, xxs: 1 }, colspan: { l: 8, xxs: 10 } },
                  { colspan: { xl: 6, l: 5, s: 6, xxs: 10 }, offset: { l: 2, xxs: 1 } },
                  { colspan: { xl: 2, l: 3, s: 4, xxs: 10 }, offset: { s: 0, xxs: 1 } }
                ]}
              >
                <Box variant="h1" fontWeight="bold" padding="n" fontSize="display-l"
                  color="inherit">
                  Virtual Engineering Workbench
                </Box>
                <Box fontWeight="light" padding={{ bottom: 's' }} fontSize="display-l"
                  color="inherit">
                  Welcome to AWS Virtual Engineering Workbench
                </Box>
              </Grid>
            </Box>
          </div>
        </Box>
      </>
    );
  }

};
