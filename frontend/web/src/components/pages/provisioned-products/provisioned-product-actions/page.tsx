import {
  Alert,
  Box,
  FormField,
  Link,
  RadioGroup,
  SpaceBetween,
  Checkbox,
  Button,
  ColumnLayout,
} from '@cloudscape-design/components';
import { useState, useMemo } from 'react';
import { useRecoilValue } from 'recoil';
import {
  filteredAssignmentsForSelectedProjectState
} from '../../../../state/index.ts';
import { loggedInUserState } from '../../../session-management/logged-user.ts';
import { Feature } from '../../../feature-toggles/feature-toggle.state.ts';
import { FeatureToggle } from '../../shared/feature-toggle.tsx';
import { UserPrompt } from '../../shared/user-prompt.tsx';
import { WORKBENCH_CONNECTION_TYPE } from '../../workbenches/workbenches.static.ts';
import {
  useWorkbenchFeatureToggles,
} from '../../../feature-toggles/feature-toggle-workbench.hook.ts';
import { useFeatureToggles } from '../../../feature-toggles/feature-toggle.hook.ts';
import { useLocalStorage } from '../../../../hooks/index.ts';
import { extractErrorResponseMessage } from '../../../../utils/api-helpers.ts';
import { provisioningAPI } from '../../../../services/API/provisioning-api.ts';
import { ProvisionedProductLoginProps } from './interface.ts';
import { useNotifications } from '../../../layout/index.ts';
import {
  GetProvisionedProductUserSecretResponse
} from '../../../../services/API/proserve-wb-provisioning-api/index.ts';
import { ValueWithLabel } from '../../shared/value-with-label.tsx';
import { CopyText } from '../../shared/index.ts';
import { LoginConfig } from './provisioned-product-login-types';

const EMPTY_COUNT = 0;


