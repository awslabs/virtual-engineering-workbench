# Use AWS Marketplace images

VEW can import AMIs from your AWS Marketplace subscriptions into the image catalog. Once imported, you publish them as products the same way you would any other image — the only difference is how VEW handles licensing in the spoke account.

## Subscription ownership models

When you discover marketplace subscriptions in VEW, each one is classified into one of two models. The model determines what happens during publishing.

### VEW Managed subscription

The hub account subscribed directly to the product, and the license permits re-granting. When you publish a version that uses this image, VEW automatically creates a License Manager grant from the hub to the spoke account, accepts it, and activates it. You don't need to do anything on the spoke side.

### Externally Managed subscription

The hub received the license from outside — a vendor grant, an Organization-level distribution, or a similar arrangement. VEW cannot redistribute it automatically. Each spoke account must already have an active grant (distributed by an Organization admin) or its own independent Marketplace subscription before you publish. VEW checks for this at publish time and fails with a clear error if neither is present.

## Prerequisites

These are one-time setup steps performed by an AWS administrator in the hub account.

### Enable License Manager Organization integration

1. Go to **AWS Marketplace → Settings → AWS License Manager integration → View setting details** and choose **Create integration**. This creates the `AWSServiceRoleForMarketplaceLicenseManagement` service-linked role.
2. Go to **License Manager → Settings → Account details** and choose **Link AWS Organizations accounts**.

This enables cross-account license sharing. You can verify it worked by checking **IAM → Roles** for the `AWSServiceRoleForMarketplaceLicenseManagement` role.

The same two steps from the CLI, in this order, run in the organization's
management account:

```bash
# 1. The service-linked role AWS Marketplace uses to manage licenses.
aws iam create-service-linked-role \
  --aws-service-name license-management.marketplace.amazonaws.com

# 2. Link AWS Organizations accounts.
aws license-manager update-service-settings \
  --organization-configuration EnableIntegration=true

# Confirm, and see the resource share it creates.
aws license-manager get-service-settings \
  --query '{integration:OrganizationConfiguration.EnableIntegration,share:LicenseManagerResourceShareArn}'
```

The order matters: linking Organizations before the service-linked role exists
fails. `deploy.sh` reports the current state in Phase 7c, read-only — it never
changes the setting, because this is an account-wide decision for an
administrator rather than something a deployment should switch on.

**Allow about 30 minutes.** `EnableIntegration` reads back as `true` almost at
once, but the RAM resource share that actually permits cross-account grants
takes a while to propagate. Until it does, importing works and distributing a
grant fails.

You do not have to enable it before importing. The decision of whether to
distribute a grant is taken again every time a product version is published, so
a subscription imported while the integration was off starts getting grants once
it is on — no re-import needed.

### Subscribe to a Marketplace product

For VEW Managed subscriptions, the hub account needs its own purchase:

1. Go to **AWS Marketplace → Discover products** in the hub account.
2. Subscribe to an AMI product. Prefer products with hourly-only pricing — products with annual contract pricing require a payment method on the account and will fail the agreement creation if one isn't configured.
3. Wait a few minutes for the subscription to activate.

For Externally Managed subscriptions, skip this step. The licenses already exist through external distribution.

### Distribute grants to spoke accounts (Externally Managed only)

If you're working with Externally Managed subscriptions, an Organization admin must distribute grants to each spoke account that will run workbenches:

1. In the hub account, go to **License Manager → Granted licenses**, select the license, and choose **Create grant**.
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

## Publish a product version

Create a product, then create a version selecting the marketplace-imported image. From here, the process is the same as any other product version — but what happens behind the scenes depends on the ownership model.

### VEW Managed license

VEW creates a License Manager grant from the hub to the spoke, accepts it in the spoke account, and waits for the launch permission to propagate. This is fully automatic. The version status progresses to **Created** once complete.

### Externally Managed license

VEW first checks whether the spoke account already has an active grant or its own subscription for the product. If it does, the version proceeds normally — no new grant is created.

If the spoke has neither, VEW checks whether it can distribute a grant itself, which it can when the License Manager Organizations integration is enabled in the hub. In that case it creates and accepts the grant exactly as for a VEW Managed licence, so no manual step is needed.

Only when the spoke has no grant *and* the integration is off does the version fail. Either enable the integration (see [above](#enable-license-manager-organization-integration)) and retry, or distribute the grant by hand (see [Distribute grants to spoke accounts](#distribute-grants-to-spoke-accounts-externally-managed-only)) and then retry.

## When a version fails

A failed version distribution carries a `statusReason` alongside its status, returned by `GetProductVersion` and shown in the UI, so the reason no longer has to be dug out of the Step Functions execution. It is a short line — an error name and message, never a stack trace — and is cleared when the version succeeds or is retried.

The reasons specific to Marketplace images are:

| `statusReason` begins with | What it means |
|---|---|
| `LicenseGrantNotVerified` | The spoke has no active grant for the product and the hub could not distribute one. |
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

A seller deprecates an AMI when it is superseded. VEW lists deprecated images so
a subscription whose images are all deprecated can still be imported, and
prefers a supported image whenever the product publishes one — you only get a
deprecated AMI when there is no alternative.

A subscription in that state carries a **Deprecated** badge in the subscriptions
list and in the import wizard, and the wizard warns before you import. The
import still works; the warning is there because the vendor no longer supports
the image and may have published a replacement product under a new listing.
