# Git as the source of truth

**Status:** Research

**Last updated:** 2026-09-04

## Desired outcome

Allow teams to manage VEW component definitions, recipes, pipelines, and product templates in a Git repository. Git should provide review history, change approval, rollback, and traceability, while VEW continues to perform domain validation, EC2 Image Builder validation and builds, publishing, and provisioning.

The intended ownership split is:

| System | Authoritative data |
| --- | --- |
| Git | Desired configuration and version intent |
| VEW | Generated identifiers, validation runs, images and AMIs, build logs, publication state, and provisioned workbench state |

## Current state

VEW does not currently provide a working GitHub or Git-backed source-of-truth integration.

The GitHub Enterprise icon in the public and private architecture diagrams represents an example corporate/on-premises service that provisioned workbenches could reach through enterprise network connectivity. It is not a GitHub server deployed by VEW and does not indicate that VEW synchronizes its configuration with GitHub.

Some integration scaffolding exists, but it is incomplete:

- The recipe-version wizard defines optional `getIntegrations` and `getIntegrationComponentList` service methods. The concrete packaging service does not implement them, so the wizard falls back to an empty integration list.
- Recipe and publishing models can carry integration identifiers, and tests commonly use `GitHub` as example data. No production GitHub API client or synchronization implementation was found.
- `/webhooks/github` appears in the REST API authentication allow-list and in `SECURITY.md`, but no matching API route or handler is present. The security documentation also states that GitHub webhook HMAC validation still needs to be implemented.
- The FreeRTOS example performs a normal public `git clone` during an image build. This is a component build dependency, not configuration synchronization.

Relevant source locations:

- `frontend/web/src/components/pages/product-packaging/recipes/shared/recipe-version-wizard/recipe-version-wizard.logic.ts`
- `frontend/web/src/services/API/packaging-api.ts`
- `backend/infra/constructs/backend_app_openapi.py`
- `SECURITY.md`
- `examples/freertos/component.yaml`

## Recommended approach

Use a push-based GitOps workflow for the first implementation:

1. Component YAML, recipe definitions, pipeline definitions, and product templates live in a Git repository.
2. A repository CI workflow validates file structure and schemas on pull requests.
3. After an approved change is merged, CI obtains a short-lived service-to-service access token from Cognito using OAuth 2.0 `client_credentials`.
4. CI calls VEW APIs to create or update the desired resources.
5. VEW executes its existing domain validation and asynchronous Image Builder validation/build workflows.
6. CI reports the VEW resource identifiers and validation/build links. VEW remains the place to inspect operational status and logs.

This approach deliberately uses VEW's API rather than writing to DynamoDB or invoking EC2 Image Builder directly. It therefore retains the meaningful server-side and build-time validation already provided by VEW. Only browser-side form validation is bypassed; equivalent schema checks should be available to CI for fast feedback.

### Why push-based first

A push-based CI workflow is smaller and easier to secure than making VEW clone repositories and reconcile them continuously. It avoids inbound GitHub webhooks, GitHub App installation handling, repository polling, and long-lived Git provider credentials inside VEW.

A pull-based reconciler could be considered later if continuous drift correction or support for multiple Git providers becomes necessary.

## Service-to-service authentication

The existing Cognito `sample-s2s` app client demonstrates the correct authentication mechanism, but it cannot currently perform this synchronization:

- its scopes cover provisioning operations, project access, and publishing reads;
- it has no packaging write scopes; and
- packaging currently has no service-to-service API entry point for component, recipe, or pipeline writes.

The preferred design is a dedicated client, such as `git-sync`, with least-privilege scopes. Candidate scopes are:

- `packaging.component.read` and `packaging.component.write`;
- `packaging.recipe.read` and `packaging.recipe.write`;
- `packaging.pipeline.read` and `packaging.pipeline.write`;
- optional publishing template/product scopes if repository-driven publishing is included.

Repository CI should store the client secret in protected environment secrets, request short-lived tokens only when needed, and use separate clients or credentials per VEW environment. Production synchronization should be restricted to protected branches and approved deployment environments.

## Versioning and reconciliation

VEW resources are versioned and builds are asynchronous, so synchronization must be idempotent and must not create a new version on every CI retry.

A practical scheme is to record the Git repository, path, and commit SHA with each synchronized definition. CI can then:

- skip a resource when the same commit and content digest have already been applied;
- create a new VEW version when normalized content changes;
- update mutable draft metadata only where VEW permits it;
- avoid deleting VEW resources automatically in the initial implementation;
- wait for, or link to, asynchronous validation rather than treating API acceptance as successful validation.

Drift should initially be handled by making Git-managed resources read-only in the UI, or by clearly warning that UI edits will be overwritten by the next synchronization. Bidirectional synchronization is not recommended because conflicting edits would make ownership ambiguous.

## Suggested initial scope

The smallest useful delivery would include:

1. A documented repository layout and schemas for components and recipes.
2. Packaging S2S read/write endpoints that reuse the same application commands and validation paths as the interactive API.
3. A dedicated Cognito resource server/client with least-privilege packaging scopes.
4. An idempotent synchronization command or reusable CI action.
5. Git provenance stored against created VEW versions.
6. CI and backend tests confirming that Git-driven changes receive the same server-side validation as UI-driven changes.

Pipelines and product publishing can follow once component and recipe synchronization is proven. Automatic deletion, webhook ingestion, pull reconciliation, and bidirectional UI synchronization should remain out of the first delivery.

## Open questions

- Should a repository map to one VEW project, or may it contain definitions for several projects?
- Which resource types belong in the first supported schema: components only, components plus recipes, or the full packaging and publishing lifecycle?
- Should Git-managed resources be completely read-only in the VEW UI, or should authorized users be able to create an exportable change?
- Should CI wait for Image Builder validation to finish, or submit work and expose a VEW status link?
- How should repository paths and Git identities map to VEW audit records?
- Is GitHub Actions the only initial CI target, or should the synchronization tool remain provider-neutral for GitLab, Bitbucket, and GitHub Enterprise Server?
