// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
//
// Marketplace public-catalog browse page.
//
// Renders a filterable, paginated tile grid of AMI listings from the
// AWS Marketplace public catalog. Selecting a listing navigates to the
// listing-detail slide-over, which hands off to the procurement wizard
// via `initialOfferId`.

import { FC, useEffect, useMemo, useRef, useState } from 'react';
import {
  Badge,
  Box,
  Button,
  Cards,
  CardsProps,
  Checkbox,
  ExpandableSection,
  Header,
  Input,
  Link,
  SpaceBetween,
  Spinner,
  StatusIndicator,
} from '@cloudscape-design/components';
import { useNavigate } from 'react-router-dom';
import { WorkbenchAppLayout } from '../../../layout/workbench-app-layout/workbench-app-layout';
import { BreadcrumbItem } from '../../../layout';
import { EmptyGridNotification } from '../../shared';
import { useNavigationPaths } from '../../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../../layout/navigation/navigation.static';
import {
  GetMarketplaceFacetsResponse,
  MarketplaceFacetValue,
  MarketplaceListingSummary,
  SearchListingsParams,
  facetValuesOf,
  marketplaceListingsAPI,
} from '../../../../services/API/marketplace-listings-api';
import { useSearchMarketplaceListings } from
  '../../../../hooks/packaging/use-search-marketplace-listings.logic';
import { useMarketplaceFacets } from
  '../../../../hooks/packaging/use-marketplace-facets.logic';
import { i18n } from './browse-marketplace.translations';

const PAGE_SIZE = 25;
const FACET_INITIAL_LIMIT = 8;
const FIRST_ITEM_INDEX = 0;
const EMPTY = 0;
// Responsive card grid: 1 card below 500px, 2 up to 900px, 3 above.
const CARDS_SINGLE_COLUMN = 1;
const CARDS_TWO_COLUMN = 2;
const CARDS_THREE_COLUMN = 3;
const BREAKPOINT_TWO_COLUMN = 500;
const BREAKPOINT_THREE_COLUMN = 900;

// Mapping between backend facet keys and translation strings.
const FACET_HEADERS: Record<string, string> = {
  CATEGORY: i18n.facetCategoryHeader,
  PRICING_MODEL: i18n.facetPricingModelHeader,
  PUBLISHER: i18n.facetPublisherHeader,
  AVERAGE_CUSTOMER_RATING: i18n.facetRatingHeader,
};

// Which facets we render in the sidebar (order matters for UX).
const SIDEBAR_FACETS = [
  'CATEGORY',
  'PRICING_MODEL',
  'PUBLISHER',
  'AVERAGE_CUSTOMER_RATING',
];

interface FacetState {
  category: Set<string>,
  pricingModel: Set<string>,
  publisher: Set<string>,
  rating: Set<string>,
}

const emptyFacetState = (): FacetState => ({
  category: new Set(),
  pricingModel: new Set(),
  publisher: new Set(),
  rating: new Set(),
});

const facetKeyToState = (facetKey: string): keyof FacetState | null => {
  switch (facetKey) {
    case 'CATEGORY': return 'category';
    case 'PRICING_MODEL': return 'pricingModel';
    case 'PUBLISHER': return 'publisher';
    case 'AVERAGE_CUSTOMER_RATING': return 'rating';
    default: return null;
  }
};


interface FacetGroupProps {
  facetKey: string,
  values: MarketplaceFacetValue[],
  selected: Set<string>,
  onToggle: (value: string) => void,
}

