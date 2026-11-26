export const i18n = {
  wizardTitle: 'Procure from AWS Marketplace',
  wizardDescription:
    'Purchase an AWS Marketplace AMI product for this project. '
    + 'The agreement is stored under the current buyer account and can be '
    + 'imported into VEW after acceptance.',

  step1Title: 'Browse offers',
  step1Description: 'Pick a purchase option to procure. Only AMI products are supported today.',
  step2Title: 'Review terms',
  step2Description: 'Review the offer, pricing model, and legal terms before requesting a quote.',
  step3Title: 'Get quote',
  step3Description: 'Confirm the pricing quote returned by AWS Marketplace.',
  step4Title: 'Accept & confirm',
  step4Description: 'Accept the quote to create the durable agreement.',

  productTypeTabAmi: 'AMI',
  productTypeTabContainer: 'Container',
  productTypeTabSaas: 'SaaS',
  comingSoonBadge: 'Coming soon',

  columnPurchaseOptionName: 'Purchase option',
  columnProductName: 'Product',
  columnSeller: 'Seller',
  columnPurchaseOptionType: 'Type',
  columnOfferId: 'Offer ID',
  columnExpires: 'Expires',
  columnStatus: 'Status',

  emptyPurchaseOptionsTitle: 'No private offers yet',
  emptyPurchaseOptionsSubtitle:
    'No private offers have been extended to this account yet. '
    + 'Browse the full AWS Marketplace catalog on the AWS Marketplace website.',
  emptyPurchaseOptionsButton: 'Open AWS Marketplace ↗',
  emptyPurchaseOptionsUrl: 'https://aws.amazon.com/marketplace',

  offerHeaderLabel: 'Offer',
  offerNameLabel: 'Offer name',
  productLabel: 'Product',
  sellerLabel: 'Seller',
  pricingModelLabel: 'Pricing model',
  termsLabel: 'Terms',
  agreeCheckboxLabel: 'I have read and agree to the terms',
  freeOfferChargesError:
    'This offer is listed as free, but its pricing terms include a charge. '
    + 'No subscription request was sent.',
  reviewTermsNoOfferHint: 'Select a purchase option first.',

  freeTierBadge: 'Free tier',
  freeTierAlertHeader: 'This offer has no software licence fee.',
  freeTierAlertBody:
    'The pricing model returned by AWS Marketplace for this offer is FREE. '
    + 'You can accept the agreement without going through a quote step. '
    + 'Note: EC2 compute costs still apply when the AMI is launched — AWS '
    + 'bills you for the instance hours; only the Marketplace software fee is $0.',

  byolBadge: 'Bring your own license',
  byolAlertHeader: 'This is a Bring-Your-Own-License offer.',
  byolAlertBody:
    'Accepting this agreement only grants your account permission to launch '
    + 'the AMI — no licence key is collected by AWS or VEW. The software '
    + 'inside will check its own licence at first boot (either against a key '
    + 'you paste in, a file you provide, or by activating against the '
    + 'seller\u2019s service). You obtain the licence directly from the '
    + 'seller — AWS is not involved in licence purchase, delivery, or '
    + 'billing. You still pay AWS for the EC2 compute when the AMI runs.',

  directImportTitle: 'Import this AMI',
  directImportAlertHeader: 'No subscription needed for this product.',
  directImportAlertBody:
    'AWS sells this product itself, and the licence is granted when you '
    + 'launch an EC2 instance from the AMI — there is no Marketplace '
    + 'agreement to accept, which is why there is no subscribe step. Continue '
    + 'to the Import AMI wizard: it looks up the AMI for this listing and '
    + 'imports it into the project.',
  directImportButton: 'Continue to import',
  directImportBackButton: 'Back to Browse catalog',
  directImportDefaultSeller: 'Amazon Web Services',
  directImportNoListing:
    'This page was opened without a listing, so the AMI cannot be looked up. '
    + 'Open the product from Marketplace \u2192 Browse catalog and try again.',
  directImportInfoHelp:
    'Products AWS sells itself (Windows Server, RHEL, SUSE, Ubuntu Pro, '
    + 'Amazon Linux) carry no pricing term, so there is no agreement to '
    + 'create. VEW resolves the AMI from the listing and imports it directly. '
    + 'Third-party products are subscribed to through this wizard as usual.',

  quoteHeader: 'Quote',
  quoteAgreementRequestIdLabel: 'Quote ID',
  quoteEstimatedValueLabel: 'Estimated agreement value',
  quoteEstimatedValueAfterTaxLabel: 'Estimated after tax',
  quoteCurrencyLabel: 'Currency',
  quoteUsageBased: 'Usage-based pricing (see terms)',
  quoteEstimateUnavailable: 'Estimate unavailable',
  quoteCurrencyUnknown: '(currency unknown)',
  commitEstimateUnavailableHeader: 'No estimated total from AWS',
  commitEstimateUnavailableBody:
    'AWS did not return an estimated total for this contract quote, so it cannot be '
    + 'accepted. Get a new quote to try again.',
  requestQuoteButton: 'Request quote',

  acceptHeader: 'Accept agreement',

  // ---------------------------------------------------------------------------
  // Configure & Confirm Pricing step (CONTRACT flow)
  //
  // Third-step-of-three for CONTRACT offers. User picks a rate card
  // (usually a duration like P12M/P24M/P36M) and — when the offer
  // permits — sets per-dimension quantities. Emits a
  // ContractPricingConfig that the wizard attaches to
  // CreateAgreementRequest as
  // configuration.configurableUpfrontPricingTermConfiguration.
  // ---------------------------------------------------------------------------
  configurePricingHeader: 'Configure your contract',
  configurePricingDescription:
    'Choose the duration and, if the offer allows it, the quantity for each '
    + 'dimension. AWS charges the total upfront when you accept the agreement.',
  configurePricingSelectorLabel: 'Duration',
  configurePricingDimensionsLabel: 'Dimensions',
  configurePricingTotalLabel: 'Total',
  configurePricingRenewalHint:
    'Auto-renewal is off for this agreement. You can change it in the AWS '
    + 'Marketplace console. When enabled, AWS creates a new agreement at expiry '
    + 'using the renewal terms shown on the previous step.',
  configurePricingNoOfferHint: 'Select a purchase option first.',
  configurePricingNoRateCardsError:
    'This offer\u2019s pricing term does not include any selectable rate cards. '
    + 'This is unusual for a CONTRACT offer — please contact the seller directly.',
  // Shown under a quantity input the buyer has made invalid. The wizard's
  // Next button is disabled while any of these is visible, so the message has
  // to say what to do, not just that something is wrong.
  configurePricingQuantityInvalidError:
    'Enter a whole number of 1 or more.',
  // multipleDimensionSelection=Disallowed: AWS rejects a configuration that
  // carries more than one dimension, so the buyer picks exactly one.
  configurePricingSingleDimensionLabel: 'Dimension',
  configurePricingSingleDimensionHint:
    'This rate card allows only one dimension per agreement.',

  // ---------------------------------------------------------------------------
  // Commit step (Accept & Confirm — pristine state)
  //
  // Copy is deliberately terse. The user has already reviewed pricing +
  // legal terms on Step 2; this step's sole job is to make the *commit
  // action* unambiguous.
  // ---------------------------------------------------------------------------
  commitHeader: 'You are about to subscribe',
  commitProductLabel: 'Product',
  commitBadgeFree: 'Free',
  commitBadgeUsage: 'Pay-as-you-go',
  commitBadgeContract: 'Annual contract',
  commitBadgeByol: 'Bring your own license',
  commitBadgeGeneric: 'Subscription',
  commitDescriptionFree:
    'Clicking Finish creates an active subscription. You will be able to launch '
    + 'this AMI in your account. There is no software licence fee — you still pay '
    + 'AWS for the EC2 instance itself (compute, storage, network).',
  commitDescriptionUsage:
    'Clicking Finish creates an active subscription. You will be able to launch '
    + 'this AMI in your account. AWS bills you per hour based on the EC2 instance '
    + 'type you launch — no charge until you actually run it, and no upfront '
    + 'commitment.',
  commitDescriptionByol:
    'Clicking Finish grants your account permission to launch this AMI. No '
    + 'licence key is collected here — AWS is only issuing the entitlement. '
    + 'The software inside the AMI will ask for its own licence (or activate '
    + 'against the seller\u2019s service) at first boot. If you do not already '
    + 'have a licence from the seller, obtain one directly from them before '
    + 'launching — AWS is not involved in licence purchase or billing.',
  commitDescriptionContract:
    'Clicking Finish creates an active subscription with the terms you configured. '
    + 'AWS will invoice the committed amount immediately.',
  commitDescriptionGeneric:
    'Clicking Finish creates an active subscription with the terms shown on the '
    + 'previous step.',

  // Shown above the Finish button on the commit step. The CONTRACT flow never
  // renders ProcurementStepGetQuote (step 3 is the pricing configurator
  // instead), so without this the buyer commits to a priced agreement having
  // never seen the total AWS quoted.
  commitQuoteHeader: 'What AWS will charge',
  acceptedAgreementIdLabel: 'Agreement ID',
  acceptedSuccessTitle: 'Agreement created',
  acceptedNextStepsHint:
    'Your subscription will appear in the Marketplace subscriptions list '
    + 'once AWS finishes provisioning the license grant (typically 1-2 minutes). '
    + 'You can start the Import AMI flow now — the new subscription will show up '
    + 'in the marketplace-source picker as soon as it is discovered.',
  importAmiButton: 'Import this AMI',
  goToAgreementsButton: 'Go to agreements',

  nextButton: 'Next',
  previousButton: 'Previous',
  cancelButton: 'Cancel',
  submitButton: 'Finish',
  // Replaces 'Finish' on the success panel: the agreement already exists, so
  // the action is "leave", not "commit".
  doneButton: 'Done',
  stepNumberLabel: (step: number) => `Step ${step}`,
  collapsedStepsLabel: (step: number, total: number) => `Step ${step} of ${total}`,

  productTypeInfoAmi:
    'AMI products deploy as EC2 machine images and are the only product type '
    + 'supported in VEW today.',
  productTypeInfoOthers:
    'Container and SaaS product types are on the roadmap but not yet supported.',

  errorRetry: 'Retry',
  errorQuoteExpiredHint:
    'This quote is no longer valid — Marketplace refused it (it may have expired '
    + 'or the terms may have changed). Request a fresh quote and try again.',
  errorAcceptFailed: 'Accepting the quote failed. Please try again.',
  getNewQuoteButton: 'Get a new quote',

  breadcrumbMarketplace: 'Marketplace',
  breadcrumbBrowse: 'Browse catalog',
  // Used as the final breadcrumb crumb regardless of entry point:
  // both the public-catalog Subscribe hand-off (`?offerId=X`)
  // and the cold left-nav "Procure offer" entry land on the same
  // wizard, which handles public and private offers alike.
  breadcrumbProcure: 'Procure offer',

  cancelPromptHeader: 'Cancel procurement?',
  cancelPromptText1: 'Progress will be lost.',
  cancelPromptCancelText: 'Keep going',
  cancelPromptConfirmText: 'Cancel procurement',
};
