// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { AppLayout, Box, Grid } from '@cloudscape-design/components';
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
                  // { colspan: { xl: 2, l: 3, s: 4, xxs: 10 }, offset: { s: 0, xxs: 1 } }
                ]}
              >
                <Box variant="h1" fontWeight="bold" padding="n" fontSize="heading-l"
                  color="inherit">
                  Virtual Engineering Workbench
                </Box>
                <Box fontWeight="light" padding={{ bottom: 's' }} fontSize="heading-m"
                  color="inherit">
                  Access to VEW is currently unavailable.
                </Box>
              </Grid>
            </Box>
          </div>
        </Box>
      </>
    );
  }

};

export { homePage as HomePageDisabled };
