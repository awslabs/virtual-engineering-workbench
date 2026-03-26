import {
  Alert,
  Badge,
  Box,
  Button,
  ButtonDropdown,
  Cards,
  CardsProps,
  Header,
  HelpPanel,
  Pagination,
  PropertyFilter,
  SpaceBetween,
  Spinner,
  StatusIndicator,
  TextContent,
  ButtonDropdownProps,
  Popover,
} from '@cloudscape-design/components';
import { RoleAccessToggle } from '../shared/role-access-toggle.tsx';
import { RoleBasedFeature } from '../../../state/index.ts';
import {
  AdditionalConfiguration,
  ProvisionedProduct,
} from '../../../services/API/proserve-wb-provisioning-api/index.ts';
import {
  provisioningAPI,
} from '../../../services/API';
import { EnabledRegion, REGION_NAMES } from '../../user-preferences/index.ts';
import { useNavigationPaths } from '../../layout/navigation/navigation-paths.logic.ts';
import {
  PRODUCT_INSTANCE_STATES,
  PRODUCT_STATE_TRANSLATIONS,
} from './logic.ts';
import {
  ProvisionedProductHeaderActionsProps,
  ProvisionedProductListHeaderProps,
  ProvisionedProductCardVersionProps,
  ProvisionedProductCardActionsProps,
  ProvisionedProductCardStatusProps,
  ProvisionedProductListProps,
  ProvisionedProductsToDeleteListProps,
  ProvisionedProductsTranslations,
} from './interface.ts';
import { useState } from 'react';
import { ProvisionedProductLogin } from './provisioned-product-actions/page';
import { useCommonProvisionedProductState } from './common.logic.ts';
import { PopoverOnHover } from '../shared/popover-on-hover.tsx';
import { StopProductPrompt } from './stop-product-prompt/stop-product-prompt';
import { FeatureToggle } from '../shared/feature-toggle.tsx';
import { Feature } from '../../feature-toggles/feature-toggle.state.ts';
import {
  UpdateProvisionedProductPrompt
} from './provisioned-product-update-prompt/update-provisioned-product-prompt';

/* eslint @typescript-eslint/no-magic-numbers: "off" */

export function ProvisionedProductsToDeleteList({
  targets,
  translations,
}: ProvisionedProductsToDeleteListProps) {
  const listTargets = targets.map((item) =>
    <li key={item.productId}>
      <b>{item.productName}</b>
    </li>
  );
  return (
    <TextContent>
      <p>{translations.deprovisionModalText1}</p>
      <ul>{listTargets}</ul>
      <p>{translations.deprovisionModalText2}</p>
    </TextContent>
  );
}

export function Tools(translations: ProvisionedProductsTranslations) {
  return (
    <HelpPanel header={<h2>{translations.infoPanelHeader}</h2>}>
      <SpaceBetween size={'s'}>
        <Box variant="awsui-key-label">{translations.infoPanelLabel1}</Box>
        <Box variant="p">{translations.infoPanelMessage1}</Box>
        <Box variant="p">{translations.infoPanelMessage2}</Box>
        <Box variant="awsui-key-label">{translations.infoPanelLabel2}</Box>
        <Box variant="p">{translations.infoPanelMessage3}</Box>
        <Box variant="p">{translations.infoPanelMessage4}</Box>
        <Box variant="p">{translations.infoPanelMessage5}</Box>
      </SpaceBetween>
    </HelpPanel>
  );
}