function provisionedProductLogin({
  loginPromptVisible,
  setLoginPromptVisible,
  provisionedProduct,
  i18n,
  headlessLogin,
}: ProvisionedProductLoginProps) {
  const { isFeatureEnabled } =
    useWorkbenchFeatureToggles(provisionedProduct);
  const { isFeatureEnabled: isGlobalFeatureEnabled } = useFeatureToggles();
  const { showErrorNotification } = useNotifications();

  const enabledLoginOptions = useMemo(() => {
    return [
      ...(isFeatureEnabled(Feature.RDPConnectionOption) ||
        isGlobalFeatureEnabled(Feature.RDPConnectionOption)) && !headlessLogin ?
        [WORKBENCH_CONNECTION_TYPE.RDP] : [],
      ...(isFeatureEnabled(Feature.DCVConnectionOptions) ||
        isGlobalFeatureEnabled(Feature.DCVConnectionOptions)) && !headlessLogin ?
        [WORKBENCH_CONNECTION_TYPE.DcvFile, WORKBENCH_CONNECTION_TYPE.DcvBrowser] : [],
      ...provisionedProduct.sshEnabled ? [WORKBENCH_CONNECTION_TYPE.SSH] : [],
    ];
  }, [isFeatureEnabled, isGlobalFeatureEnabled, provisionedProduct, headlessLogin]);

  const [selectedIPForLogon] = useState(
    provisionedProduct.publicIp || provisionedProduct.privateIp || undefined
  );

  const [selectedConnectionOption, setSelectedConnectionOption] = useState(getDefaultLoginOption());
  const [confirmInProgress, setConfirmInProgress] = useState(false);
  const [connectDirectly, setConnectDirectly] = useState(true);

  const loggedInUser = useRecoilValue(loggedInUserState);
  const filteredAssignment = useRecoilValue(
    filteredAssignmentsForSelectedProjectState
  );
  const aDGroups = getADGroups();
  const adDomains = getADDomains();
  const [selectedDomain, setSelectedDomain] = useState(
    adDomains.length > EMPTY_COUNT ? adDomains[0] : ''
  );
  const [passwordRevealInProgress, setPasswordRevealInProgress] = useState(false);
  const [
    userCredentials,
    setUserCredentials
  ] = useState<GetProvisionedProductUserSecretResponse | undefined>();
  const loginTypes = useMemo(() => LoginConfig.initLoginConfig(), []);
  const isMultipleDomain = adDomains.length > EMPTY_COUNT;
  const [selectedAllMonitors, setselectedAllMonitors] = useLocalStorage(
    'workbench-login#use-all-monitors',
    'true'
  );

  function getADDomains(): string[] {
    return aDGroups.map((x) => x.domain || '');
  }

  return (
    <>
      <UserPrompt
        onConfirm={() => {
          handleConfirm();
        }}
        onCancel={() => setLoginPromptVisible(false)}
        headerText={i18n.loginPromptHeader}
        content={
          <>
            <SpaceBetween size="l">
              <FeatureToggle feature={Feature.BetaUserInfoText}>
                {renderBetaUserWarning()}
              </FeatureToggle>
              {renderStandardLogin()}
            </SpaceBetween>
          </>
        }
        cancelText={i18n.loginPromptCancel}
        confirmText={i18n.loginPromptConfirm}
        confirmButtonLoading={confirmInProgress}
        visible={loginPromptVisible}
        confirmButtonDisabled={!selectedIPForLogon || !selectedConnectionOption}
        data-test="login-modal"
      />
    </>
  );

  function getADGroups() {
    const filteredADGroups = filteredAssignment[0].activeDirectoryGroups;
    return filteredADGroups ? filteredADGroups : [];
  }

  function getDefaultLoginOption() {
    if (enabledLoginOptions.length) {
      return enabledLoginOptions[0];
    }
    return null;
  }

  /* eslint complexity: "off" */
  async function handleConfirm() {
    try {
      if (!selectedConnectionOption) { throw Error(i18n.errorNoConnectionMethodSelected); }
      if (!loggedInUser?.user) { throw Error(i18n.errorNoUserData); }

      setConfirmInProgress(true);

      const loginType = loginTypes.getLoginType(selectedConnectionOption);

      await authorizeUserIpAddress();

      const loginResult = await loginType?.doLogin({
        user: loggedInUser.user,
        userDomain: selectedDomain,
        provisionedProduct,
        connectAddress: selectedIPForLogon,
        extendToAllMonitors: selectedAllMonitors === 'true',
        vpnConnection: connectDirectly,
      });

      switch (loginResult.type) {
        case 'file': {
          if (loginResult.loginFile) {
            downloadFile(
              loginResult.loginFile.loginFileContent,
              loginResult.loginFile.loginFileName
            );
          }
          break;
        }
        case 'browser': {
          window.open(loginResult.loginUrl, '_blank');
          hideLoginPrompt();
          break;
        }
        default: {
          throw Error('Unable to determine login type.');
        }
      }

    } catch (err) {
      showErrorNotification({
        header: i18n.loginError,
        content: await extractErrorResponseMessage(err),
      });
    } finally {
      setConfirmInProgress(false);
    }
  }

  function authorizeUserIpAddress() {
    if (isGlobalFeatureEnabled(Feature.AuthorizeUserIp)) {
      return provisioningAPI.authorizeUserIpAddress(
        provisionedProduct.projectId,
        provisionedProduct.provisionedProductId,
      );
    }
    return Promise.resolve();
  }

  function renderBetaUserWarning() {
    return <Alert type="warning">{i18n.betaUserPromptContent}</Alert>;
  }

  function renderDomainChoice() {
    if (isMultipleDomain) {
      return (
        <FormField description={i18n.loginDomainChoiceDescription}>
          <RadioGroup
            onChange={({ detail }) => setSelectedDomain(detail.value)}
            value={selectedDomain}
            items={adDomains.map((item) => ({
              value: item,
              label: item,
              description: i18n.loginSelectedDomainDescription(item),
            }))}
            data-test="login-domain-choice"
          />
        </FormField>
      );
    }
    return <></>;
  }

  function renderConnectionChoice() {
    i18n.loginPromptHeader = 'Select your network and connection type';
    if (!enabledLoginOptions.length) {
      return <></>;
    }

    return (
      <FormField description={i18n.loginConnectionChoiceDescription}>
        <RadioGroup
          onChange={({ detail }) => {
            setSelectedConnectionOption(detail.value);
            setConnectDirectly(true);
          }}
          value={selectedConnectionOption}
          items={renderLoginOptions()}
          data-test="login-type-choice"
        />
      </FormField>
    );
  }

  function renderLoginOptions() {
    return [
      ...enabledLoginOptions.includes(WORKBENCH_CONNECTION_TYPE.RDP) ?
        [{
          value: WORKBENCH_CONNECTION_TYPE.RDP,
          label: i18n.loginConnectionChoiceRDPLabel,
          description: i18n.loginConnectionChoiceRDPDescription,
        }] : [],
      ...enabledLoginOptions.includes(WORKBENCH_CONNECTION_TYPE.DcvFile) ?
        [{
          value: WORKBENCH_CONNECTION_TYPE.DcvFile,
          label: i18n.loginConnectionChoiceDCVFileLabel,
          description:
          <Box
            color="text-status-inactive"
            fontSize="body-s"
            variant="p"
          >
            {i18n.loginConnectionChoiceDCVFileDescription}
            <Link
              fontSize="body-s"
              external
              href="https://docs.aws.amazon.com/dcv/latest/userguide/client.html"
            >
              here
            </Link>
          </Box>
          ,
        }] : [],
      ...enabledLoginOptions.includes(WORKBENCH_CONNECTION_TYPE.DcvBrowser) ?
        [{
          value: WORKBENCH_CONNECTION_TYPE.DcvBrowser,
          label: i18n.loginConnectionChoiceDCVBrowserLabel,
          description: i18n.loginConnectionChoiceDCVBrowserDescription,
        }] : [],
      ...enabledLoginOptions.includes(WORKBENCH_CONNECTION_TYPE.SSH) ?
        [{
          value: WORKBENCH_CONNECTION_TYPE.SSH,
          label: i18n.loginConnectionChoiceSSHLabel,
          description: i18n.loginConnectionChoiceSSHDescription,
        }] : [],
    ];
  }

  function renderRevealPassword() {
    if (!shouldRenderRevealPassword()) { return <></>; }
    return (
      <FormField>
        {!userCredentials && <Button
          onClick={revealUserCredentials}
          loading={passwordRevealInProgress}>
          {i18n.loginUserCredentialsShowButton}
        </Button>}
        {userCredentials && <>
          <ColumnLayout columns={2} variant="text-grid">
            <ValueWithLabel label={i18n.loginUserCredentialsUsername}>
              <CopyText copyText={userCredentials.username || ''}/>
            </ValueWithLabel>
            <ValueWithLabel label={i18n.loginUserCredentialsPassword}>
              <CopyText copyText={userCredentials.password || ''}/>
            </ValueWithLabel>
          </ColumnLayout>
        </>}
      </FormField>
    );
  }

  function shouldRenderRevealPassword() {
    return provisionedProduct.usernamePasswordLoginEnabled && selectedConnectionOption && new Set([
      WORKBENCH_CONNECTION_TYPE.DcvBrowser,
      WORKBENCH_CONNECTION_TYPE.RDP,
      WORKBENCH_CONNECTION_TYPE.DcvFile,
    ]).has(selectedConnectionOption);
  }

  function renderMultipleMonitorChoice() {
    return (
      <FormField>
        <Checkbox
          checked={selectedAllMonitors === 'true'}
          onChange={(onChangeEvent) =>
            setselectedAllMonitors(`${onChangeEvent.detail.checked}`)
          }
          description={i18n.loginMultipleMonitorChoiceDescription}
          disabled={!selectedConnectionOption ||
            ![
              WORKBENCH_CONNECTION_TYPE.RDP,
              WORKBENCH_CONNECTION_TYPE.DcvFile,
            ].includes(selectedConnectionOption)
          }
          data-test="extend-monitor"
        >
          Extend to all monitors
        </Checkbox>
      </FormField>
    );
  }

  function downloadFile(fileContent: string, fileName: string) {
    // Create download object
    const e = document.createElement('a');
    e.setAttribute(
      'href',
      'data:text;charset=utf-8,' + encodeURIComponent(fileContent)
    );
    e.setAttribute('download', fileName);

    // Trigger the download
    e.style.display = 'none';
    document.body.appendChild(e);
    e.click();
    document.body.removeChild(e);
    hideLoginPrompt();
  }

  function hideLoginPrompt() {
    if (userCredentials) { return; }
    setLoginPromptVisible(false);
  }

  function revealUserCredentials() {
    setPasswordRevealInProgress(true);

    provisioningAPI.getUserCredential(
      provisionedProduct.projectId,
      provisionedProduct.provisionedProductId,
    ).then((resp: GetProvisionedProductUserSecretResponse) => {
      setUserCredentials(resp);
    }).finally(() => {
      setPasswordRevealInProgress(false);
    }).catch(async (e: unknown) => {
      showErrorNotification({
        header: i18n.loginUserCredentialRevealError,
        content: await extractErrorResponseMessage(e),
      });
    });
  }

  function renderStandardLogin() {
    return <>
      { renderDomainChoice() }
      { renderConnectionChoice() }
      { renderRevealPassword() }
      { renderMultipleMonitorChoice() }
    </>;
  }

}

export { provisionedProductLogin as ProvisionedProductLogin };
