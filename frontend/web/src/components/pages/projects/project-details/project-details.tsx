// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import {
  Box,
  Button,
  ColumnLayout,
  Container,
  Header,
  HelpPanel,
  SpaceBetween,
  Spinner,
  StatusIndicator,
  Tabs
} from '@cloudscape-design/components';
import { FC, useEffect } from 'react';
import { useLocalStorage, useProjectsSwitch } from '../../../../hooks';
import { useRoleAccessToggle } from '../../../../hooks/role-access-toggle';
import { RoleBasedFeature } from '../../../../state';
import { BreadcrumbItem } from '../../../layout';
import { useNavigationPaths } from '../../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../../layout/navigation/navigation.static';
import { WorkbenchAppLayout } from '../../../layout/workbench-app-layout/workbench-app-layout';
import { ProjectAccounts } from './project-accounts';

const i18n = {
  breadcrumbLevel1: 'Administration',
  breadcrumbProjectUnknown: '(...)',
  headerLoading: 'Loading...',
  header: 'Program details',
  detailsId: 'Id',
  detailsName: 'Name',
  detailsDecription: 'Description',
  detailsStatus: 'Status',
  tabUsers: 'Users',
  tabAccounts: 'Accounts',
  updateButtonText: 'Update',
  projectActive: 'Active',
  projectInactive: 'Inactive'
};

const TAB_ID_ACCOUNTS = 'accounts';

/* eslint @typescript-eslint/no-magic-numbers: "off" */
// eslint-disable-next-line @typescript-eslint/no-empty-object-type
interface SampleProps {
}

const projectDetails: FC<SampleProps> = () => {

  const [selectedTab, setSelectedTab] = useLocalStorage('project-details#last-selected-tab');
  const { loadingProjects, selectedProject } = useProjectsSwitch({});
  const isFeatureAccessible = useRoleAccessToggle();
  const { getPathFor, navigateTo } = useNavigationPaths();

  useEffect(() => {
    if (!!selectedTab && !new Set([TAB_ID_ACCOUNTS]).has(selectedTab)) {
      setSelectedTab(TAB_ID_ACCOUNTS);
    }
  }, []);

  function getBreadcrumbItems(): BreadcrumbItem[] {
    return [
      { path: i18n.breadcrumbLevel1, href: getPathFor(RouteNames.Programs) },
      { path: selectedProject?.projectName || i18n.breadcrumbProjectUnknown, href: '#' },
    ];
  }

  return (
    <WorkbenchAppLayout
      breadcrumbItems={getBreadcrumbItems()}
      content={renderContent()}
      contentType="default"
      tools={renderTools()}
      customHeader={renderHeader()}
    />
  );

  function renderHeader() {
    return <>
      <Header
        variant='h1'
        actions={
          <Button onClick={() => {
            navigateTo(RouteNames.UpdateProgram);
          }}
          variant='primary'
          >
            {i18n.updateButtonText}
          </Button>
        }
      >
        {loadingProjects ? i18n.headerLoading : `${selectedProject?.projectName} program`}
      </Header>
    </>;
  }

  function renderContent() {
    return <>
      <SpaceBetween size='l'>
        {renderProjectDetails()}
        {renderTabs()}
      </SpaceBetween>
    </>;
  }

  function renderProjectDetails() {
    return <Container
      header={
        <Header variant="h2">
          {i18n.header}
        </Header>
      }
    >
      {loadingProjects && <Spinner/>}
      {!loadingProjects && <ColumnLayout columns={2} variant="text-grid">
        <SpaceBetween size="l">
          <div>
            <Box variant="awsui-key-label">{i18n.detailsId}</Box>
            <div>{selectedProject?.projectId}</div>
          </div>
          <div>
            <Box variant="awsui-key-label">{i18n.detailsName}</Box>
            <div>{selectedProject?.projectName}</div>
          </div>
        </SpaceBetween>
        <SpaceBetween size="l">
          <div>
            <Box variant="awsui-key-label">{i18n.detailsDecription}</Box>
            <div>{selectedProject?.projectDescription}</div>
          </div>
          <div>
            <Box variant="awsui-key-label">{i18n.detailsStatus}</Box>
            <div><StatusIndicator type={selectedProject?.isActive ? 'success' : 'stopped'}>
              {getProjectStatusText()}
            </StatusIndicator></div>
          </div>
        </SpaceBetween>
      </ColumnLayout>}
    </Container>;
  }

  function getProjectStatusText() {
    return selectedProject?.isActive ? i18n.projectActive : i18n.projectInactive;
  }

  function renderTabs() {
    const tabs = [];

    if (isFeatureAccessible(RoleBasedFeature.OnboardAccount)) {
      tabs.push(
        {
          label: i18n.tabAccounts,
          id: TAB_ID_ACCOUNTS,
          content: <ProjectAccounts/>
        }
      );
    }

    return (
      <Tabs
        tabs={tabs}
        activeTabId={selectedTab || TAB_ID_ACCOUNTS}
        onChange={(e) => setSelectedTab(e.detail.activeTabId)}
      />
    );
  }

  function renderTools() {
    return (
      <HelpPanel
        header={<h2>Program details</h2>}
      >
        <h3>Accounts</h3>
        <p>
          Users with Frontend Admin role can onboard or reonboard AWS accounts to a program.
        </p>
        <p>
          To onboard a new account:
          You should see new account appear in the list. If account onboarding is successful,
          account status will change from OnBoarding to Active.
          If there where onboarding errors, the status will change to Failed.
        </p>
        <ol>
          <li>Click Onboard.</li>
          <li>Enter the required details.</li>
          <li>Click Onboard.</li>
        </ol>
        <p>
          Frontend Admins can also restart the onboarding by clicking Restart onboarding button.
          Note, that Active account status will stay Active in this case,
          because users may already have provisioned workbenches in these accounts.
        </p>
      </HelpPanel>
    );
  }
};

export { projectDetails as ProjectDetails };
