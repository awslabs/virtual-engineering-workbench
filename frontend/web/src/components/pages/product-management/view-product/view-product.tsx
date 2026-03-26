import { useParams } from 'react-router-dom';
import { WorkbenchAppLayout } from '../../../layout/workbench-app-layout/workbench-app-layout.tsx';
import { RouteNames } from '../../../layout/navigation/navigation.static.ts';
import { i18n } from './view-product.translations.ts';
import { useNavigationPaths } from '../../../layout/navigation/navigation-paths.logic.ts';
import {
  Header,
  Container,
  ColumnLayout,
  SpaceBetween,
  StatusIndicator,
  Spinner,
  Button,
  HelpPanel,
  Box,
} from '@cloudscape-design/components';
import React from 'react';
import {
  PromoteVersionPrompt,
  RetireVersionPrompt,
  RestoreVersionPrompt,
  ArchiveProductPrompt,
  SetAsRecommendedPrompt,
} from '../user-prompts';
import { Product, VersionSummary } from '../../../../services/API/proserve-wb-publishing-api';
import { ValueWithLabel } from '../../shared/value-with-label.tsx';
import { useProductDetails } from './view-product.logic.ts';
import { publishingAPI } from '../../../../services/API/publishing-api.ts';
import { useRecoilValue } from 'recoil';
import { selectedProjectState, RoleBasedFeature } from '../../../../state';
import { EmptyGridNotification } from '../../shared';
import { PRODUCT_STATUS_COLOR_MAP, PRODUCT_STATUS_MAP, PRODUCT_TYPE_MAP } from '../products.translations.ts';
import { ProductVersions } from './product-versions.tsx';
import { useRoleAccessToggle } from '../../../../hooks/role-access-toggle';


/* eslint-disable complexity */

const ZERO_INDEX = 0;

const ProductOverviewLoading = () => {
  return (
    <Container header={<Header>{i18n.containerHeader}</Header>}>
      <SpaceBetween alignItems="center" size="l">
        <Spinner />
      </SpaceBetween>
    </Container>
  );
};

type ProductOverviewHeaderProps = {
  title?: string,
  description?: string,
  productStatus?: string,
  archiveProduct: () => void,
  createVersion: () => void,
  goBack: () => void,
  loadProductDetails: () => void,
  isProductArchived: () => boolean,
};

const ProductOverviewHeader = ({
  title,
  description,
  productStatus,
  createVersion,
  archiveProduct,
  goBack,
  loadProductDetails,
  isProductArchived,
}: ProductOverviewHeaderProps) => {
  const isFeatureAccessible = useRoleAccessToggle();

  return (
    <Header
      variant='awsui-h1-sticky'
      description={description}
      actions={
        <SpaceBetween direction='horizontal' size='m'>
          <Button data-test='button-refresh-overview' iconName='refresh' onClick={loadProductDetails} />
          <Button
            onClick={goBack}
            variant='normal'>{i18n.buttonReturn}
          </Button>
          {!isProductArchived() &&
            <>
              {isFeatureAccessible(RoleBasedFeature.ArchiveProducts) &&
                <Button
                  data-test="archive-product-button"
                  onClick={archiveProduct}
                  disabled={productStatus !== PRODUCT_STATUS_MAP.CREATED.toUpperCase()}
                  variant='normal'>{i18n.buttonProductArchive}
                </Button>
              }
              <Button
                data-test="create-version-button"
                variant='primary'
                onClick={createVersion}>
                {i18n.buttonProductVersionCreate}
              </Button></>}
        </SpaceBetween>
      }
    >
      {title}
    </Header>
  );
};

type ProductOverviewDetailsProps = {
  prod?: Product,
};

const ProductOverviewDetails = ({ prod }: ProductOverviewDetailsProps) => {
  return (
    <Container data-test='product-overview' header={<Header>{i18n.containerHeader}</Header>}>
      <ColumnLayout columns={3} variant="text-grid">
        <ValueWithLabel data-test='product-name' label={i18n.productType}>
          {prod ? PRODUCT_TYPE_MAP[prod.productType] : ''}
        </ValueWithLabel>
        <ValueWithLabel data-test='product-status' label={i18n.status}>
          <StatusIndicator
            type={prod ? PRODUCT_STATUS_COLOR_MAP[prod.status] : 'pending'}
          >
            {prod ? PRODUCT_STATUS_MAP[prod.status] : ''}
          </StatusIndicator>
        </ValueWithLabel>
        <ValueWithLabel data-test='product-recommended-version' label={i18n.recommendedVersion}>
          {getRecommendedVersionName() || i18n.noValue}
        </ValueWithLabel>
        <ValueWithLabel data-test='product-id' label={i18n.productId}>
          {prod?.productId}
        </ValueWithLabel>
        <ValueWithLabel data-test='product-technology-name' label={i18n.technologyName}>
          {prod?.technologyName}
        </ValueWithLabel>
        <ValueWithLabel data-test='product-technology-id' label={i18n.technologyId}>
          {prod?.technologyId}
        </ValueWithLabel>
        <ValueWithLabel data-test='product-author' label={i18n.createdBy}>
          {prod?.createdBy}
        </ValueWithLabel>
      </ColumnLayout>
    </Container>
  );

  function getRecommendedVersionName() {
    if ((prod?.versions || []).length === ZERO_INDEX) {
      return i18n.noVersionsAvailable;
    }
    const version = prod?.versions?.find(x => x.versionId === prod.recommendedVersionId);
    return version === undefined ? i18n.noRecommendedVersionAvailable : version.name;
  }
};

