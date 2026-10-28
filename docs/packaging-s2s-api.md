# Packaging service-to-service API

The Packaging S2S API is a thin proof of concept over the existing UI commands for
project-scoped components, recipes, pipelines, and image builds. All resources use
the existing internal IDs and request field names. There are no external-ID
mappings, ETags, or separate reconciliation operations. This document describes
the local contract; it does not claim deployed AWS availability.

## Prerequisites

The OAuth client needs these scopes:

- `clients/packaging/component.read`
- `clients/packaging/component.write`
- `clients/packaging/component.release` to release a validated version

An administrator must also assign the client to every project it may access. OAuth scopes grant an action; a project assignment grants access to a particular project. Requests need both.

The examples use these placeholders:

```bash
export CLIENT_ID='<OAuth client ID>'
export CLIENT_SECRET='<OAuth client secret>'
export TOKEN_URL='https://<cognito-domain>/oauth2/token'
export API_BASE_URL='https://<api-host>'
export PROJECT_ID='proj-example'
```

Do not put client credentials in source control or Terraform state.

## Obtain an access token

Request the scopes needed by the workflow with the Cognito client-credentials grant:

```bash
ACCESS_TOKEN="$(
  curl --fail --silent --show-error \
    --user "$CLIENT_ID:$CLIENT_SECRET" \
    --header 'Content-Type: application/x-www-form-urlencoded' \
    --data-urlencode 'grant_type=client_credentials' \
    --data-urlencode 'scope=clients/packaging/component.read clients/packaging/component.write clients/packaging/component.release' \
    "$TOKEN_URL" | jq --raw-output '.access_token'
)"
```

Send the token as `Authorization: Bearer $ACCESS_TOKEN` on every API request.

For recipes and pipelines, request the explicitly granted scopes described below.
Poll each resource's GET endpoint for lifecycle status.

## OAuth clients and project access

Deploying the backend CDK `IntegrationOauthStack` creates the Cognito app clients
and generates their client IDs and secrets. Client creation is separate from
granting those clients access to a project. The stack provisions one set of
clients per deployed environment; the same clients can be assigned to multiple
projects.

| Client | Projects scopes | Packaging scopes |
| --- | --- | --- |
| `projects-assignment-management` | `program.read`, `program.write`, `client_assignment.read`, `client_assignment.write` | None |
| `sample-s2s` | Existing read and other Projects scopes, without `client_assignment.write` or bootstrap | Packaging operation scopes |
| `platform-projects-bootstrap` | `client_assignment.read`, `client_assignment.write`, `client_assignment.bootstrap` | None |

Projects scopes in the table use the `clients/projects/` prefix. Configure
separate Terraform provider aliases or API callers with the management and
Packaging credentials. The provider consumes existing credentials; it does not
create these Cognito app clients.

### Assign the Packaging client

Use the dedicated `projects-assignment-management` OAuth client with
`clients/projects/client_assignment.write` and an existing `ACTIVE` assignment to
the target project to create or reactivate assignments. This client has
project and assignment read/write scopes and no Packaging scopes. The
`sample-s2s` client retains its Packaging scopes and no longer has
assignment-write access.

A client must never hold both `clients/projects/client_assignment.write` and
any `clients/packaging/*` scopes. Use separate credentials for assignment
management and Packaging operations, including for custom clients.

The `clientId` path value is the client ID contained in the Packaging access
token. It must differ from the calling management client's token `client_id`.
Self-assignment PUT requests return HTTP `403`, even when the caller already
has an active assignment or holds the bootstrap scope.

```bash
curl --fail-with-body --request PUT \
  --header "Authorization: Bearer $MANAGEMENT_ACCESS_TOKEN" \
  "$API_BASE_URL/clients/projects/v1/projects/$PROJECT_ID/clients/$CLIENT_ID"
```

The response reports `ACTIVE`. A Packaging request for an unassigned project returns `403 PROJECT_ACCESS_DENIED` before Packaging looks up the requested resource. Deleting the same Projects URL revokes the assignment.

Reading and revoking assignments also require an `ACTIVE` caller assignment to
the target project, plus `client_assignment.read` or `client_assignment.write`,
respectively.

### Project-creation scope compatibility

The CDK stack defines `clients/projects/program.write` and grants it to the
management client together with `clients/projects/program.read`. This prepares
the credentials for deployments that support Projects S2S project creation.
The Projects S2S API in this branch currently exposes project listing;
project-creation endpoints and automatic creator assignments are outside this
upstream change. The scopes alone do not add those endpoints or assign the
manager to an existing project.

For deployments with project creation and automatic creator assignments, create
the project using the management client's `program.write` scope. The resulting
creator assignment lets the manager grant access to the Packaging client
without a self-assignment PUT or bootstrap credentials. Use management
credentials for project and client-assignment operations, and Packaging
credentials after its project assignment is active. An active assignment for
the Packaging client alone prevents orphan-project bootstrap from adding the
manager later.

### Recover an existing orphaned project

