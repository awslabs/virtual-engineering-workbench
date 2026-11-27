// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
//
// Marketplace public-catalog listing detail page.
//
// Renders full detail for a single listing (long description, highlights,
// resources, associated products), plus a "Get this product" CTA that
// opens the procurement wizard at the listing's primary offer via
// ?offerId=<id>.

import { FC, ReactNode } from 'react';
import {
  Alert,
  Badge,
  Box,
  Button,
  ColumnLayout,
  Container,
  Header,
  Link,
  SpaceBetween,
  Spinner,
  StatusIndicator,
} from '@cloudscape-design/components';
import { NavigateFunction, useNavigate, useParams } from 'react-router-dom';
import { useRecoilValue } from 'recoil';
import { WorkbenchAppLayout } from '../../../layout/workbench-app-layout/workbench-app-layout';
import { BreadcrumbItem } from '../../../layout';
import { EmptyGridNotification } from '../../shared';
import { useNavigationPaths } from '../../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../../layout/navigation/navigation.static';
import { RoleBasedFeature, selectedProjectState } from '../../../../state';
import { useRoleAccessToggle } from '../../../../hooks/role-access-toggle';
import { SafeHtml } from './safe-html';
import { getListingCtaLabel } from './procurement-wizard/offer-helpers';
import {
  marketplaceListingsAPI,
  GetMarketplaceListingResponse,
} from '../../../../services/API/marketplace-listings-api';
import { useGetMarketplaceListing } from
  '../../../../hooks/packaging/use-get-marketplace-listing.logic';
import { i18n } from './listing-detail.translations';
import { safeExternalUrl } from './safe-external-url';

const MARKETPLACE_LISTING_URL = (listingId: string) =>
  `https://aws.amazon.com/marketplace/pp/${encodeURIComponent(listingId)}`;

// Empty-array sentinel for `.length > EMPTY_LIST` idioms; named to satisfy
// `no-magic-numbers` without sprinkling per-line disables.
const EMPTY_LIST = 0;

interface ServiceAPI {
  getListing: typeof marketplaceListingsAPI.getListing,
}

