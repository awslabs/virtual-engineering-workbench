# Auth0 Logout and VEW User ID Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete Auth0-backed logout for the public CloudFront deployment and include the prepared mapping from an Auth0 app-metadata claim to Cognito `custom:user_tid`.

**Architecture:** Amplify continues to initiate Cognito logout using its generated `redirectSignOut` value. Cognito redirects the browser to Auth0 `/v2/logout`, which clears only the Auth0 session and returns to the generated CloudFront `/login` URL; the existing authentication flow then presents a fresh login. The Auth0 Action publishes the stable VEW ID as a namespaced token claim, and Cognito maps the configured claim into `custom:user_tid`.

**Tech Stack:** Bash, AWS CDK/TypeScript, Amazon Cognito, CloudFront, Auth0 OIDC, Jest.

**Spec:** `docs/superpowers/specs/2026-09-07-auth0-logout-design.md`, plus the approved existing requirement to configure `UserIDClaim` for Auth0 `app_metadata`-backed VEW IDs.

## Global Constraints

- Support only the current public CloudFront deployment; do not add custom-domain or private/ALB behavior.
- Do not modify `frontend/web/src/components/session-management/authenticator.ts`.
- Do not request upstream identity-provider logout; never add Auth0's `federated` parameter.
- Do not modify existing README files.
- Create root-level `CHANGES.md` beside `FINDINGS.md`.
- Preserve unrelated working-tree changes.

---

### Task 1: Verify the prepared Auth0 user-ID mapping

**Files:**
- Modify: `deploy.sh`
- Modify: `frontend/infrastructure/lib/constructs/app-user-pool.ts`
- Test: `frontend/infrastructure/test/infrastructure.test.ts`

**Interfaces:**
- Consumes: deployment values `OIDC_USER_ID_CLAIM`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, and `OIDC_ISSUER_URL`.
- Produces: Secrets Manager JSON field `UserIDClaim`; Cognito mapping from that configured OIDC claim to `custom:user_tid`.

- [x] **Step 1: Inspect the prepared diff without rewriting it**

Confirm that `deploy.sh` requires and persists `OIDC_USER_ID_CLAIM`, writes it to the OIDC secret as `UserIDClaim`, and that `app-user-pool.ts` maps the resolved claim to `custom:user_tid` while mapping `email_verified`.

- [x] **Step 2: Run the focused infrastructure tests**

Run:

```bash
yarn --cwd frontend/infrastructure test --runInBand infrastructure.test.ts
```

Expected: the user-ID and verified-email mapping tests pass. These changes and tests were prepared before this implementation plan, so they are verified as existing work rather than represented as a new red-green cycle.

### Task 2: Add a failing logout URL synthesis test

**Files:**
- Test: `frontend/infrastructure/test/infrastructure.test.ts`

**Interfaces:**
- Consumes: an `AppConfig` with `LogoutUrl` equal to `https://tenant.example/v2/logout?client_id=auth0-client&returnTo={appDns}/login`.
- Produces: a regression assertion on the Cognito `LogoutURLs` property.

- [x] **Step 1: Parameterize the test stack logout configuration**

Change `FEStack.get` to accept an optional logout URL while retaining the existing default for tests that do not exercise Auth0 logout.

- [x] **Step 2: Write the failing CloudFront logout URL test**

Add a test that synthesizes the stack with:

```text
https://tenant.example/v2/logout?client_id=auth0-client&returnTo={appDns}/login
```

Assert that the Cognito client `LogoutURLs` contains an `Fn::Join` whose pieces resolve to:

```text
https://tenant.example/v2/logout?client_id=auth0-client&returnTo=https://<CloudFront DomainName>/login
```

- [x] **Step 3: Run the focused test and verify RED**

Run:

```bash
yarn --cwd frontend/infrastructure test --runInBand infrastructure.test.ts -t "Auth0 logout URL"
```

Expected: FAIL because `app-cdn.ts` currently replaces `{appDns}` with `https://` when no custom domain is configured.