For orphan-project recovery, obtain a token from the separate
`platform-projects-bootstrap` client requesting both
`clients/projects/client_assignment.write` and
`clients/projects/client_assignment.bootstrap`. Use that token to assign the
management client's ID to an existing project with no active service-client
assignments. Then use the management client's token to assign the Packaging
client. The bootstrap client cannot assign itself, and it has no Packaging
scopes. The successful bootstrap PUT does not give the recovery caller access
to read or revoke assignments. Use the now-assigned management client's
credentials for subsequent reads, grants, and revocations.

Projects with active service clients require an already assigned client with
`clients/projects/client_assignment.write` to grant the manager access;
bootstrap cannot bypass that restriction. When migrating an existing
deployment, provision the manager in a staged deployment that retains the old
Packaging client's assignment-write scope, and use the assigned old client to
grant the manager access. Verify the manager's access, then switch assignment
operations to its credentials and deploy the scope separation.

## Component POC

Paths below are relative to `/clients/packaging/v1/projects/{projectId}`.
Components and their versions use the same generated `componentId` and
`componentVersionId` as the UI. Existing UI-created resources are accessible
through these IDs when associated with the authorized project.

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` / `GET` | `/components` | Create / list components |
| `GET` / `PUT` / `DELETE` | `/components/{componentId}` | Read, update description, or archive |
| `POST` / `GET` | `/components/{componentId}/versions` | Create / list versions |
| `GET` / `PUT` / `DELETE` | `/components/{componentId}/versions/{versionId}` | Read, update, or retire a version |
| `POST` | `/components/{componentId}/versions/{versionId}/release` | Release a validated version |

Create a component with `POST /components`:

```json
{
  "componentName": "build-agent",
  "componentDescription": "Installs the build agent",
  "componentPlatform": "Linux",
  "componentSupportedArchitectures": ["amd64"],
  "componentSupportedOsVersions": ["Ubuntu 24"]
}
```

The response is `201` with `{"componentId": "comp-..."}`. Use that ID for subsequent
requests. `PUT /components/{componentId}` accepts only `componentDescription`.
Update and archive return `200` with `{}`. GET returns `{component: ...}`; list
returns `{components: [...]}`.

Create a version with `POST /components/{componentId}/versions` using the existing
UI fields:

```json
{
  "componentVersionDescription": "Install the build agent",
  "componentVersionReleaseType": "MAJOR",
  "componentVersionYamlDefinition": "<valid Image Builder component YAML>",
  "componentVersionDependencies": [],
  "softwareVendor": "Example Corp",
  "softwareVersion": "1.0.0"
}
```

Optional metadata fields are `licenseDashboard` and `notes`. Dependency entries
use the UI's `componentId`, `componentName`, `componentVersionId`,
`componentVersionName`, `componentVersionType`, `order`, and `position` fields;
use internal IDs for dependencies too. Dependencies must be available in the
authorized project.

Create/update/retire returns `202` with `componentVersionId` and `Retry-After: 5`.
Poll the version GET and inspect `component_version.status`: wait for
`VALIDATED` or `FAILED` after create/update, or `RETIRED` or `FAILED` after
retirement. The response includes `yaml_definition` and `yaml_definition_b64`
when a stored definition is available. Version lists return `{component_versions: [...]}`.

Version update accepts the same fields except `componentVersionReleaseType`,
which is creation-only. Once validated, send a bodyless POST to the release
endpoint. It returns `200` with `componentVersionId`; the existing domain
workflow assigns the final semantic version. Released content is immutable:
create a new version for further edits. DELETE archives the base or retires a
version through the existing lifecycle; it does not physically delete records.

Component POST requests are non-idempotent. If a response is lost, inspect the
component/version lists before retrying. There are no external-ID, conditional
update, or reconciliation deduplication guarantees in this POC. No existing
component/version IDs need migration.

## Recipe POC

Recipe access requires a project assignment and one of these explicitly granted
scopes:

- `clients/packaging/recipe.read` for reads and lists
- `clients/packaging/recipe.write` for create, update, and delete/retire actions
- `clients/packaging/recipe.release` for release

Existing clients are not automatically granted recipe scopes. The POC keeps the
existing UI request field names and uses internal IDs; it does not accept or create
external recipe/version IDs, ETags, or recipe mapping records.

The routes are:

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` / `GET` | `/clients/packaging/v1/projects/{projectId}/recipes` | Create a recipe / list recipes |
| `GET` / `DELETE` | `/clients/packaging/v1/projects/{projectId}/recipes/{recipeId}` | Read / archive a recipe |
| `POST` / `GET` | `/clients/packaging/v1/projects/{projectId}/recipes/{recipeId}/versions` | Create a version / list versions |
| `GET` / `PUT` / `DELETE` | `/clients/packaging/v1/projects/{projectId}/recipes/{recipeId}/versions/{versionId}` | Read, update, or retire a version |
| `POST` | `/clients/packaging/v1/projects/{projectId}/recipes/{recipeId}/versions/{versionId}/release` | Release a version |

