# Use AWS Marketplace images

VEW can import AMIs from your AWS Marketplace subscriptions into the image catalog. Once imported, you publish them as products the same way you would any other image — the only difference is how VEW handles licensing in the spoke account.

You can also find and subscribe to Marketplace AMI products from inside VEW, accept private offers, and list or cancel the account's agreements. Those features are described from [Get a Marketplace product from inside VEW](#get-a-marketplace-product-from-inside-vew) onwards. Both halves use the hub account: VEW subscribes in the hub account, and imports from the hub account's subscriptions.

## Subscription ownership models

When you discover marketplace subscriptions in VEW, each one is classified into one of two models. The model determines what happens during publishing.

### VEW Managed subscription

The hub account subscribed directly to the product, and the license permits re-granting (`CreateGrant`). This does not depend on where the hub sits in the organization. When you publish a version that uses this image, VEW automatically creates a License Manager grant from the hub to the spoke account, accepts it, and activates it. You don't need to do anything on the spoke side.

### Externally Managed subscription

The hub received the license from outside — a vendor grant, an Organization-level distribution, or a similar arrangement. VEW cannot redistribute it automatically. Each spoke account must already have an active grant (distributed by an Organization admin) or its own independent Marketplace subscription before you publish. VEW checks for this at publish time and fails with a clear error if neither is present.

## Prerequisites

VEW needs no AWS Organizations or License Manager setup for Marketplace AMIs. The hub can
be the management account or any member account. VEW does not require a delegated
administrator, the License Manager Organizations integration, or its RAM resource share.

