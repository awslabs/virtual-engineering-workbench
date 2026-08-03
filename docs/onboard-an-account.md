# Onboard a technology account

Before anyone can publish products, the platform needs a **technology** with at least one **onboarded AWS account**. Onboarding an account is what creates the AWS Service Catalog **portfolio** that products and product versions are published into. This is a one-time setup per technology (and per stage), not something you repeat for every product.

If you skip it, creating a product version fails with:

> Error while creating product version!
> No portfolio found for DEV stage. Account setup might be incomplete.

This is an administrator task, done in the **Administration** area. It's separate from the day-to-day packaging and publishing work that product contributors do.

## What you'll need

- A deployed VEW platform and an account with administrator access.
- The 12-digit ID of an AWS account that has been bootstrapped as a **spoke account**. See [Spoke account onboarding](../README.md#spoke-account-onboarding) in the README — this is the AWS account where workbenches for this technology will be provisioned.

## Step 1: Create a technology

A technology groups products and the AWS accounts they're published into (for example, a product line, a customer program, or a hardware family).

1. Go to **Administration** → **Technologies** in the side navigation.
2. Choose **Add technology**.
3. Fill in the form:

   | Field | Value |
   | ------- | ------- |
   | Technology name | A short name, e.g. `Virtual Targets` (1–50 characters) |
   | Technology description | Optional description |

4. Choose **Continue**.

The new technology appears in the **Technologies** list.

## Step 2: Onboard an AWS account to the technology

1. From the **Technologies** list, choose the technology you just created to open its details page.
2. In the **Technology accounts** section, choose **Onboard**.
3. Fill in the form:

   | Field | Value |
   | ------- | ------- |
   | Account ID | The 12-digit AWS account ID of your spoke account |
   | Name | A label for the account, e.g. `acct-vew-dev-user` |
   | Type | **User** |
   | Description | Optional description |
   | Environment | **DEV** |
   | Region | The region the account is based in |
   | Technology | Pre-selected — leave it as the technology you opened |

4. Choose **Onboard**.

Onboarding runs asynchronously: VEW provisions resources in the target account and then creates and shares the Service Catalog portfolio. The account starts in an **OnBoarding** status.

## Step 3: Confirm onboarding completed

On the technology details page, wait for the account's status to leave **OnBoarding** and become active. Only after onboarding completes does the DEV portfolio exist and product versions can be created.

If onboarding fails, select the account and choose **Restart onboarding**. A common cause is an AWS account ID that doesn't exist or hasn't been bootstrapped as a spoke account.

## What this enables

Once a technology has an onboarded DEV account, products created under that technology can have versions published into its portfolio. Continue with:

- [Build your first product](../examples/freertos/README.md) — the full packaging-to-provisioning walkthrough. In Step 4, pick the technology you onboarded here.
- [Launch a product](launch-a-product.md) — provision a product once it's in the catalog.
