const SINGLE_RESULT = 1;

export const i18n = {
  header: 'Browse AWS Marketplace',
  description:
    'Browse the public AWS Marketplace catalog for AMI products. '
    + 'Pick a listing to see full details and start the procurement flow.',
  breadcrumbMarketplace: 'Marketplace',
  breadcrumbBrowse: 'Browse catalog',

  // Search bar
  searchPlaceholder: 'Search AMI products (e.g. ubuntu, windows, firewall)',
  searchButton: 'Search',
  clearFiltersButton: 'Clear filters',

  // Result count / meta
  resultsCount: (shown: number, total?: number | null) =>
    // `total` is optional AND nullable, so both null and undefined mean "no
    // total available". Spelled out rather than using `!= null`, which the
    // repo's eqeqeq/no-eq-null rules reject.
    total !== null && total !== undefined && total > shown
      ? `Showing ${shown} of ${total.toLocaleString()} results`
      : `Showing ${shown} result${shown === SINGLE_RESULT ? '' : 's'}`
  ,
  loadMoreButton: 'Load more',

  // Facet sidebar
  facetSidebarHeader: 'Filters',
  facetCategoryHeader: 'Category',
  facetPricingModelHeader: 'Pricing model',
  facetPublisherHeader: 'Publisher',
  facetRatingHeader: 'Rating',
  facetLoading: 'Loading filters…',
  facetShowMore: 'Show more',
  facetShowLess: 'Show less',

  // Tile
  tilePublisherLabel: 'By',
  tileFreeBadge: 'Free',
  tileUsageBadge: 'Usage-based',
  tileContractBadge: 'Contract',
  tileBYOLBadge: 'BYOL',
  tileNoDescription: 'No description available.',
  tileViewButton: 'View details',

  // Empty state
  emptyTitle: 'No listings match your filters',
  emptySubtitle:
    'Try clearing filters or adjusting your search text. '
    + 'You can also browse the full AWS Marketplace catalog on the AWS Marketplace website.',
  emptyExternalButton: 'Open AWS Marketplace ↗',
  emptyExternalUrl: 'https://aws.amazon.com/marketplace',

  // Error
  errorTitle: 'Failed to load listings',
  errorRetry: 'Retry',
};