const FacetGroup: FC<FacetGroupProps> = ({ facetKey, values, selected, onToggle }) => {
  const [expanded, setExpanded] = useState(false);
  const header = FACET_HEADERS[facetKey] || facetKey;
  const visible = expanded ? values : values.slice(FIRST_ITEM_INDEX, FACET_INITIAL_LIMIT);
  const hasMore = values.length > FACET_INITIAL_LIMIT;

  if (values.length === EMPTY) { return null; }

  return (
    <ExpandableSection headerText={`${header} (${values.length})`} defaultExpanded>
      <SpaceBetween direction="vertical" size="xs">
        {visible.map((v) =>
          <Checkbox
            key={v.value}
            checked={selected.has(v.value)}
            onChange={() => onToggle(v.value)}
          >
            {v.displayName}
            {' '}
            <Box display="inline" color="text-body-secondary" fontSize="body-s">
              (
              {v.count.toLocaleString()}
              )
            </Box>
          </Checkbox>
        )}
        {hasMore &&
          <Link onFollow={(e) => { e.preventDefault(); setExpanded(!expanded); }} href="#">
            {expanded ? i18n.facetShowLess : i18n.facetShowMore}
          </Link>
        }
      </SpaceBetween>
    </ExpandableSection>
  );
};

type PricingBadge = { text: string, color: 'blue' | 'green' | 'grey' };

const pricingBadge = (listing: MarketplaceListingSummary): PricingBadge | null => {
  const models = listing.pricingModels || [];
  if (models.some((m) => m.pricingModelType === 'FREE')) {
    return { text: i18n.tileFreeBadge, color: 'green' };
  }
  if (models.some((m) => m.pricingModelType === 'USAGE')) {
    return { text: i18n.tileUsageBadge, color: 'blue' };
  }
  if (models.some((m) => m.pricingModelType === 'CONTRACT')) {
    return { text: i18n.tileContractBadge, color: 'blue' };
  }
  if (models.some((m) => m.pricingModelType === 'BYOL')) {
    return { text: i18n.tileBYOLBadge, color: 'grey' };
  }
  return null;
};

interface FacetSidebarProps {
  facetsLoading: boolean,
  facetSet: GetMarketplaceFacetsResponse | null | undefined,
  facets: FacetState,
  onToggleFacet: (stateKey: keyof FacetState, value: string) => void,
}

/**
 * The facet sidebar: a spinner while facets load, then one FacetGroup per
 * configured facet. Extracted from the browse component to keep it under the
 * repo's complexity limit.
 */
const FacetSidebar: FC<FacetSidebarProps> = ({
  facetsLoading,
  facetSet,
  facets,
  onToggleFacet,
}) => {
  if (facetsLoading) {
    return (
      <Box padding="s">
        <Spinner />
        {' '}
        {i18n.facetLoading}
      </Box>
    );
  }
  if (!facetSet) { return null; }
  return (
    <SpaceBetween direction="vertical" size="s">
      {SIDEBAR_FACETS.map((facetKey) => {
        const stateKey = facetKeyToState(facetKey);
        if (!stateKey) { return null; }
        return (
          <FacetGroup
            key={facetKey}
            facetKey={facetKey}
            values={facetValuesOf(facetSet, facetKey)}
            selected={facets[stateKey]}
            onToggle={(v) => onToggleFacet(stateKey, v)}
          />
        );
      })}
    </SpaceBetween>
  );
};

/**
 * Should a freshly-arrived page be folded into the accumulator?
 *
 * A page is identified by (filterKey, pageToken, first-listing-id). If any of
 * the three differs from what was last appended, it is a new page. If all
 * three match, it is the same page re-delivered by an SWR revalidation and
 * must be skipped, or rows would duplicate.
 *
 * Extracted from the append effect so the browse component stays under the
 * repo's complexity limit; the guard sequence is unchanged.
 */
const shouldAppendPage = ({
  isLoading,
  pageCount,
  filterKey,
  currentFilterKey,
  lastAppendedFilterKey,
  pageToken,
  lastAppendedToken,
  firstId,
  lastAppendedFirstId,
}: {
  isLoading: boolean,
  pageCount: number,
  filterKey: string,
  currentFilterKey: string | null,
  lastAppendedFilterKey: string | null,
  pageToken: string | undefined,
  lastAppendedToken: string | null | undefined,
  firstId: string | null | undefined,
  lastAppendedFirstId: string | null,
}): boolean => {
  if (isLoading || pageCount === EMPTY) { return false; }
  // The in-flight page belongs to a previous filter; wait for the reset.
  if (currentFilterKey !== filterKey) { return false; }
  const alreadyAppended = lastAppendedFilterKey === filterKey
    && lastAppendedToken === pageToken
    && lastAppendedFirstId === firstId;
  return !alreadyAppended;
};