export function ProvisionedProductHeaderActions({
  isInTurnDownMode,
  isLoading,
  isValidToTurnDown,
  translations,
  onRefreshHandler,
  onRemoveHandler,
  onProvisionHandler,
  onCancelRemoveHandler,
  onSubmitRemoveHandler,
}: ProvisionedProductHeaderActionsProps) {
  if (isInTurnDownMode) {
    return (
      <SpaceBetween size={'xs'} direction={'horizontal'}>
        <Button
          iconName="refresh"
          loading={isLoading}
          onClick={onRefreshHandler}
          data-test="vt-reload-btn"
        />
        <RoleAccessToggle feature={RoleBasedFeature.ProvisionVirtualTarget}>
          <Button onClick={onCancelRemoveHandler}>
            {translations.headerButtonCancel}
          </Button>
        </RoleAccessToggle>
        <RoleAccessToggle feature={RoleBasedFeature.RemoveVirtualTarget}>
          <Button
            data-test="confirm-remove-workflow"
            variant='primary'
            onClick={onSubmitRemoveHandler}
            disabled={!isValidToTurnDown}
          >
            {translations.headerButtonSubmitTurnDown}
          </Button>
        </RoleAccessToggle>
      </SpaceBetween>
    );
  }
  return (
    <SpaceBetween size={'xs'} direction={'horizontal'}>
      <Button
        iconName="refresh"
        loading={isLoading}
        onClick={onRefreshHandler}
        data-test="vt-reload-btn"
      />
      <RoleAccessToggle feature={RoleBasedFeature.RemoveVirtualTarget}>
        <Button data-test="start-remove-workflow" onClick={onRemoveHandler}>
          {translations.headerButtonTurnDown}
        </Button>
      </RoleAccessToggle>
      <RoleAccessToggle feature={RoleBasedFeature.ProvisionVirtualTarget}>
        <Button
          variant='primary'
          onClick={onProvisionHandler}>
          {translations.headerButtonProvision}
        </Button>
      </RoleAccessToggle>
    </SpaceBetween>
  );
}

export function ProvisionedProductListHeader({
  actions,
  translations,
}: ProvisionedProductListHeaderProps) {
  return (
    <Header variant="awsui-h1-sticky" actions={actions}>
      {translations.headerTitle}
    </Header>
  );
}

function ProvisionedProductCardVersion({
  provisionedProduct,
  hideUpgradeButton,
  disableUpgradeButton,
  translations,
  upgradePage,
}: ProvisionedProductCardVersionProps) {
  const { navigateTo } = useNavigationPaths();

  function renderVersionName() {
    return <Popover
      dismissButton={false}
      position="right"
      size="small"
      header={translations.versionDescriptionPopoverHeader}
      content={
        provisionedProduct.versionDescription ||
        translations.versionDescriptionPopoverDefaultText
      }
    >
      {provisionedProduct.versionName}
    </Popover>;
  }

  if (hideUpgradeButton) {
    return renderVersionName();
  }

  return (
    <>
      <SpaceBetween direction='vertical' size='xxs'>
        <SpaceBetween direction="horizontal" size={'xxs'}>
          <Box>{renderVersionName()}</Box>
          <Box>-</Box>
          <Box variant="strong">
            <i>{translations.provisionedProductCardProductVersionUpdateAvailable}</i>
          </Box>
          <Box>|</Box>
          <Button
            variant="inline-link"
            disabled={disableUpgradeButton}
            onClick={() => {
              navigateTo(
                upgradePage,
                {},
                {
                  provisionedProduct,
                }
              );
            }}
            data-test={`upgrade-${provisionedProduct.provisionedProductId}`}
          >
            {translations.provisionedProductCardProductVersionUpdateButton}
          </Button>
        </SpaceBetween>
      </SpaceBetween>
    </>
  );
}