### Task 3: Generate and resolve the Auth0 logout URL

**Files:**
- Modify: `deploy.sh`
- Modify: `frontend/infrastructure/cdk.json`
- Modify: `frontend/infrastructure/lib/constructs/app-cdn.ts`
- Test: `frontend/infrastructure/test/infrastructure.test.ts`

**Interfaces:**
- Consumes: `OIDC_ISSUER_URL`, `OIDC_CLIENT_ID`, and the `{appDns}` placeholder.
- Produces: `context.config.dev.LogoutUrl` and a Cognito allowed logout URL resolved against the generated CloudFront domain.

- [x] **Step 1: Patch deployment configuration generation**

In the OIDC-enabled branch, normalize a trailing slash from `OIDC_ISSUER_URL` and build:

```bash
AUTH0_LOGOUT_URL="${OIDC_ISSUER_URL%/}/v2/logout?client_id=${OIDC_CLIENT_ID}&returnTo={appDns}/login"
```

Extend the existing `jq` update so the OIDC-enabled branch sets both `OIDCSecretName` and `LogoutUrl`. The OIDC-disabled branch must delete both keys so stale Auth0 configuration cannot survive a later non-OIDC deployment.

- [x] **Step 2: Resolve the placeholder against CloudFront only**

In `AppCdn.withCDN`, replace `{appDns}` with:

```typescript
`https://${this._distribution.distributionDomainName}`
```

Do not add or alter custom-domain logic elsewhere.

- [x] **Step 3: Update the checked-in development context**

Add the concrete Auth0 logout template generated from the current non-secret issuer and client ID to `frontend/infrastructure/cdk.json`. Do not add the OIDC client secret.

- [x] **Step 4: Run the focused test and verify GREEN**

Run:

```bash
yarn --cwd frontend/infrastructure test --runInBand infrastructure.test.ts -t "Auth0 logout URL"
```

Expected: PASS.

- [x] **Step 5: Run shell syntax validation**

Run:

```bash
bash -n deploy.sh
```

Expected: exit code 0 with no output.

### Task 4: Document both Auth0 changes

**Files:**
- Create: `CHANGES.md`

**Interfaces:**
- Consumes: the completed user-ID mapping and logout design.
- Produces: operator-facing configuration and verification instructions.

- [x] **Step 1: Create `CHANGES.md` beside `FINDINGS.md`**

Document:

1. The Auth0 Post Login Action that generates a stable VEW ID in `event.user.app_metadata.vew_user_id` on first login and emits it under the configured namespaced claim.
2. The exact claim URI supplied as `OIDC_USER_ID_CLAIM` and its mapping to Cognito `custom:user_tid`.
3. The Auth0 logout chain and the intentional omission of `federated`.
4. The concrete CloudFront `/login` URL that must be added to the Auth0 application's Allowed Logout URLs after deployment.
5. Login and logout smoke-test steps, including verifying that a second login does not silently reuse the Auth0 session.

### Task 5: Full verification

**Files:**
- Verify all files above; do not change unrelated files to make unrelated failures disappear.

**Interfaces:**
- Consumes: all implementation tasks.
- Produces: build and test evidence.

- [x] **Step 1: Run the full infrastructure tests**

```bash
yarn --cwd frontend/infrastructure test --runInBand
```

Expected: all Jest suites pass.

- [x] **Step 2: Build the infrastructure package**

```bash
yarn --cwd frontend/infrastructure build
```

Expected: TypeScript compilation exits 0.

- [x] **Step 3: Build the frontend without modifying its logout implementation**

```bash
yarn --cwd frontend/web build
```

Expected: TypeScript and Vite build exit 0.

- [x] **Step 4: Validate shell and patch hygiene**

```bash
bash -n deploy.sh
git diff --check
```

Expected: both commands exit 0.

- [x] **Step 5: Review the scoped diff**

Confirm that the requested change set modifies only the intended Auth0/logout files plus pre-existing deployment-local changes, that the frontend authenticator is untouched, and that no URL contains `federated`.