const FIRST_REVIEW_INDEX = 0;

/**
 * Pricing badge + star rating for a listing card.
 *
 * Extracted from the cardDefinition sections, whose inline branching
 * (optional review chains, conditional badge/rating) pushed the browse
 * component over the repo's complexity limit.
 */
const ListingBadges: FC<{ listing: MarketplaceListingSummary }> = ({ listing }) => {
  const badge = pricingBadge(listing);
  const review = listing.reviewSummary?.[FIRST_REVIEW_INDEX];
  const rating = review?.averageRating;
  const totalReviews = review?.totalReviews;
  return (
    <SpaceBetween direction="horizontal" size="xs">
      {badge && <Badge color={badge.color}>{badge.text}</Badge>}
      {rating &&
        <StatusIndicator type="info">
          ★
          {' '}
          {rating}
          {totalReviews && ` (${totalReviews})`}
        </StatusIndicator>
      }
    </SpaceBetween>
  );
};


interface ServiceAPI {
  searchListings: typeof marketplaceListingsAPI.searchListings,
  getFacets: typeof marketplaceListingsAPI.getFacets,
}

export const BrowseMarketplace: FC<{ serviceApi?: ServiceAPI }> = ({
  serviceApi = marketplaceListingsAPI,
}) => {
  const navigate = useNavigate();
  const { getPathFor } = useNavigationPaths();

  const [searchText, setSearchText] = useState('');
  const [appliedSearchText, setAppliedSearchText] = useState('');
  const [facets, setFacets] = useState<FacetState>(emptyFacetState());
  const [pageToken, setPageToken] = useState<string | undefined>(undefined);
  const [accumulatedListings, setAccumulatedListings] = useState<MarketplaceListingSummary[]>([]);

  // The "filter key" captures every input that scopes the current search.
  // When it changes, the accumulator must be reset before the next page
  // arrives — otherwise stale listings from the previous filter would
  // linger (SWR's `keepPreviousData: true` briefly returns the old page
  // while the new one is in-flight; without a reset the accumulator
  // would append the new page onto stale rows and pagination via
  // `nextToken` would then be wrong).
  const filterKey = useMemo(
    () => JSON.stringify({
      appliedSearchText,
      category: Array.from(facets.category).sort(),
      pricingModel: Array.from(facets.pricingModel).sort(),
      publisher: Array.from(facets.publisher).sort(),
      rating: Array.from(facets.rating).sort(),
    }),
    [appliedSearchText, facets],
  );

  const searchParams: SearchListingsParams = useMemo(() => ({
    searchText: appliedSearchText || undefined,
    category: Array.from(facets.category),
    pricingModel: Array.from(facets.pricingModel),
    publisher: Array.from(facets.publisher),
    rating: Array.from(facets.rating),
    nextToken: pageToken,
    maxResults: PAGE_SIZE,
  }), [appliedSearchText, facets, pageToken]);

  const { data: pageListings, nextToken, totalResults, isLoading, error, run } =
    useSearchMarketplaceListings({ serviceApi, params: searchParams });

  const { data: facetSet, isLoading: facetsLoading } =
    useMarketplaceFacets({ serviceApi });

  // --- Pagination state machine (useEffect-driven, race-free) ---
  //
  // Two effects, tied to two refs so they don't fire on unrelated re-renders:
  //
  // 1. Reset effect. When `filterKey` changes, drop the accumulator and the
  //    page token. Fires synchronously with the filter change; the next
  //    render will trigger a fresh SWR request for page 0 of the new filter.
  //
  // 2. Append effect. When a page arrives (pageListings changes) AND we are
  //    NOT currently loading AND the page belongs to the current filterKey,
  //    append it to the accumulator. The isLoading guard is what makes this
  //    race-free: SWR's `keepPreviousData: true` briefly returns the old
  //    filter's page while the new one is fetching, but `isLoading` is
  //    `true` during that transition — so we skip the append and wait for
  //    the real new-filter page.

  const lastFilterKeyRef = useRef(filterKey);
  const lastAppendedFilterKeyRef = useRef<string | null>(null);
  const lastAppendedTokenRef = useRef<string | null | undefined>(undefined);
  const lastAppendedFirstIdRef = useRef<string | null>(null);

  // Reset effect: filter changed.
  useEffect(() => {
    if (lastFilterKeyRef.current !== filterKey) {
      lastFilterKeyRef.current = filterKey;
      setAccumulatedListings([]);
      setPageToken(undefined);
      lastAppendedFilterKeyRef.current = null;
      lastAppendedTokenRef.current = undefined;
      lastAppendedFirstIdRef.current = null;
    }
  }, [filterKey]);

  // Append effect: a fresh, filter-aligned, non-loading page arrived.
  useEffect(() => {
    const firstId = pageListings[FIRST_ITEM_INDEX]?.listingId ?? null;
    if (!shouldAppendPage({
      isLoading,
      pageCount: pageListings.length,
      filterKey,
      currentFilterKey: lastFilterKeyRef.current,
      lastAppendedFilterKey: lastAppendedFilterKeyRef.current,
      pageToken,
      lastAppendedToken: lastAppendedTokenRef.current,
      firstId,
      lastAppendedFirstId: lastAppendedFirstIdRef.current,
    })) { return; }

    setAccumulatedListings((prev) => {
      const seen = new Set(prev.map((l) => l.listingId));
      const additions = pageListings.filter((l) => !seen.has(l.listingId));
      return prev.concat(additions);
    });
    lastAppendedFilterKeyRef.current = filterKey;
    lastAppendedTokenRef.current = pageToken;
    lastAppendedFirstIdRef.current = firstId;
  }, [pageListings, isLoading, filterKey, pageToken]);

  const onSubmitSearch = () => {
    setAppliedSearchText(searchText.trim());
  };

  const onToggleFacet = (facetStateKey: keyof FacetState, value: string) => {
    setFacets((prev) => {
      const nextSet = new Set(prev[facetStateKey]);
      if (nextSet.has(value)) { nextSet.delete(value); } else { nextSet.add(value); }
      return { ...prev, [facetStateKey]: nextSet };
    });
  };

  const clearFilters = () => {
    setFacets(emptyFacetState());
    setSearchText('');
    setAppliedSearchText('');
  };

  const loadMore = () => {
    if (nextToken) { setPageToken(nextToken); }
  };

  const goToListing = (listing: MarketplaceListingSummary) => {
    // Absolute path via the route registry — a relative `navigate(...)` from
    // the browse page (`/projects/:id/marketplace/browse`) would resolve to
    // `/projects/:id/marketplace/browse/marketplace/listings/:listingId`
    // and 404.
    const detailPath = getPathFor(RouteNames.MarketplaceListingDetail)
      .replace(':listingId', encodeURIComponent(listing.listingId));
    navigate(detailPath);
  };

  const hasActiveFilters =
    facets.category.size > EMPTY
    || facets.pricingModel.size > EMPTY
    || facets.publisher.size > EMPTY
    || facets.rating.size > EMPTY
    || !!appliedSearchText;

  const cardDefinition: CardsProps.CardDefinition<MarketplaceListingSummary> = {
    header: (item) =>
      <Link
        onFollow={(e) => { e.preventDefault(); goToListing(item); }}
        href="#"
        fontSize="heading-m"
      >
        {item.listingName}
      </Link>
    ,
    sections: [
      {
        id: 'publisher',
        content: (item) =>
          <Box color="text-body-secondary" fontSize="body-s">
            {i18n.tilePublisherLabel}
            {' '}
            {item.publisher.displayName}
          </Box>
        ,
      },
      {
        id: 'description',
        content: (item) =>
          <Box variant="p">
            {item.shortDescription || i18n.tileNoDescription}
          </Box>
        ,
      },
      {
        id: 'badges',
        content: (item) => <ListingBadges listing={item} />,
      },
      {
        id: 'actions',
        content: (item) =>
          <Button onClick={() => goToListing(item)}>
            {i18n.tileViewButton}
          </Button>
        ,
      },
    ],
  };

  const breadcrumbItems: BreadcrumbItem[] = [
    { path: i18n.breadcrumbMarketplace, href: '#' },
    { path: i18n.breadcrumbBrowse, href: '#' },
  ];

  const displayListings = accumulatedListings.length > EMPTY
    ? accumulatedListings
    : pageListings;

  return (
    <WorkbenchAppLayout
      breadcrumbItems={breadcrumbItems}
      contentType="default"
      content={
        <SpaceBetween direction="vertical" size="l">
          <Header
            variant="h1"
            description={i18n.description}
          >
            {i18n.header}
          </Header>

          {/* Search bar */}
          <SpaceBetween direction="horizontal" size="xs">
            <Box>
              <Input
                type="search"
                value={searchText}
                onChange={({ detail }) => setSearchText(detail.value)}
                onKeyDown={({ detail }) => {
                  if (detail.key === 'Enter') { onSubmitSearch(); }
                }}
                placeholder={i18n.searchPlaceholder}
                data-test="marketplace-search-input"
              />
            </Box>
            <Button variant="primary" onClick={onSubmitSearch} data-test="marketplace-search-submit">
              {i18n.searchButton}
            </Button>
            {hasActiveFilters &&
              <Button onClick={clearFilters} iconName="close">
                {i18n.clearFiltersButton}
              </Button>
            }
          </SpaceBetween>

          {/* Layout: sidebar + grid. Using Box with grid CSS for a two-column layout. */}
          <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: '24px' }}>
            {/* Facet sidebar */}
            <aside>
              <Header variant="h2">{i18n.facetSidebarHeader}</Header>
              <FacetSidebar
                facetsLoading={facetsLoading}
                facetSet={facetSet}
                facets={facets}
                onToggleFacet={onToggleFacet}
              />
            </aside>

            {/* Tile grid */}
            <section>
              {error &&
                <EmptyGridNotification
                  title={i18n.errorTitle}
                  subTitle={error.message}
                  actionButtonText={i18n.errorRetry}
                  actionButtonOnClick={() => run()}
                />
              }
              {!error &&
                <>
                  <Box padding={{ bottom: 'xs' }} color="text-body-secondary">
                    {i18n.resultsCount(displayListings.length, totalResults)}
                  </Box>
                  <Cards
                    cardDefinition={cardDefinition}
                    items={displayListings}
                    loading={isLoading && displayListings.length === EMPTY}
                    loadingText="Loading listings…"
                    cardsPerRow={[
                      { cards: CARDS_SINGLE_COLUMN },
                      { minWidth: BREAKPOINT_TWO_COLUMN, cards: CARDS_TWO_COLUMN },
                      { minWidth: BREAKPOINT_THREE_COLUMN, cards: CARDS_THREE_COLUMN },
                    ]}
                    trackBy={(item) => item.listingId}
                    empty={
                      <EmptyGridNotification
                        title={i18n.emptyTitle}
                        subTitle={i18n.emptySubtitle}
                        actionButtonText={i18n.emptyExternalButton}
                        actionButtonOnClick={() => window.open(
                          i18n.emptyExternalUrl,
                          '_blank',
                          'noopener,noreferrer',
                        )}
                      />
                    }
                  />
                  {nextToken &&
                    <Box padding={{ top: 's' }} textAlign="center">
                      <Button onClick={loadMore} loading={isLoading}>
                        {i18n.loadMoreButton}
                      </Button>
                    </Box>
                  }
                </>
              }
            </section>
          </div>
        </SpaceBetween>
      }
    />
  );
};

export default BrowseMarketplace;
