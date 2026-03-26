/* eslint complexity: "off" */

import {
  Box,
  Button,
  Container,
  Form,
  FormField,
  Header,
  HelpPanel,
  Icon,
  Input,
  RadioGroup,
  Select,
  SpaceBetween
} from '@cloudscape-design/components';
import { FC, useEffect } from 'react';
import { BreadcrumbItem } from '../../../layout';
import { WorkbenchAppLayout } from '../../../layout/workbench-app-layout/workbench-app-layout';
import { useProjectAccountOnboarding } from './project-account-on-board.logic';
import { EnabledRegion, REGION_NAMES } from '../../../user-preferences';
import { useRecoilValue } from 'recoil';
import { selectedProjectState } from '../../../../state';
import { useNavigationPaths } from '../../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../../layout/navigation/navigation.static';
import { Technology } from '../../../../services/API/proserve-wb-projects-api';

// eslint-disable-next-line @typescript-eslint/no-empty-object-type
interface Params { }

const i18n = {
  breadcrumbLevel1: 'Administration: Program',
  breadcrumbLevel2: 'Onboard account',
  breadcrumbProjectUnknown: '(...)',
  buttonCancel: 'Cancel',
  buttonOnboard: 'Onboard',
  headerDetails: 'Details',
  inputAccountNameLabel: 'Name',
  inputAccountNamePlaceholder: 'acct-vew-bsn0000000-dev-user',
  inputAccountTypeLabel: 'Type',
  inputAccountTypeUserLabel: 'User',
  inputAccountTypeUserDescription: 'Choose this option if account will be used to provision workbenches.',
  inputAccountStageLabel: 'Environment',
  inputAccountStageDevLabel: 'DEV',
  inputAccountStageDevDescription: 'Choose this option if account will be used to develop workbenches.',
  inputAccountStageQALabel: 'QA',
  inputAccountStageQADescription: 'Choose this option if account will be used to test workbenches.',
  inputAccountStagePRODLabel: 'PROD',
  inputAccountStagePRODDescription: 'Choose this option if account will be used by the end users.',
  inputAccountIdLabel: 'Account ID',
  inputAccountIdPlaceholder: '001234567890',
  inputDescriptionLabel: 'Description',
  inputDescriptionPlaceholder: 'Workbench account for program X',
  inputTechnologyIdLabel: 'Technology',
  inputRegionLabel: 'Region',
  pageHeader: (projectName?: string) => `Onboard AWS account to ${projectName}`,
  infoPanelHeader: 'Onboard account',
  infoPanelLabel1: 'What can I accomplish here?',
  infoPanelMessage1: `The account ID is the AWS account ID and should be 12 numbers. This ID can be 
  found in the AWS console.`,
  infoPanelMessage2: `The name refers to the AWS account and should match the following format: 
  acct-vew-bsn0000000-dev-user. This name can be found in the AWS console.`,
  infoPanelMessage3: 'The account type is set to user. A user account is used to provision workbenches.',
  infoPanelMessage4: 'Provide a description to assist in identifying the account at a later point in time.',
  infoPanelMessage5: 'Select one environment the AWS account will be used for.',
  infoPanelMessage6: 'Select the region this AWS account is based in. Only one region may be available.',
  infoPanelMessage7: `The technology has been preselected based off of your previous selection. If needed, 
  this can be changed using the dropdown.`,
  infoPanelLearnMore: 'Learn more ',
  infoPanelLink: 'View your AWS account ID'
};