export function ProvisionedProductCardActions({
  isLoading,
  isInTurnDownMode,
  state,
  onViewDetailsHandler,
  translations,
  provisionedProduct,
  loginTranslations,
  headlessLogin,
  stateActionCompleteHandler,
  productType,
  renderLoginButton = true
}: ProvisionedProductCardActionsProps) {

  const [loginPromptVisible, setLoginPromptVisible] = useState(false);
  const [stopConfirmVisible, setStopConfirmVisible] = useState(false);

  const {
    handleStartProduct,
    handleStopProduct,
    startInProgress,
    stopInProgress,
  } = useCommonProvisionedProductState({
    provisionedProduct,
    stateActionCompleteHandler,
    setStopConfirmVisible
  });

  function renderSpinner() {
    return (
      <Box textAlign="center">
        <Spinner />
      </Box>
    );
  }

  function renderIsRunningButton() {
    return <>
      <Box float="right">
        <SpaceBetween size="xs" direction="horizontal">
          {renderDetailsButton()}
          <PopoverOnHover
            popoverContent={translations.popoverContent}
            popoverSize={'medium'}
            popoverPosition={'top'}
            popoverTriggerType={'custom'}
            buttonLabel={translations.cardActionStop}
            buttonOnClick={() => setStopConfirmVisible(true)}
            buttonDisabled={isInTurnDownMode}
          />
          {renderLoginButton && <Button
            variant="primary"
            onClick={() => setLoginPromptVisible(true)}
            disabled={isInTurnDownMode || stopInProgress }
            data-test="login-button"
          >
            {translations.loginPromptConfirm}
          </Button>}
        </SpaceBetween>
      </Box>
      <ProvisionedProductLogin
        loginPromptVisible={loginPromptVisible}
        setLoginPromptVisible={setLoginPromptVisible}
        provisionedProduct={provisionedProduct}
        i18n={loginTranslations}
        headlessLogin={headlessLogin}
      />
      <StopProductPrompt
        provisionedProduct={provisionedProduct}
        stopConfirmVisible={stopConfirmVisible}
        setStopConfirmVisible={setStopConfirmVisible}
        productType={productType}
        handleStopProduct={handleStopProduct}
        stopInProgress={stopInProgress} />
    </>;
  }

  function renderDetailsButton() {
    return <Button
      variant="link"
      onClick={onViewDetailsHandler}
      disabled={isInTurnDownMode}
      data-test="details-button"
    >
      {translations.cardActionDetails}
    </Button>;
  }

  function renderIsStoppedButton(translations: ProvisionedProductsTranslations) {
    return (
      <Box float="right">
        <SpaceBetween size="xs" direction="horizontal">
          {renderDetailsButton()}
          <Button
            variant="primary"
            onClick={handleStartProduct}
            loading={startInProgress}
            disabled={isInTurnDownMode}
            data-test="start-button"
          >
            {translations.cardActionStart}
          </Button>
        </SpaceBetween>
      </Box>
    );
  }

  if (isLoading) {
    return renderSpinner();
  }

  if (state === PRODUCT_INSTANCE_STATES.Running) {
    return renderIsRunningButton();
  }

  if (state === PRODUCT_INSTANCE_STATES.Stopped) {
    return renderIsStoppedButton(translations);
  }

  return <Box float="right">
    <SpaceBetween size="xs" direction="horizontal">
      {renderDetailsButton()}
    </SpaceBetween>
  </Box>;
}

function ProvisionedProductCardStatus({
  decideStatusIndicatorType,
  provisionedProductId,
  productStatus,
}: ProvisionedProductCardStatusProps) {
  return (
    <StatusIndicator
      type={decideStatusIndicatorType}
      data-test={`wb-status-${provisionedProductId}`}
    >
      {PRODUCT_STATE_TRANSLATIONS.get(productStatus) || productStatus}
    </StatusIndicator>
  );
}

function getOSImage(osVersion: string) {
  if (osVersion.toLocaleLowerCase().includes('ubuntu')) {
    return <img src='/ubuntu.svg' width={20} height={20} />;
  } else if (osVersion.toLocaleLowerCase().includes('windows')) {
    return <img src='/windows.svg' width={20} height={20} />;
  } else if (osVersion.toLocaleLowerCase().includes('blackberry')) {
    return <img src='/blackberry.svg' width={20} height={20} />;
  }
  return <></>;
}