Recipe creation uses the UI fields `recipeName`, `recipeDescription`,
`recipePlatform`, `recipeArchitecture`, and `recipeOsVersion`. Version requests use
the UI fields `recipeVersionDescription`, `recipeVersionReleaseType`,
`recipeVersionVolumeSize`, `recipeVersionIntegrations`, and
`recipeComponentsVersions`; each component entry must include the internal IDs,
the UI names, `componentVersionType`, and `order`:

```json
{
  "recipeVersionDescription": "Engineering image components",
  "recipeVersionReleaseType": "MINOR",
  "recipeVersionVolumeSize": "30",
  "recipeVersionIntegrations": [],
  "recipeComponentsVersions": [
    {
      "componentId": "comp-0001",
      "componentName": "build-agent",
      "componentVersionId": "vers-0001",
      "componentVersionName": "1.0.0",
      "componentVersionType": "HELPER",
      "order": 1
    }
  ]
}
```

Components are sorted by `order`; existing mandatory components are added by the
domain workflow. `recipeVersionReleaseType` is accepted only when the
version is created; it is not an update field. A successful recipe create returns
`recipeId`; a version create/update/retire action returns `recipeVersionId`.
`DELETE` archives the recipe base or retires the version; it never physically
deletes the underlying UI resource.

Version create, update, and retire actions return `202 Accepted` with a
`recipeVersionId` and `Retry-After: 5`. Poll
`GET /clients/packaging/v1/projects/{projectId}/recipes/{recipeId}/versions/{versionId}`
until `recipe_version.status` becomes `VALIDATED` or `FAILED` after create/update,
or `RETIRED` or `FAILED` after retirement. Release requires a validated version
whose component versions are all released, and returns the `recipeVersionId`
synchronously. Released content is immutable. This POC reuses the existing build
and test workflows without adding a separate recipe operation reconciler.

Retry caveat: recipe `POST` requests are non-idempotent. If the response is lost,
check the recipe/version list first and inspect the returned internal IDs before
submitting another create. There are no external IDs, ETags, or operation-reconciler
deduplication guarantees for recipes in this POC. Use the stable problem `code` and
`retryable` fields for errors, but do not blindly replay a non-idempotent create.

## Pipeline and image-build POC

All paths below are relative to `/clients/packaging/v1/projects/{projectId}`.
The client must be assigned to that project and explicitly granted the relevant scopes:

- `clients/packaging/pipeline.read`: pipeline and image reads/lists.
- `clients/packaging/pipeline.write`: create, update, and retire pipelines.
- `clients/packaging/pipeline.execute`: start an image build.

These scopes are not automatically granted to existing clients. There are no
external pipeline IDs, ETags, or pipeline reconciliation operations.

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` / `GET` | `/pipelines` | Create / list pipelines |
| `GET` / `PUT` / `DELETE` | `/pipelines/{pipelineId}` | Read / update / retire a pipeline |
| `POST` / `GET` | `/images` | Start a build / list images |
| `GET` | `/images/{imageId}` | Read image build status and resulting AMI ID |

Create a pipeline using the existing internal IDs of a released recipe version:

```json
{
  "pipelineName": "engineering-image",
  "pipelineDescription": "Build the engineering image",
  "recipeId": "reci-example",
  "recipeVersionId": "vers-example",
  "buildInstanceTypes": ["m8i.2xlarge"],
  "pipelineSchedule": "0 0 * * ? *"
}
```

Use build instance types allowed by the deployment's pipeline configuration for the
recipe architecture. The schedule is a six-field expression, without a `cron(...)`
wrapper, matching the UI. Optional `productId` retains the UI's automatic product
version association behavior.

Create/update/retire returns `202` with `pipelineId`. Poll the pipeline GET until
`pipeline.status` is `CREATED` or `FAILED` after create/update, or `RETIRED` or
`FAILED` after retirement. Updates accept `buildInstanceTypes`, `pipelineSchedule`,
`recipeVersionId`, and `productId`; the recipe itself, pipeline name, and description
are not mutable through the existing command. As in the UI, omitting `productId`
on update clears the product association.

Once the pipeline is `CREATED`, send this to `POST /images`:

```json
{"pipelineId": "pipe-example"}
```

The response is `202` with the existing internal `imageId`. Poll `GET /images/{imageId}`
with `pipeline.read` until `image.status` becomes `CREATED` or `FAILED`.
`image.imageUpstreamId` is the resulting AMI ID when available. Builds still run
through the existing Image Builder and event-processing workflow.

Pipeline creates and image-build requests are not deduplicated. After a lost response,
inspect the project pipeline/image lists before retrying; repeating `POST /images`
can launch another billable build. No deployment or live build has been performed
as part of local verification.

## Errors

Errors use `application/problem+json` and a stable machine-readable `code`:

```json
{
  "type": "https://problems.virtual-engineering-workbench.dev/project-access-denied",
  "title": "Forbidden",
  "status": 403,
  "detail": "The client is not assigned to this project.",
  "code": "PROJECT_ACCESS_DENIED",
  "requestId": "request-id",
  "retryable": false
}
```

Clients should branch on `code`, not `title` or `detail`. Retry transient errors only
when `retryable` is `true`, and inspect current state before replaying any
non-idempotent request.