This is based on a live test (November 2026) in an organization with two accounts. A
plain member hub created grants for two Marketplace AMIs to the management account, and
the grants became `ACTIVE` and launched. This also worked with no delegated administrator
and with the Organizations integration switched off. An unsubscribed Marketplace AMI
failed with `OptInRequired`, so the grants were what made the launches work. Grants
between two member accounts, and to accounts outside the organization, were not tested.
If AWS refuses a grant, VEW falls back as described in
[If AWS refuses the grant](#if-aws-refuses-the-grant).

The AWS documentation says only the management account or the License Manager delegated
administrator can distribute licenses. If your organization relies on that, registering
the hub as delegated administrator does no harm, but VEW does not check for it.

The first grant a spoke account accepts can fail for about a minute with *"Marketplace
Service Linked Role creation is in-progress"* while AWS creates that role. The state
machine's retries cover this.

### Subscribe to a Marketplace product

For VEW Managed subscriptions, the hub account needs its own purchase. You can subscribe from inside VEW (see [Get a Marketplace product from inside VEW](#get-a-marketplace-product-from-inside-vew)) or in the AWS console:

1. Go to **AWS Marketplace → Discover products** in the hub account.
2. Subscribe to an AMI product. Prefer products with hourly-only pricing — products with annual contract pricing require a payment method on the account and will fail the agreement creation if one isn't configured.
3. Wait a few minutes for the subscription to activate.

For Externally Managed subscriptions, skip this step. The licenses already exist through external distribution.

### Distribute grants to spoke accounts (Externally Managed only)

If you're working with Externally Managed subscriptions, the account that holds the license must distribute grants to each spoke account that will run workbenches:

1. In that account, go to **License Manager → Granted licenses**, select the license, and choose **Create grant**.
2. Enter the spoke account ID.
3. In the spoke account, accept and activate the grant.

## Discover subscriptions

1. Go to **Project → Images → Import AMI → Marketplace Product**.
2. VEW lists all active Marketplace subscriptions in the hub account. Each subscription shows a badge indicating its ownership model — **VEW Managed** or **Externally Managed**.

If the list is empty, the hub account has no active Marketplace subscriptions. Subscribe to a product or ask your Organization admin to grant a license.

## Import a Marketplace AMI

1. From the import wizard, select **Marketplace Product** and pick a subscription.
2. Proceed to the image details step. Fill in the **Image Name**, **OS Version**, and at least one **Component Version**.
3. Review the summary and choose **Import**.

The image appears in the catalog with a purple **Marketplace** badge. The detail page includes a Marketplace Metadata section with subscription details.

VEW does not trust the details the browser sends. The import request carries the AMI id and the product code. VEW re-runs discovery for the project on the server and imports only when exactly one current subscription matches both. The license ARN, home region, regional AMI ids and ownership model come from that result, not from the request. If the subscription changed since the list was loaded, the import is rejected and you refresh the list.

If you've already imported a particular product, it shows as **Already Imported** in the subscription list (dimmed and non-selectable).

An AMI can be imported into one project only. Once a project has imported an AMI, importing the same AMI into another project fails with "already imported in another project", and that stays true after the first project retires its image. This applies to Marketplace AMIs and existing AMIs alike, because VEW records an imported AMI, and authorizes its licence grants, against a single project.

## Publish a product version

Create a product, then create a version selecting the marketplace-imported image. From here, the process is the same as any other product version — but what happens behind the scenes depends on the ownership model.

### VEW Managed license

VEW creates a License Manager grant from the hub to the spoke, accepts it in the spoke account, and waits for the launch permission to propagate. This is fully automatic. The version status progresses to **Created** once complete.

#### If AWS refuses the grant

If AWS refuses to create the grant, or the grant never reaches the spoke, VEW does not fail the version straight away. It checks whether the spoke already has its own active grant or subscription for the product, the same check it runs for an Externally Managed image. If the spoke has one, the version proceeds. If not, the version fails with `LicenseGrantNotVerified`, and the state machine execution input records AWS's error under `licenseGrantError`. Throttling and AWS service errors are not treated as a refusal: they fail the version, and retrying it can succeed.

### Externally Managed license

VEW first checks whether the spoke account already has an active grant or its own subscription for the product. If it does, the version proceeds normally — no new grant is created.

If the spoke has neither, VEW checks whether the hub can distribute the license after all. The label is recorded when you import the image, and earlier VEW versions labelled a hub-owned license Externally Managed unless the hub was the organization's management account with the License Manager integration active. At publish time, if the persisted license permits `CreateGrant` and the hub's license still allows it, VEW takes the VEW Managed route and creates the grant itself. You don't need to re-import such an image. Historical imports that do not contain the capability flag are treated as not grant-capable; rediscover and re-import to record the current license capability.

Publishing fails when the spoke has no grant and the license does not permit `CreateGrant`. Subscribe the spoke account to the product, or distribute the grant by hand (see [Distribute grants to spoke accounts](#distribute-grants-to-spoke-accounts-externally-managed-only)), and then retry.

## When a version fails

A failed version distribution carries a `statusReason` alongside its status and returns it from `GetProductVersion`, so API clients and operators do not have to inspect the Step Functions execution. The current UI does not display this field. It is a short line — an error name and message, never a stack trace — and is cleared when the version succeeds or is retried.

The reasons specific to Marketplace images are:

| `statusReason` begins with | What it means |
|---|---|
| `LicenseGrantNotVerified` | The spoke has no active grant for the product and the hub could not distribute one, either because the license does not allow `CreateGrant` or because AWS refused the grant (see [If AWS refuses the grant](#if-aws-refuses-the-grant)). |
| `LaunchPermissionDenied` | The grant exists but the spoke still cannot launch the regional AMI. Launch permission can lag a grant by a few minutes; retry before investigating. |
| `UnexpectedDecision` | An internal error: the sharing decision was one the state machine does not handle. |

## Instance type limits

A Marketplace product decides which instance types it may run on, and the seller
often allows only a few. Launching a workbench whose instance type is not on
that list fails with "The instance configuration for this AWS Marketplace
product is not supported", classified as a **template** failure, because the fix
is to change the instance type in the product's parameters rather than to retry.

Check the product's listing on AWS Marketplace for the types it supports before
choosing the workbench instance type. The message names no specific type, so
there is nothing in the failure itself to tell you which to pick.

## Deprecated AMIs

A seller can schedule an AMI deprecation time. VEW treats the AMI as deprecated only
once that UTC time has passed. VEW lists deprecated images so a subscription whose
images are all deprecated can still be imported, and prefers a supported image whenever
the product publishes one — you only get a deprecated AMI when there is no alternative.

A subscription in that state carries a **Deprecated** badge in the subscriptions
list and in the import wizard, and the wizard warns before you import. The
import still works; the warning is there because the vendor no longer supports
the image and may have published a replacement product under a new listing.

## Get a Marketplace product from inside VEW

Users who can manage products see a **Marketplace** section in the navigation. Subscriptions and Browse catalog are shown to every such user. Agreements and Procure offer are shown to admins only, because their APIs allow admins only, and the Subscribe button on a listing is disabled for other roles.

| Page | What it does |
|---|---|
| **Subscriptions** | The hub account's active Marketplace subscriptions, as used by [Import AMI](#import-a-marketplace-ami). |
| **Browse catalog** | Search the public AWS Marketplace catalog for AMI products. |
| **Agreements** | List the hub account's active AMI agreements and cancel them. |
| **Procure offer** | Pick a private offer that a seller has extended to the hub account. |

All Marketplace API calls go to `us-east-1`, whatever region VEW is deployed in, because the Marketplace Discovery and Agreement APIs are only available there.

### Browse the catalog

**Browse catalog** calls the Marketplace Discovery API `SearchListings`. VEW always adds two filters on the server side, and the caller cannot remove them:

- fulfillment option type `AMAZON_MACHINE_IMAGE`, so only AMI listings appear;
- number of products `SINGLE_PRODUCT`, so listings that bundle several products are excluded.

You can add free-text search and facet filters for category, pricing model, publisher and average customer rating. The facet values and counts come from `SearchFacets`. Results are paged, 25 per page by default and at most 100.

Choosing a listing opens its detail page (`GetListing`): description, highlights, use cases, resources, pricing models and reviews. If the listing has no AMI fulfillment option, the API returns an error instead of the detail. Seller-supplied HTML is sanitised before display, and seller-supplied links are rendered as links only when they use `https:` or `mailto:`; anything else is shown as plain text.

The detail page's main action depends on the listing:

| Listing | Button | What happens |
|---|---|---|
| FREE or USAGE pricing | **Subscribe** | Opens the subscribe wizard. |
| BYOL pricing | **Subscribe with own license** | Opens the subscribe wizard. |
| CONTRACT pricing | **Buy contract** | Opens the subscribe wizard. |
| Published by AWS itself (Windows Server, RHEL, SUSE and similar) | **Import this AMI** | Resolves the listing to an AMI and opens the Import AMI wizard. See [Import an AMI that AWS publishes](#import-an-ami-that-aws-publishes). |

If a listing offers several pricing models, the label follows the order FREE, BYOL, USAGE, CONTRACT. The wizard uses the listing's first associated offer.

### Private offers

**Procure offer** lists the offers a seller has extended privately to the hub account (`ListPurchaseOptions` with visibility scope `PRIVATE`). That API cannot filter by product type, so VEW calls `GetProduct` for each product and drops any that has no AMI fulfillment option. A product whose type cannot be determined is also dropped, and the failure is logged. If no private offers exist, the page says so and links to the AWS Marketplace website.

A private offer goes through the same wizard as a public one. The steps depend on the offer's pricing model, as described below.

### The subscribe wizard

The wizard turns an offer into an agreement in two AWS calls:

1. `CreateAgreementRequest` creates a quote: an agreement request for a specific set of the offer's terms. AWS returns an `agreementRequestId` and, for up-front pricing, the estimated total.
2. `AcceptAgreementRequest` accepts that quote. AWS creates the agreement and returns its `agreementId`. From this point the hub account is bound by the agreement.

The buyer must tick **I have read and agree to the terms** on the Review terms step before VEW requests a quote. Review terms shows the offer, the seller, the pricing model, the rate card, links to the legal documents and the refund policy.

| Pricing model | Wizard steps | Terms VEW sends in the quote | What the buyer sees before accepting |
|---|---|---|---|
| FREE | Review terms → Accept & confirm | Mandatory terms + `UsageBasedPricingTerm` | A "Free tier" notice: no software fee, EC2 compute is still billed. |
| USAGE | Review terms → Accept & confirm | Mandatory terms + `UsageBasedPricingTerm`, `RecurringPaymentTerm` | The rate card. AWS returns no up-front total for usage pricing. |
| BYOL | Review terms → Accept & confirm | Mandatory terms + `ByolPricingTerm` | A notice that the licence comes from the seller, not from AWS or VEW. |
| CONTRACT | Review terms → Configure your contract → Accept & confirm | Every term on the offer, with the buyer's configuration attached to `ConfigurableUpfrontPricingTerm` | The estimated total and the total after tax, as quoted by AWS. If AWS returns no total, **Finish** is disabled and the buyer can request a new quote. |

The mandatory terms are `LegalTerm`, `SupportTerm`, `ValidityTerm`, `RenewalTerm` and, when the offer has one, `FreeTrialPricingTerm`. VEW always sends `RenewalTerm` with auto-renewal turned off.

In AWS's Agreement API a FREE offer is a usage offer whose prices are all zero, so VEW handles FREE and USAGE the same way. Before it requests a FREE quote, the web app checks that every rate on the usage and recurring terms it would send is zero, and refuses the request otherwise.

For the two-step flows, VEW requests the quote in the background as soon as the buyer agrees to the terms. Accept & confirm explains what **Finish** does for that pricing model. **Finish** sends the accept call.

For CONTRACT, the **Configure your contract** step shows each rate card, usually one per contract duration (for example 12, 24 or 36 months). The buyer picks one. If the rate card allows it, the buyer also enters a quantity per dimension, as a whole number of 1 or more. If the rate card allows only one dimension per agreement, the buyer picks exactly one. VEW sends the choice as `configurableUpfrontPricingTermConfiguration` (`selectorValue` and `dimensions`). Any change to the duration or a quantity discards the current quote and requests a new one, so the buyer can only accept a quote for the configuration on screen. Quantity edits are debounced, so typing a number requests one quote for the final value, not one per keystroke.

After a successful accept, the wizard shows the new agreement ID and two actions: **Import this AMI**, which opens the Import AMI wizard on the Marketplace source with the purchased subscription preselected, matched on the Marketplace product ID (if the new subscription is not listed yet, the wizard shows the normal picker and asks the user to reload in a few minutes), and a link to the Agreements page. The wizard cannot be stepped back after the agreement exists, so the same quote cannot be accepted twice.

### Checks before a quote is created

The backend runs these checks before it calls `CreateAgreementRequest`:

1. **At least one term.** A request with no requested terms is rejected.
2. **No duplicate subscription.** VEW lists the account's active agreements and rejects the request if one already exists for the same offer. The error names the existing agreement and suggests cancelling it or importing the AMI. If listing agreements fails, VEW skips this check and leaves the decision to AWS. A different offer for the same product is not caught by this check.
3. **AMI only, single product.** VEW calls `GetOffer` and rejects offers with no product, offers that belong to a multi-product offer set, and offers that reference more than one product. It then calls `GetProduct` and rejects the offer unless the product has an AMI fulfillment option.

If AWS rejects the request, for example because a term configuration is invalid, the API returns HTTP 400 with AWS's message.

### Idempotency

`CreateAgreementRequest` takes a `clientToken` (1 to 64 characters, letters, digits and hyphens). AWS returns the same agreement request for repeated calls with the same token and payload. The web app generates a new token per offer and pricing configuration, and reuses it when the same quote is retried, so a retry returns the existing agreement request and a later purchase of the same configuration gets a new one. A caller that sends no token gets one derived from the project, the offer, the agreement proposal and the requested terms, sorted by term ID.

AWS can answer a repeated `AcceptAgreementRequest` or `CancelAgreement` with `ConflictException`. On a live check with a free offer, a second accept of the same request returned the same agreement ID and a second cancel of a cancelled agreement succeeded; both publish their event again (see below). The handling for a conflict is:

- **Cancel:** VEW treats the conflict as success when `DescribeAgreement` reports the agreement `CANCELLED`, because the agreement to cancel is known. That also covers an agreement cancelled outside VEW; the event's `cancelledAt` is then the time VEW saw the cancellation.
- **Accept:** AWS offers no API that maps an agreement request to the agreement it created, so VEW cannot tell a repeated accept from a conflict with another purchase of the same offer. A conflicting accept is refused with HTTP 400 and a message that points the buyer to the **Agreements** page. It is never reported as a successful purchase.

After each of the three AWS write calls, VEW publishes a domain event (`AgreementRequestCreated`, `AgreementRequestAccepted`, `AgreementCancelled`). Publication is best effort. If it fails, the API still reports the AWS outcome, because the AWS change has already happened. VEW logs the failure at ERROR level with the agreement identifiers and emits the `MarketplaceEventPublishFailed` metric. This includes entries that EventBridge rejects individually in an otherwise successful `PutEvents` call. A repeated create or a recovered cancel publishes its event again, so a consumer must deduplicate: `AgreementRequestCreated` on `agreementRequestId`, `AgreementCancelled` on `agreementId`. Nothing consumes these events today.

## Import an AMI that AWS publishes

For some Marketplace products AWS is the seller of record: Windows Server, Red Hat Enterprise Linux, SUSE, Ubuntu Pro, Amazon Linux and similar. `CreateAgreementRequest` is rejected for those, so no agreement and no License Manager grant ever exist, and they never appear in the subscriptions list. They are imported directly instead.

The listing detail page offers **Import this AMI**, which calls `POST /projects/{projectId}/images/aws-published/resolve` with the listing ID. VEW reads the listing's product back from AWS and resolves it to an AMI two ways:

1. **By product code.** The product's offer carries a purchase-option ID, which is the product code AWS stamps on the published AMI, so `DescribeImages` filtered on that code returns exactly that product's images. This is how most products resolve.
2. **By a verified table.** The plain-OS products AWS publishes itself carry no product code; their licence is priced through the EC2 billing code. For those VEW matches on a table of owner account, anchored AMI name pattern, architecture and `UsageOperation`. Neighbouring families under one owner (a high-availability or BYOL variant of the same OS) are different licensed products, so both the full name and the billing code must match.

A product that neither path identifies is reported as unresolvable, with a note that a product needing a subscription has to go through the subscribe wizard first. Nothing is guessed. When a product still offers several AMIs, they differ by architecture and the user picks one.

The import then runs as image source `AWS_PUBLISHED_AMI` and must carry the listing ID. VEW resolves the listing again on the server and refuses the import unless that resolution offers the AMI, because this source has no product code and no Image Service ownership to check, and the AMI ID comes from the caller. For the same reason the caller's `regionalAmiIds` are ignored and only the resolved region is recorded: those IDs go into the published product template. A second check requires the AMI's owner to be one of the known vendor accounts.

These imports record `subscriptionOwnership=AWS_MANAGED` when the AMI has no product code, since there is no subscription to own; the licence is granted at launch. An AMI that does carry a product code is recorded as `VEW_MANAGED` with that code and, where one is found, the agreement it belongs to.

Keeping the table current is manual work: when AWS changes an AMI naming scheme, that product stops resolving until its entry is updated. The tests pin each entry's pattern together with the near-misses it must not match.

## Manage agreements

An AWS Marketplace agreement belongs to the AWS account, not to a VEW project. AWS records no project on an agreement. The agreement routes are therefore account-scoped and have no `/projects/{projectId}` prefix:

| Method and path | Cedar action | What it does |
|---|---|---|
| `GET /marketplace/agreements` | `ListMarketplaceAgreements` | Lists the hub account's active purchase agreements (`SearchAgreements`) where every resource is an `AmiProduct`. Each row is enriched with the product name, offer name and pricing model from `GetOffer`. If enrichment fails for a row, the row is still returned with raw IDs. |
| `POST /marketplace/quotes/{agreementRequestId}/accept` | `AcceptMarketplaceQuote` | Accepts a quote and returns the `agreementId`. |
| `DELETE /marketplace/agreements/{agreementId}` | `CancelMarketplaceAgreement` | Cancels an agreement (`CancelAgreement`). VEW first reads the agreement with `DescribeAgreement` and refuses to cancel one that is not an AMI agreement. |

These three actions are permitted to any user whose `totalAdminAssignments` is greater than 0, that is, a user who is an admin of at least one VEW project. In practice, **any project admin can list, accept and cancel every Marketplace agreement in the hub account**, including agreements created from another project or outside VEW. Treat Marketplace purchasing as a platform-level permission when you assign project admins.

The **Agreements** page lists the agreements and offers a **Cancel** action with a confirmation dialog.

## Agreement lifecycle events

AWS Marketplace publishes buyer-side agreement events (`source` `aws.agreement-marketplace`) on the default EventBridge bus in `us-east-1`. VEW subscribes to six of them:

- `Purchase Agreement Created - Acceptor`
- `Purchase Agreement Amended - Acceptor`
- `Purchase Agreement Ended - Acceptor`
- `Purchase Agreement Ending - Acceptor`
- `Purchase Agreement Renewal Terms Finalized - Acceptor`
- `Purchase Agreement Renewal Upcoming - Acceptor`

An EventBridge rule sends these events to the packaging Lambda `marketplace-agreement-events`. The events carry no product type, so the rule matches agreements for every product type in the account. The Lambda calls `DescribeAgreement` for each event and drops the event unless every resource on the agreement is an `AmiProduct`. For AMI agreements it republishes the event on VEW's domain event bus as `MarketplaceAgreementActivated`, `MarketplaceAgreementAmended`, `MarketplaceAgreementEnded` and so on.

If `DescribeAgreement` fails, the Lambda raises an error instead of dropping the event, because an unknown product type is not the same as a non-AMI product. The same applies to an Ending event that is missing `daysBeforeEndTime` or `endTime`. The Lambda is invoked asynchronously. After its retries, a failed event goes to the Lambda's dead-letter queue (`<function-name>-dlq`), where it can be inspected and replayed. A separate dead-letter queue on the EventBridge rule target catches events that EventBridge could not deliver to the Lambda at all.

The Lambda refuses to start in any region other than `us-east-1`.

## API routes and authorization

| Method and path | Cedar action | Who may call it |
|---|---|---|
| `GET /projects/{projectId}/marketplace/subscriptions` | `DiscoverMarketplaceSubscriptions` | Product contributors of the project |
| `GET /projects/{projectId}/marketplace/listings` | `SearchMarketplaceListings` | Product contributors of the project |
| `GET /projects/{projectId}/marketplace/listings/{listingId}` | `GetMarketplaceListing` | Product contributors of the project |
| `GET /projects/{projectId}/marketplace/facets` | `GetMarketplaceFacets` | Product contributors of the project |
| `POST /projects/{projectId}/images/aws-published/resolve` | `ResolveAwsPublishedAmi` | Product contributors of the project |
| `GET /projects/{projectId}/marketplace/purchase-options` | `ListMarketplacePurchaseOptions` | Admins of the project |
| `GET /projects/{projectId}/marketplace/offers/{offerId}` | `GetMarketplaceOffer` | Admins of the project |
| `POST /projects/{projectId}/marketplace/offers/{offerId}/quotes` | `CreateMarketplaceQuote` | Admins of the project |
| `POST /marketplace/quotes/{agreementRequestId}/accept` | `AcceptMarketplaceQuote` | Admins of at least one project |
| `GET /marketplace/agreements` | `ListMarketplaceAgreements` | Admins of at least one project |
| `DELETE /marketplace/agreements/{agreementId}` | `CancelMarketplaceAgreement` | Admins of at least one project |

"Product contributors of the project" and "Admins of the project" are the Cedar conditions `principal in resource.productContributors` and `principal in resource.admins`. The project-scoped routes check the project ID format but do not filter Marketplace data by project. The catalog, the private offers and the agreements are the same for every project.

## IAM permissions

The packaging API Lambda's role has these Marketplace actions, all on `Resource: "*"`:

| Purpose | Actions |
|---|---|
| Import AMI: discover subscriptions | `aws-marketplace:SearchAgreements` |
| Private offers: drop non-AMI products | `aws-marketplace:GetProduct` |
| Cancel: read the status back | `aws-marketplace:DescribeAgreement` |
| Private offers and quotes | `aws-marketplace:ListPurchaseOptions`, `GetOffer`, `GetOfferTerms` |
| Subscribe and cancel | `aws-marketplace:CreateAgreementRequest`, `AcceptAgreementRequest`, `CancelAgreement` |
| Browse the catalog | `aws-marketplace:SearchListings`, `GetListing`, `SearchFacets` |
| Resolve an AWS-published AMI | `aws-marketplace:ListPurchaseOptions`, `GetListing`; `ec2:DescribeImages` |

The role also has `license-manager:ListReceivedLicenses`, `ec2:DescribeImages` and `DescribeImageAttribute`, all on `*`, for subscription discovery and AMI validation.

The `marketplace-agreement-events` Lambda has only `aws-marketplace:DescribeAgreement` on `*`, plus permission to put events on VEW's domain event bus.

Why `*`: the Agreement API actions define no resource types in the IAM Service Authorization Reference, only condition keys such as `aws-marketplace:AgreementType`, `aws-marketplace:PartyType` and `aws-marketplace:ProductId`. The Discovery API does support resource-level permissions, but the listings, products and offers VEW reads are whatever the user picks from the public catalog at runtime, so no fixed resource list exists. The write actions cover purchases of any product type, so VEW checks the AMI-only rule in code: when it creates a quote, and before it cancels an agreement. Accept has no such check, because AWS offers no API that maps an agreement request to its product; VEW accepts only the quote ID the caller sends. If you want IAM to enforce more, condition keys such as `aws-marketplace:AgreementType` are the place to start. See [Actions, resources, and condition keys for AWS Marketplace](https://docs.aws.amazon.com/service-authorization/latest/reference/list_marketplace-agreement.html) and [Access control for the AWS Marketplace Discovery API](https://docs.aws.amazon.com/marketplace/latest/APIReference/discovery-api-access-control.html).

## Known limitations

- **The CONTRACT accept path is covered by unit tests only.** Accepting a paid CONTRACT agreement has not been exercised against a real AWS agreement.
- **Agreements are created in the hub account.** The hub account is the buyer of record and pays for every subscription, whichever project started it. Spoke accounts get access through the [publishing flow](#publish-a-product-version).
- **There is no provisioning signal after accept.** VEW does not wait for the agreement to become active or for the AMI entitlement to reach the account. The lifecycle events are republished on the domain bus, but nothing consumes them.
- **An AWS-published listing with no resolvable AMI cannot be imported.** See [Import an AMI that AWS publishes](#import-an-ami-that-aws-publishes).
- **Multi-product listings and offer sets are excluded.** Browse hides them and the quote check rejects them.
- **Only AMI products are supported.** Container, SaaS and other product types are filtered out of browse, private offers, agreements and lifecycle events. The AMI-only rule is enforced in code; there is no setting to widen it.
- **Auto-renewal is always sent as off.** VEW has no control to turn it on. Change it in the AWS Marketplace console if needed.
- **No payment-method pre-check.** If the hub account has no payment method for a paid offer, AWS rejects the request and VEW shows AWS's error.
- **Region-restricted products** are rejected by AWS when the quote is created. VEW does not warn in advance.
- **Lifecycle events require a `us-east-1` deployment.** AWS publishes them only in `us-east-1`, and the event Lambda will not start elsewhere.
- **AWS refuses to cancel an agreement in the first minutes after it was accepted.** On a live check with a free offer, `CancelAgreement` returned `ValidationException` "This action is not supported." for at least 77 seconds after the accept and succeeded after 158 seconds. VEW reports the refusal as HTTP 400 with AWS's message and a hint to try again or to use **Manage subscriptions** in the AWS Marketplace console. The window is not documented by AWS and was measured once.
- **Repeat calls were checked once, on a free offer.** A second accept of the same request returned the same agreement ID, and a second cancel of a cancelled agreement succeeded. Both publish their event again, so consumers must deduplicate. The `ConflictException` handling is covered by unit tests only, because AWS did not raise it. A paid CONTRACT accept has not been run.
- **The import hand-off assumes the license's product SKU is the Marketplace product ID.** If it is not, the import wizard falls back to the normal subscription picker.
- **Agreement permissions are account-wide.** See [Manage agreements](#manage-agreements).