export function ProvisionedProductList({
  targets,
  isCardDisabled,
  header,
  empty,
  selectionType,
  paginationProps,
  filterProps,
  isInTurnDownMode,
  collectionProps,
  isLoading,
  handleViewDetail,
  decideStatusIndicatorType,
  decideToHideUpgradeButton,
  decideToDisableUpgradeButton,
  additionalCardDefinitionSections,
  translations,
  upgradePage,
  loginTranslations,
  headlessLogin,
  stateActionCompleteHandler,
  disableCardMenu,
}: ProvisionedProductListProps) {

  const [updatePromptVisible, setUpdatePromptVisible] = useState(false);
  const [selectedProvisionedProduct, setSelectedProvisionedProduct] =
    useState<ProvisionedProduct>(targets[0]);
  const [updateType, setUpdateType] = useState<string>('instance type');

  const getJobNameValue = (vvAdditionalConfiguration: AdditionalConfiguration) => {
    const jobName = vvAdditionalConfiguration.parameters!.find(parameter =>
      parameter.key === 'jobName');
    return jobName && jobName.value ? jobName.value : 'N/A';
  };

  const getPlatformValue = (vvAdditionalConfiguration: AdditionalConfiguration) => {
    const platformType = vvAdditionalConfiguration.parameters!.find(parameter =>
      parameter.key === 'platformType');
    return platformType && platformType.value ? platformType.value : 'N/A';
  };

  const getVersionValue = (vvAdditionalConfiguration: AdditionalConfiguration) => {
    const version = vvAdditionalConfiguration.parameters!.find(parameter =>
      parameter.key === 'version');
    return version && version.value ? version.value : 'N/A';
  };

  const getPlatformInfo = (product: ProvisionedProduct) => {
    const vvAdditionalConfiguration = product.additionalConfigurations?.find(configuration =>
      configuration.type === 'VVPL_PROVISIONED_PRODUCT_CONFIGURATION');
    if (vvAdditionalConfiguration && vvAdditionalConfiguration.parameters) {
      return <Alert statusIconAriaLabel="Info">
        {translations.mappingInfo(
          getJobNameValue(vvAdditionalConfiguration),
          getPlatformValue(vvAdditionalConfiguration),
          getVersionValue(vvAdditionalConfiguration))}
      </Alert>;
    }
    return <></>;
  };

  const getExperimentalBanner = (product: ProvisionedProduct) => {
    if (product.provisioningParameters?.some(x => x.key === 'Experimental' && x.value === 'True')) {
      return <Alert>{translations.experimentalWorkbenchBanner}</Alert>;
    }
    return <></>;
  };

  function handleDropdownClick(product: ProvisionedProduct, { detail }:
  CustomEvent<ButtonDropdownProps.ItemClickDetails>) {
    if (detail.id === 'updateInstanceType') {
      setUpdatePromptVisible(true);
      setSelectedProvisionedProduct(product);
      setUpdateType('instance type');
    } else {
      setUpdatePromptVisible(true);
      setSelectedProvisionedProduct(product);
      setUpdateType('version');
    }
  }

  const ALLOWED_STATUS_FOR_UPDATE = [PRODUCT_INSTANCE_STATES.Running, PRODUCT_INSTANCE_STATES.Stopped];
  const renderDropdownActions = (e: ProvisionedProduct) =>
    <FeatureToggle feature={Feature.ProvisionedProductManualUpdates}>
      <ButtonDropdown
        items={[
          {
            id: 'updateInstanceType',
            text: translations.provisionedProductUpdateInstanceTypeAction,
          },
          {
            id: 'updateVersion',
            text: translations.provisionedProductUpdateVersionAction,
          },
        ]}
        variant={e.recommendedInstanceType ? 'inline-icon' : 'icon'}
        onItemClick={(event) => handleDropdownClick(e, event)}
      />
    </FeatureToggle>
  ;

  const truncateProductNameFullWords = (nameParts: string[], maxHeaderTextLen: number) => {
    let truncatedName = '';
    for (const namePart of nameParts) {
      if (namePart.length + truncatedName.length < maxHeaderTextLen) {
        truncatedName = truncatedName.concat(' ', namePart);
      } else {
        break;
      }
    }
    return truncatedName;
  };

  const truncateProducName = (productName: string) => {
    const maxHeaderTextLen = 24;
    const zero = 0;
    const nameParts = productName.split(' ');
    if (nameParts.length === 0) { return ''; }
    if (nameParts[zero].length > maxHeaderTextLen) {
      return `${nameParts[zero].substring(zero, maxHeaderTextLen)}...`;
    }
    return truncateProductNameFullWords(nameParts, maxHeaderTextLen);
  };


  const renderHeader = (e: ProvisionedProduct) => {
    return (
      <Header variant="h2" description={e.productName} actions={
        ALLOWED_STATUS_FOR_UPDATE.includes(e.status) &&
          !isInTurnDownMode &&
          !disableCardMenu &&
          renderDropdownActions(e)}>
        <div className="cards-title">{truncateProducName(e.productName)}</div>
      </Header>
    );

  };


  const cardDefinition: CardsProps.CardDefinition<ProvisionedProduct> = {
    header: (e) => renderHeader(e),
    sections: [
      ...[
        {
          id: 'info',
          content: (e: ProvisionedProduct) => <SpaceBetween direction='vertical' size='xs'>
            {getPlatformInfo(e)}
            {getExperimentalBanner(e)}
          </SpaceBetween>
        },
        {
          id: 'stage-region',
          header: translations.provisionedProductCardStageAndRegion,
          content: (e: ProvisionedProduct) => {
            return (
              <SpaceBetween size={'xxs'} direction='horizontal'>
                <Badge color="blue">{e.stage?.toUpperCase() ?? 'n/a'}</Badge>
                /
                <Box>
                  {REGION_NAMES[
                    (e.region as EnabledRegion) || 'unspecified'
                  ] || e.region}
                </Box>
              </SpaceBetween>
            );
          },
        },
        {
          id: 'version',
          header: translations.provisionedProductCardProductVersion,
          content: (e: ProvisionedProduct) =>
            <ProvisionedProductCardVersion
              hideUpgradeButton={decideToHideUpgradeButton(e)}
              disableUpgradeButton={decideToDisableUpgradeButton(e)}
              provisionedProduct={e}
              translations={translations}
              upgradePage={upgradePage}
            />
          ,
        },
        {
          id: 'status',
          header: translations.provisionedProductCardStatus,
          content: (e: ProvisionedProduct) =>
            <ProvisionedProductCardStatus
              productStatus={e.status}
              provisionedProductId={e.provisionedProductId}
              decideStatusIndicatorType={
                isLoading(e) ? 'loading' : decideStatusIndicatorType(e.status)
              }
            />
          ,
        },
        {
          id: 'operating-system',
          header:
            <FeatureToggle feature={Feature.ProductMetadata}>
              {translations.provisionedProductCardOS}
            </FeatureToggle>,
          content: (e: ProvisionedProduct) =>
            <FeatureToggle feature={Feature.ProductMetadata}>
              <SpaceBetween size={'xxxs'} direction='horizontal'>
                {getOSImage(e.osVersion || 'N/A')} {e.osVersion || 'N/A'}
              </SpaceBetween>
            </FeatureToggle>
        }
      ],
      ...additionalCardDefinitionSections ?? [
        {
          id: 'actions',
          content: (e: ProvisionedProduct) =>
            <ProvisionedProductCardActions
              state={e.status}
              isLoading={isLoading(e)}
              isInTurnDownMode={isInTurnDownMode}
              onViewDetailsHandler={() => handleViewDetail(e)}
              provisionedProduct={e}
              translations={translations}
              loginTranslations={loginTranslations}
              headlessLogin={headlessLogin}
              stateActionCompleteHandler={stateActionCompleteHandler}
            />
          ,
        },
      ],
    ],
  };




  const cardLayoutDefinition: CardsProps.CardsLayout[] = [
    { cards: 1 },
    { minWidth: 600, cards: 2 },
    { minWidth: 900, cards: 3 },
    { minWidth: 1200, cards: 4 },
  ];

  return (
    <>
      <UpdateProvisionedProductPrompt
        provisionedProduct={selectedProvisionedProduct}
        updateConfirmVisible={updatePromptVisible}
        setUpdatePromptVisible={setUpdatePromptVisible}
        serviceApi={provisioningAPI}
        stateActionCompleteHandler={stateActionCompleteHandler}
        updateType={updateType}
      />
      <Cards
        {...collectionProps}
        ariaLabels={{
          itemSelectionLabel: (_, t) => `select ${t.productName}`,
          selectionGroupLabel: translations.ariaSelectionGroupLabel,
        }}
        cardDefinition={cardDefinition}
        cardsPerRow={cardLayoutDefinition}
        isItemDisabled={(item: ProvisionedProduct) => isCardDisabled(item)}
        items={targets}
        loading={isLoading()}
        loadingText={translations.ariaSelectionGroupLabel}
        selectionType={selectionType}
        stickyHeader={true}
        variant="full-page"
        filter={
          <PropertyFilter
            {...filterProps}
            i18nStrings={translations.propertyFilterI18nStrings}
            expandToViewport
            hideOperations
            tokenLimit={2}
          />
        }
        header={header}
        pagination={<Pagination {...paginationProps} />}
        empty={empty}
      />
    </>
  );
}
