# Use AWS Marketplace images

VEW can import AMIs from your AWS Marketplace subscriptions into the image catalog. Once imported, you publish them as products the same way you would any other image — the only difference is how VEW handles licensing in the spoke account.

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

For VEW Managed subscriptions, the hub account needs its own purchase:

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