export const ProductOverview = () => {
  const { getPathFor, navigateTo, goBack } = useNavigationPaths();
  const selectedProject = useRecoilValue(selectedProjectState);
  const { id } = useParams();
  const [selectedVersion, setSelectedVersion] = React.useState<VersionSummary>();
  const [promoteConfirmVisible, setPromoteConfirmVisible] = React.useState(false);
  const [archiveConfirmVisible, setArchiveConfirmVisible] = React.useState(false);
  const [retireConfirmVisible, setRetireConfirmVisible] = React.useState(false);
  const [restoreConfirmVisible, setRestoreConfirmVisible] = React.useState(false);
  const [setAsRecommendedConfirmVisible, setSetAsRecommendedConfirmVisible] = React.useState(false);

  const { product, error, isLoading, loadProductDetails } = useProductDetails({
    projectId: selectedProject.projectId,
    productId: id,
    serviceAPI: publishingAPI
  });

  function navigateToCreateProductVersion() {
    navigateTo(RouteNames.CreateProductVersion, {
      ':id': id
    });
  }

  function handleArchiveAction() {
    setArchiveConfirmVisible(true);
  }

  function navigateToUpdateProductVersion() {
    const versionId = selectedVersion?.versionId;

    navigateTo(RouteNames.UpdateProductVersion, {
      ':productId': id,
      ':versionId': versionId,
    }, {
      productVersionDescription: selectedVersion?.description,
      isRecommended: selectedVersion?.recommendedVersion,
    });
  }

  function navigateToVersionDetails(productId?: string, versionId?: string) {
    navigateTo(RouteNames.ProductVersionDetails, {
      ':productId': productId,
      ':versionId': versionId
    }, {
      productStatus: product?.status,
    });
  }

  const resolveErrorAction = React.useCallback(() => {
    navigateTo(RouteNames.Products);
  }, [navigateTo]);

  const breadCrumbsMemo = React.useMemo(() => {
    return [
      { path: i18n.breadcrumbLevel1, href: getPathFor(RouteNames.Products) },
      { path: i18n.breadcrumbLevel2, href: '#' },
    ];
  }, [getPathFor]);

  if (isLoading || !product) {
    return <WorkbenchAppLayout
      breadcrumbItems={breadCrumbsMemo}
      content={
        <SpaceBetween direction='vertical' size='l'>
          <ProductOverviewLoading />
          <ProductVersions
            isLoading={isLoading || !product}
            setSelectedVersion={setSelectedVersion}
            loadVersions={() => { return null; }}
            viewVersionDetails={() => { return null; }}
            updateVersionDetails={navigateToUpdateProductVersion}
            promoteVersion={() => { return null; }}
            emptyVersionResolveAction={() => { return null; }}
            retireVersion={() => { return null; }}
            isProductArchived={() => { return true; }}
            restoreVersion={() => { return null; }}
            setRecommendedVersion={(() => { return null; })}
          />
        </SpaceBetween>
      }
      contentType="default"
    />;
  }

  if (error) {
    return <WorkbenchAppLayout
      breadcrumbItems={breadCrumbsMemo}
      content={<EmptyGridNotification title={i18n.errorTitle}
        subTitle={i18n.errorSubTitle}
        actionButtonText={i18n.resolveError}
        actionButtonOnClick={resolveErrorAction} />}
      contentType="default"
    />;
  }

  function handlePromoteAction() {
    setPromoteConfirmVisible(true);
  }

  function handleRetireAction() {
    setRetireConfirmVisible(true);
  }

  function isProductArchived() {
    return product?.status === 'ARCHIVED';
  }

  function handleRestoreAction() {
    setRestoreConfirmVisible(true);
  }

  function handleSetRecommendedVersionAction() {
    setSetAsRecommendedConfirmVisible(true);
  }

  function handleSetRecommendedVersionSuccess() {
    setSetAsRecommendedConfirmVisible(false);
    loadProductDetails();
  }

  return <>
    <PromoteVersionPrompt
      projectId={selectedProject.projectId}
      productId={id}
      selectedVersion={selectedVersion}
      promoteConfirmVisible={promoteConfirmVisible}
      setPromoteConfirmVisible={setPromoteConfirmVisible}
      loadProductDetails={loadProductDetails}
    />
    <ArchiveProductPrompt
      projectId={product.projectId}
      productId={product.productId}
      selectedProduct={product}
      archiveConfirmVisible={archiveConfirmVisible}
      setArchiveConfirmVisible={setArchiveConfirmVisible}
      loadProductDetails={loadProductDetails}
    />
    <RetireVersionPrompt
      projectId={selectedProject.projectId!}
      productId={id!}
      selectedVersion={selectedVersion!}
      retireConfirmVisible={retireConfirmVisible}
      setRetireConfirmVisible={setRetireConfirmVisible}
      loadProducts={loadProductDetails}
    />
    <RestoreVersionPrompt
      projectId={selectedProject.projectId!}
      productId={id!}
      selectedVersion={selectedVersion!}
      restoreConfirmVisible={restoreConfirmVisible}
      setRestoreConfirmVisible={setRestoreConfirmVisible}
      loadProducts={loadProductDetails}
    />
    <SetAsRecommendedPrompt
      projectId={selectedProject.projectId!}
      productId={id!}
      selectedVersion={selectedVersion!}
      promptVisible={setAsRecommendedConfirmVisible}
      setPromptVisible={setSetAsRecommendedConfirmVisible}
      successCallback={handleSetRecommendedVersionSuccess}
    />
    <WorkbenchAppLayout
      breadcrumbItems={breadCrumbsMemo}
      content={
        <SpaceBetween direction='vertical' size='l'>
          <ProductOverviewDetails prod={product} />
          <ProductVersions
            productId={product?.productId}
            versions={product?.versions}
            setSelectedVersion={setSelectedVersion}
            isLoading={isLoading}
            loadVersions={loadProductDetails}
            viewVersionDetails={(versionId: string) => navigateToVersionDetails(product.productId, versionId)}
            updateVersionDetails={navigateToUpdateProductVersion}
            promoteVersion={handlePromoteAction}
            emptyVersionResolveAction={navigateToCreateProductVersion}
            retireVersion={handleRetireAction}
            isProductArchived={isProductArchived}
            restoreVersion={handleRestoreAction}
            setRecommendedVersion={handleSetRecommendedVersionAction}
          />
        </SpaceBetween>
      }
      contentType="default"
      customHeader={
        <ProductOverviewHeader
          title={product?.productName}
          description={product?.productDescription}
          productStatus={product.status}
          archiveProduct={handleArchiveAction}
          createVersion={navigateToCreateProductVersion}
          goBack={goBack}
          loadProductDetails={loadProductDetails}
          isProductArchived={isProductArchived}
        />
      }
      tools={renderTools()}
    />
  </>;

  function renderTools() {
    return (
      <HelpPanel header={<h2>{i18n.infoPanelHeader}</h2>}>
        <SpaceBetween size={'s'}>
          <Box variant="awsui-key-label">{i18n.infoPanelLabel1}</Box>
          <Box variant="p">{i18n.infoPanelMessage1}</Box>
          <Box>
            <p>{i18n.infoPanelMessage2}</p>
            <ul>
              <li><b>{i18n.infoPanelPoint1}</b><br />{i18n.infoPanelPoint1Message}</li>
              <li><b>{i18n.infoPanelPoint2}</b></li>
              <li><b>{i18n.infoPanelPoint3}</b><br />{i18n.infoPanelPoint3Message}</li>
              <ul style={{ listStyle: 'disc' }}>
                <li>{i18n.infoPanelPoint3Subpoint1}</li>
                <li>{i18n.infoPanelPoint3Subpoint2}</li>
                <li>{i18n.infoPanelPoint3Subpoint3}</li>
              </ul>
              <li><b>{i18n.infoPanelPoint4}</b><br />{i18n.infoPanelPoint4Message}</li>
              <li><b>{i18n.infoPanelPoint5}</b><br />{i18n.infoPanelPoint5Message}</li>
              <li><b>{i18n.infoPanelPoint6}</b><br />{i18n.infoPanelPoint6Message}</li>
            </ul>
          </Box>
        </SpaceBetween>
      </HelpPanel>
    );
  }
};