const onboardProjectAccount: FC<Params> = () => {
  const selectedProject = useRecoilValue(selectedProjectState);
  const { navigateTo, getPathFor } = useNavigationPaths();

  if (!selectedProject) {
    navigateTo(RouteNames.Programs);
  }

  const {
    accountName,
    setAccountName,
    accountType,
    setAccountType,
    awsAccountId,
    setAWSAccountId,
    accountDescription,
    setAccountDescription,
    isFormValid,
    onboardSuccess,
    onboardAccount,
    accountOnboardingInProgress,
    stage,
    setStage,
    technologyId,
    setTechnologyId,
    region,
    setRegion,
    enabledRegions,
    enabledRegionsLoading,
    technologies,
    isLoadingTechnologies,
  } = useProjectAccountOnboarding({ projectId: selectedProject.projectId || '' });

  useEffect(() => {
    if (onboardSuccess) {
      navigateTo(RouteNames.Programs);
    }
  }, [onboardSuccess]);

  return <>
    <WorkbenchAppLayout
      breadcrumbItems={getBreadcrumbItems()}
      content={renderContent()}
      contentType="default"
      tools={renderTools()}
      headerText={i18n.pageHeader(selectedProject?.projectName)}
    />
  </>;

  function renderContent() {
    return <>
      <Form
        actions={
          <SpaceBetween direction="horizontal" size="xs">
            <Button variant="link" onClick={() => {
              navigateTo(RouteNames.Programs);
            }}>
              {i18n.buttonCancel}
            </Button>
            <Button
              variant="primary"
              disabled={!isFormValid()}
              onClick={onboardAccount}
              loading={accountOnboardingInProgress}
              data-test="onboard-account-button"
            >
              {i18n.buttonOnboard}
            </Button>
          </SpaceBetween>
        }
      >
        <SpaceBetween size="l">
          {renderAccountDetails()}
        </SpaceBetween>
      </Form>
    </>;
  }

  function renderAccountDetails() {
    return <>
      <Container
        header={<Header variant="h2">{i18n.headerDetails}</Header>}
      >
        <SpaceBetween size="l">
          {renderAccountIdInput()}
          {renderAccountNameInput()}
          {renderAccountTypeInput()}
          {renderAccountDescriptionInput()}
          {renderAccountStageInput()}
          {renderRegionDropdownInput()}
          {renderAccountTechnologyIdInput()}
        </SpaceBetween>
      </Container>
    </>;
  }


  function getBreadcrumbItems(): BreadcrumbItem[] {
    return [
      { path: i18n.breadcrumbLevel1, href: getPathFor(RouteNames.Programs) },
      { path: i18n.breadcrumbLevel2, href: '#' },
    ];
  }

  function renderTools() {
    return (
      <HelpPanel header={<h2>{i18n.infoPanelHeader}</h2>}
        footer={<div>
          <h3>
            {i18n.infoPanelLearnMore}<Icon name="external" />
          </h3>
          <a href="https://docs.aws.amazon.com/IAM/latest/UserGuide/console_account-alias.html#ViewYourAWSId">
            {i18n.infoPanelLink}</a>
        </div>}>
        <SpaceBetween size={'s'}>
          <Box variant="awsui-key-label">{i18n.infoPanelLabel1}</Box>
          <Box variant="p">{i18n.infoPanelMessage1}</Box>
          <Box variant="p">{i18n.infoPanelMessage2}</Box>
          <Box variant="p">{i18n.infoPanelMessage3}</Box>
          <Box variant="p">{i18n.infoPanelMessage4}</Box>
          <Box variant="p">{i18n.infoPanelMessage5}</Box>
          <Box variant="p">{i18n.infoPanelMessage6}</Box>
          <Box variant="p">{i18n.infoPanelMessage7}</Box>
        </SpaceBetween>
      </HelpPanel>
    );
  }

  function renderAccountNameInput() {
    return <>
      <FormField
        label={i18n.inputAccountNameLabel}
      >
        <Input
          value={accountName}
          onChange={({ detail: { value } }) => setAccountName(value)}
          placeholder={i18n.inputAccountNamePlaceholder}
          data-test="account-name-input"
        />
      </FormField>
    </>;
  }

  function renderAccountTypeInput() {
    return <>
      <FormField
        label={i18n.inputAccountTypeLabel}
      >
        <RadioGroup
          onChange={({ detail }) => setAccountType(detail.value)}
          value={accountType}
          items={[
            {
              value: 'USER',
              label: i18n.inputAccountTypeUserLabel,
              description: i18n.inputAccountTypeUserDescription
            },
          ]}
        />
      </FormField>
    </>;
  }


  function renderAccountStageInput() {
    return <>
      <FormField
        label={i18n.inputAccountStageLabel}
      >
        <RadioGroup
          onChange={({ detail }) => setStage(detail.value)}
          value={stage}
          data-test="account-stage-radio-group"
          items={[
            {
              value: 'dev',
              label: i18n.inputAccountStageDevLabel,
              description: i18n.inputAccountStageDevDescription
            },
            {
              value: 'qa',
              label: i18n.inputAccountStageQALabel,
              description: i18n.inputAccountStageQADescription
            },
            {
              value: 'prod',
              label: i18n.inputAccountStagePRODLabel,
              description: i18n.inputAccountStagePRODDescription
            },
          ]}
        />
      </FormField>
    </>;
  }

  function renderAccountIdInput() {
    return <>
      <FormField
        label={i18n.inputAccountIdLabel}
      >
        <Input
          value={awsAccountId}
          onChange={({ detail: { value } }) => setAWSAccountId(value)}
          placeholder={i18n.inputAccountIdPlaceholder}
          data-test="account-id-input"
        />
      </FormField>
    </>;
  }

  function renderAccountDescriptionInput() {
    return <>
      <FormField
        label={i18n.inputDescriptionLabel}
      >
        <Input
          value={accountDescription}
          onChange={({ detail: { value } }) => setAccountDescription(value)}
          placeholder={i18n.inputDescriptionPlaceholder}
          data-test="account-description-input"
        />
      </FormField>
    </>;
  }

  function renderAccountTechnologyIdInput() {
    const technologyOptions = technologies.map(getTechOption);
    const technologyAssociatedWithId = technologies.find(tech => tech.id === technologyId);
    // eslint-disable-next-line @stylistic/max-len
    const selectedTechnology = technologyAssociatedWithId ? getTechOption(technologyAssociatedWithId) : technologyOptions[0];
    return <>
      <FormField
        label={i18n.inputTechnologyIdLabel}
      >
        <Select
          selectedOption={selectedTechnology}
          onChange={({ detail }) => setTechnologyId(detail.selectedOption.value ?? '')
          }
          options={technologyOptions}
          statusType={isLoadingTechnologies ? 'loading' : undefined}
          data-test="account-technology-id-select"
        />
      </FormField>
    </>;
  }

  function getTechOption(t: Technology) {
    return {
      label: t.name, value: t.id
    };
  }

  function renderRegionDropdownInput() {
    const enabledRegionOptions = enabledRegions.map(getRegionOption);
    const selectedRegion = region ? getRegionOption(region) : null;

    return <FormField
      label={i18n.inputRegionLabel}
    >
      <Select
        selectedOption={selectedRegion}
        onChange={({ detail }) => setRegion(detail.selectedOption.value)
        }
        options={enabledRegionOptions}
        statusType={enabledRegionsLoading ? 'loading' : undefined}
      />
    </FormField>;
  }

  function getRegionOption(r: string) {
    return {
      label: REGION_NAMES[r as EnabledRegion] || r, value: r
    };
  }

};



export { onboardProjectAccount as OnboardProjectAccount };