interface Props {
  serviceApi?: ServiceAPI,
  // Optional prop override for tests. When absent, uses the URL param.
  listingIdOverride?: string,
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const pricingBadges = (listing: GetMarketplaceListingResponse) => {
  const models = listing.pricingModels || [];
  return models.map((m) => {
    let color: 'green' | 'blue' | 'grey' = 'blue';
    if (m.pricingModelType === 'FREE') { color = 'green'; }
    if (m.pricingModelType === 'BYOL') { color = 'grey'; }
    return (
      <Badge key={m.pricingModelType} color={color}>
        {m.displayName || m.pricingModelType}
      </Badge>
    );
  });
};

// Every listing, whoever sells it, routes to the procurement wizard. The
// wizard reads the offer's terms and, for an offer with no pricing term,
// offers a direct import instead of the subscription steps. The CTA
// therefore only needs an offer.
const hasPurchasableOffer = (listing: GetMarketplaceListingResponse): boolean =>
  !!listing.primaryOfferId;

// The listing id travels with the offer id because the direct-import path
// needs it: resolving the AMI starts from the listing, not from the offer.
const navigateToGetProduct = (
  listing: GetMarketplaceListingResponse,
  navigate: NavigateFunction,
  getPathFor: (route: RouteNames) => string,
): void => {
  if (!listing.primaryOfferId) { return; }
  const wizardPath = getPathFor(RouteNames.MarketplaceProcurementWizard);
  const search = new URLSearchParams({
    offerId: listing.primaryOfferId,
    listingId: listing.listingId,
  });
  navigate(`${wizardPath}?${search.toString()}`);
};

const NOT_AVAILABLE = '—';
const PRODUCT_DETAILS_COLUMNS = 2;

/** Display names joined with commas, or a dash when there are none. */
const joinDisplayNames = (items?: ReadonlyArray<{ displayName?: string }>): string =>
  (items || []).map((item) => item.displayName).join(', ') || NOT_AVAILABLE;

// ---------------------------------------------------------------------------
// Presentation sub-components (kept in-file: they're only used here)
// ---------------------------------------------------------------------------

interface LayoutShellProps {
  breadcrumbItems: BreadcrumbItem[],
  children: ReactNode,
}

// Common WorkbenchAppLayout shell reused by loading / error / not-found
// screens. Hoisted out to keep the top-level render function short.
const LayoutShell: FC<LayoutShellProps> = ({ breadcrumbItems, children }) =>
  <WorkbenchAppLayout
    breadcrumbItems={breadcrumbItems}
    contentType="default"
    content={children}
  />
;

const LoadingView: FC<{ breadcrumbItems: BreadcrumbItem[] }> = ({ breadcrumbItems }) =>
  <LayoutShell breadcrumbItems={breadcrumbItems}>
    <Box padding="l" textAlign="center">
      <Spinner size="large" />
      {' '}
      {i18n.loadingText}
    </Box>
  </LayoutShell>
;

interface ErrorViewProps {
  breadcrumbItems: BreadcrumbItem[],
  message: string,
  onRetry: () => void,
}

const ErrorView: FC<ErrorViewProps> = ({ breadcrumbItems, message, onRetry }) =>
  <LayoutShell breadcrumbItems={breadcrumbItems}>
    <EmptyGridNotification
      title={i18n.errorTitle}
      subTitle={message}
      actionButtonText={i18n.errorRetry}
      actionButtonOnClick={onRetry}
    />
  </LayoutShell>
;

const NotFoundView: FC<{
  breadcrumbItems: BreadcrumbItem[],
  onBack: () => void,
}> = ({ breadcrumbItems, onBack }) =>
  <LayoutShell breadcrumbItems={breadcrumbItems}>
    <EmptyGridNotification
      title={i18n.notFoundTitle}
      subTitle={i18n.notFoundSubtitle}
      actionButtonText={i18n.backToBrowseButton}
      actionButtonOnClick={onBack}
    />
  </LayoutShell>
;


const KeyValue: FC<{ label: string, children: ReactNode }> = ({ label, children }) =>
  <div>
    <Box variant="awsui-key-label">{label}</Box>
    <div>{children}</div>
  </div>
;

const ListingHeader: FC<{
  listing: GetMarketplaceListingResponse,
  canPurchase: boolean,
  ctaLabel: string,
  onBack: () => void,
  onGetProduct: () => void,
}> = ({ listing, canPurchase, ctaLabel, onBack, onGetProduct }) =>
  <Header
    variant="h1"
    description={
      <SpaceBetween direction="horizontal" size="xs">
        <Box color="text-body-secondary">
          By
          {' '}
          {listing.publisher.displayName}
        </Box>
        {pricingBadges(listing)}
      </SpaceBetween>
    }
    actions={
      <SpaceBetween direction="horizontal" size="xs">
        <Button onClick={onBack} iconName="arrow-left">
          {i18n.backToBrowseButton}
        </Button>
        <Button
          variant="normal"
          iconName="external"
          iconAlign="right"
          href={MARKETPLACE_LISTING_URL(listing.listingId)}
          target="_blank"
          data-test="listing-detail-external"
        >
          {i18n.openOnMarketplaceButton}
        </Button>
        <Button
          variant="primary"
          onClick={onGetProduct}
          disabled={!canPurchase}
          data-test="listing-detail-get-product"
        >
          {ctaLabel}
        </Button>
      </SpaceBetween>
    }
  >
    {listing.listingName}
  </Header>
;

const OverviewSection: FC<{ listing: GetMarketplaceListingResponse }> = ({ listing }) =>
  <Container header={<Header variant="h2">{i18n.overviewHeader}</Header>}>
    {listing.shortDescription &&
      <Box variant="p" padding={{ bottom: 's' }}>
        <strong>{listing.shortDescription}</strong>
      </Box>
    }
    {listing.longDescription &&
      // AWS Marketplace ships LongDescription as sanitizable HTML
      // (headings, paragraphs, lists, links, basic emphasis).
      // Render via SafeHtml — see safe-html.tsx.
      <SafeHtml
        html={listing.longDescription}
        data-test="listing-detail-long-description"
      />
    }
  </Container>
;

/** Seller-authored inline HTML entries (e.g. <strong>), one list item each. */
const HtmlList: FC<{ items: string[], testPrefix: string }> = ({ items, testPrefix }) =>
  <ul>
    {items.map((item, i) =>
      <li key={`${testPrefix}-${i}`}>
        <SafeHtml
          html={item}
          style={{ display: 'inline' }}
          data-test={`listing-detail-${testPrefix}-${i}`}
        />
      </li>
    )}
  </ul>
;

const HighlightsSection: FC<{ highlights?: string[] }> = ({ highlights }) =>
  <Container header={<Header variant="h2">{i18n.highlightsHeader}</Header>}>
    {highlights && highlights.length > EMPTY_LIST
      ? <HtmlList items={highlights} testPrefix="highlight" />
      : <Box color="text-body-secondary">{i18n.noHighlights}</Box>
    }
  </Container>
;

const UseCasesSection: FC<{ useCases?: string[] }> = ({ useCases }) => {
  if (!useCases || useCases.length === EMPTY_LIST) { return null; }
  return (
    <Container header={<Header variant="h2">{i18n.useCasesHeader}</Header>}>
      <HtmlList items={useCases} testPrefix="usecase" />
    </Container>
  );
};

const ProductDetailsSection: FC<{ listing: GetMarketplaceListingResponse }> = ({ listing }) => {
  const primaryProduct = listing.associatedEntities?.[0];
  return (
    <Container header={<Header variant="h2">{i18n.productDetailsHeader}</Header>}>
      <ColumnLayout columns={PRODUCT_DETAILS_COLUMNS} variant="text-grid">
        <KeyValue label={i18n.publisherLabel}>{listing.publisher.displayName}</KeyValue>
        <KeyValue label={i18n.fulfillmentLabel}>
          {joinDisplayNames(listing.fulfillmentOptionSummaries)}
        </KeyValue>
        <KeyValue label={i18n.pricingModelLabel}>{joinDisplayNames(listing.pricingModels)}</KeyValue>
        <KeyValue label={i18n.categoriesLabel}>{joinDisplayNames(listing.categories)}</KeyValue>
        {primaryProduct &&
          <KeyValue label={i18n.productIdLabel}>
            <code data-test="listing-detail-product-id">{primaryProduct.productId}</code>
          </KeyValue>
        }
        {primaryProduct && listing.primaryOfferId &&
          <KeyValue label={i18n.offerIdLabel}>
            <code data-test="listing-detail-offer-id">{listing.primaryOfferId}</code>
          </KeyValue>
        }
        <KeyValue label={i18n.listingIdLabel}><code>{listing.listingId}</code></KeyValue>
      </ColumnLayout>
    </Container>
  );
};

type ListingResource = NonNullable<GetMarketplaceListingResponse['resources']>[number];

/**
 * `resource.value` is seller-authored. Only render it as a link if it passes
 * the scheme allowlist; a rejected value still shows as text so the user can
 * see what the seller supplied rather than the row silently vanishing.
 */
const ResourceItem: FC<{ resource: ListingResource }> = ({ resource }) => {
  const href = resource.contentType === 'LINK' ? safeExternalUrl(resource.value) : null;
  if (href) {
    return <Link href={href} external>{resource.displayName || resource.value}</Link>;
  }
  return <span>{resource.displayName || resource.value || resource.resourceType}</span>;
};

const ResourcesSection: FC<{ resources?: ListingResource[] }> = ({ resources }) =>
  <Container header={<Header variant="h2">{i18n.resourcesHeader}</Header>}>
    {resources && resources.length > EMPTY_LIST
      ?
      <ul>
        {resources.map((r, i) =>
          <li key={`resource-${i}`}><ResourceItem resource={r} /></li>
        )}
      </ul>
      : <Box color="text-body-secondary">{i18n.noResources}</Box>
    }
  </Container>
;

const ActionsSection: FC<{
  canPurchase: boolean,
  ctaLabel: string,
  projectId?: string,
  onGetProduct: () => void,
}> = ({ canPurchase, ctaLabel, projectId, onGetProduct }) =>
  <Container header={<Header variant="h2">{i18n.actionsHeader}</Header>}>
    <SpaceBetween direction="vertical" size="s">
      <Box variant="p">{i18n.getProductNote}</Box>
      <Button
        variant="primary"
        onClick={onGetProduct}
        disabled={!canPurchase}
        data-test="listing-detail-get-product-footer"
      >
        {ctaLabel}
      </Button>
      {!canPurchase &&
        <StatusIndicator type="warning">
          {i18n.getProductDisabled}
        </StatusIndicator>
      }
      <Box color="text-body-secondary" fontSize="body-s">
        Buyer account:
        {' '}
        {projectId}
      </Box>
    </SpaceBetween>
  </Container>
;

const LoadedView: FC<{
  listing: GetMarketplaceListingResponse,
  breadcrumbItems: BreadcrumbItem[],
  projectId?: string,
  onBack: () => void,
  onGetProduct: () => void,
  canProcure: boolean,
}> = ({ listing, breadcrumbItems, projectId, onBack, onGetProduct, canProcure }) => {
  // The offer and quote APIs allow project admins only, so the CTA is hidden for other roles.
  const canPurchase = canProcure && hasPurchasableOffer(listing);
  const ctaLabel = getListingCtaLabel(
    (listing.pricingModels || []).map((p) => p.pricingModelType),
  );
  return (
    <LayoutShell breadcrumbItems={breadcrumbItems}>
      <SpaceBetween direction="vertical" size="l">
        <ListingHeader
          listing={listing}
          canPurchase={canPurchase}
          ctaLabel={ctaLabel}
          onBack={onBack}
          onGetProduct={onGetProduct}
        />
        {!canPurchase &&
          <Alert type="warning" data-test="listing-detail-no-offer">
            {i18n.getProductDisabled}
          </Alert>
        }
        <OverviewSection listing={listing} />
        <HighlightsSection highlights={listing.highlights} />
        <UseCasesSection useCases={listing.useCases} />
        <ProductDetailsSection listing={listing} />
        <ResourcesSection resources={listing.resources} />
        <ActionsSection
          canPurchase={canPurchase}
          ctaLabel={ctaLabel}
          projectId={projectId}
          onGetProduct={onGetProduct}
        />
      </SpaceBetween>
    </LayoutShell>
  );
};

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export const ListingDetail: FC<Props> = ({
  serviceApi = marketplaceListingsAPI,
  listingIdOverride,
}) => {
  const params = useParams<{ listingId?: string }>();
  const listingId = listingIdOverride ?? params.listingId ?? null;
  const navigate = useNavigate();
  const { getPathFor } = useNavigationPaths();
  const selectedProject = useRecoilValue(selectedProjectState);
  const isFeatureAccessible = useRoleAccessToggle();

  const { data: listing, isLoading, error, run } = useGetMarketplaceListing({
    serviceApi,
    listingId,
  });

  const breadcrumbItems: BreadcrumbItem[] = [
    { path: i18n.breadcrumbMarketplace, href: '#' },
    {
      path: i18n.breadcrumbBrowse,
      href: getPathFor(RouteNames.MarketplaceBrowse),
    },
    { path: listing?.listingName || listingId || '...', href: '#' },
  ];

  const goBack = () => {
    navigate(getPathFor(RouteNames.MarketplaceBrowse));
  };

  if (isLoading && !listing) {
    return <LoadingView breadcrumbItems={breadcrumbItems} />;
  }
  if (error && !listing) {
    return (
      <ErrorView
        breadcrumbItems={breadcrumbItems}
        message={error.message}
        onRetry={run}
      />
    );
  }
  if (!listing) {
    return <NotFoundView breadcrumbItems={breadcrumbItems} onBack={goBack} />;
  }

  return (
    <LoadedView
      listing={listing}
      breadcrumbItems={breadcrumbItems}
      projectId={selectedProject.projectId}
      onBack={goBack}
      onGetProduct={() => navigateToGetProduct(listing, navigate, getPathFor)}
      canProcure={isFeatureAccessible(RoleBasedFeature.ManagePlatform)}
    />
  );
};

export default ListingDetail;
