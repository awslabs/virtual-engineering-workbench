# Provisioning service-to-service API

The Provisioning S2S API lets another application launch, inspect, stop and
remove provisioned products without a signed-in user. It is the unattended path:
a CI job can take a product version and give a build a fresh workbench or
virtual target, then remove it when the build ends.

It covers the same operations the portal uses for a project's products. A
launch is still attributed to a VEW user, so the provisioned product appears in
that user's list and counts against their per-user limit.

The examples use these placeholders:

```bash
export CLIENT_ID='<OAuth client ID>'
export CLIENT_SECRET='<OAuth client secret>'
export TOKEN_URL='https://<cognito-domain>/oauth2/token'
export API_BASE_URL='https://<api-host>'
export PROJECT_ID='proj-example'
export USER_NAME='JDOE'
```

Do not put client credentials in source control or Terraform state.

## Scopes

Every operation requires one scope, and API Gateway rejects a token without it.

| Scope | Operations |
| --- | --- |
| `clients/provisioning/product.read` | List the products available to a project; list a product's versions |
| `clients/provisioning/provisioned_product.read` | List a project's provisioned products; read one |
| `clients/provisioning/provisioned_product.write` | Launch, start, stop, remove |

Request them with the Cognito client-credentials grant:

```bash
ACCESS_TOKEN="$(
  curl --fail --silent --show-error \
    --user "$CLIENT_ID:$CLIENT_SECRET" \
    --header 'Content-Type: application/x-www-form-urlencoded' \
    --data-urlencode 'grant_type=client_credentials' \
    --data-urlencode 'scope=clients/provisioning/product.read clients/provisioning/provisioned_product.read clients/provisioning/provisioned_product.write' \
    "$TOKEN_URL" | jq --raw-output '.access_token'
)"
```

Send the token as `Authorization: Bearer $ACCESS_TOKEN` on every request.

These routes authorize on the scope alone. **An S2S client is scoped to the
deployment, not to a project**: a client holding these scopes may act on any
project in the deployment, and the lifecycle routes act under a service identity
rather than as a user. The Packaging routes are stricter and additionally
require the client to be assigned to the project in the path.

Treat these credentials as deployment-wide. Where separate teams must not reach
each other's projects, the boundary is a separate deployment, not a separate
client. See [Authorization model](authorization-model.md) for all three
authorization paths, and `SECURITY.md` for this as a recorded design decision.

## Operations

| Method | Path under `$API_BASE_URL/clients/provisioning/v1` | Operation |
| --- | --- | --- |
| `GET` | `/projects/{projectId}/products/available` | `GetAvailableProducts` |
| `GET` | `/projects/{projectId}/products/{productId}/versions` | `GetAvailableProductVersions` |
| `POST` | `/projects/{projectId}/products/provisioned` | `LaunchProduct` |
| `GET` | `/projects/{projectId}/products/provisioned` | `GetPaginatedProvisionedProducts` |
| `GET` | `/projects/{projectId}/products/provisioned/{provisionedProductId}` | `GetProvisionedProduct` |
| `PATCH` | `/projects/{projectId}/products/provisioned/{provisionedProductId}/start` | `StartProvisionedProduct` |
| `PATCH` | `/projects/{projectId}/products/provisioned/{provisionedProductId}/stop` | `StopProvisionedProduct` |
| `PUT` | `/projects/{projectId}/products/provisioned/{provisionedProductId}/remove` | `RemoveProvisionedProduct` |

The full contract is in
`backend/app/provisioning/entrypoints/s2s_api/schema/proserve-workbench-s2s-provisioning-api-schema.yaml`.

## An unattended launch, end to end

### 1. Find a product and a version

```bash
curl --fail-with-body --silent \
  --header "Authorization: Bearer $ACCESS_TOKEN" \
  "$API_BASE_URL/clients/provisioning/v1/projects/$PROJECT_ID/products/available"
```

Pick a `productId` from the response, then list its versions:

```bash
export PRODUCT_ID='prod-example'

curl --fail-with-body --silent \
  --header "Authorization: Bearer $ACCESS_TOKEN" \
  "$API_BASE_URL/clients/provisioning/v1/projects/$PROJECT_ID/products/$PRODUCT_ID/versions"
```

A version is published to one stage, so choose the version that matches the
stage you intend to launch in.

### 2. Launch

`productId`, `versionId`, `stage`, `region` and `userName` are required.
`provisioningParameters` carries the parameters the product's template declares,
as `key` and `value` pairs.

```bash
curl --fail-with-body --silent --request POST \
  --header "Authorization: Bearer $ACCESS_TOKEN" \
  --header 'Content-Type: application/json' \
  --data '{
    "productId": "prod-example",
    "versionId": "pv-example",
    "stage": "DEV",
    "region": "us-east-1",
    "userName": "'"$USER_NAME"'",
    "provisioningParameters": [
      { "key": "InstanceType", "value": "m8i.xlarge" }
    ]
  }' \
  "$API_BASE_URL/clients/provisioning/v1/projects/$PROJECT_ID/products/provisioned"
```

The response is `202 Accepted` with the id to poll:

```json
{ "provisionedProductId": "pp-example" }
```

`userName` becomes the owner of the provisioned product. Give it the user's VEW
id in the form the authorization layer uses — upper case, with any `@domain`
removed, the same value as their `custom:user_tid`. The API does not check that
the user exists, so a wrong value produces a product nobody can see in the
portal. The launch counts against that user's limit for this product and stage,
which is five, or six in QA.

### 3. Wait for it to run

A provisioned product reports one of `PROVISIONING`, `STARTING`, `RUNNING`,
`STOPPING`, `STOPPED`, `SHUTTING_DOWN`, `DEPROVISIONING` or `TERMINATED`. Only
the first two mean "still working", so treat every other status as a failed
launch and give the wait a deadline — a job that polls for `RUNNING` alone hangs
for ever when a launch fails.

```bash
export PROVISIONED_PRODUCT_ID='pp-example'
deadline=$(( $(date +%s) + 1800 ))   # 30 minutes

while :; do
  product="$(curl --fail-with-body --silent \
    --header "Authorization: Bearer $ACCESS_TOKEN" \
    "$API_BASE_URL/clients/provisioning/v1/projects/$PROJECT_ID/products/provisioned/$PROVISIONED_PRODUCT_ID")"
  status="$(printf '%s' "$product" | jq --raw-output '.status')"

  case "$status" in
    RUNNING) break ;;
    PROVISIONING|STARTING) ;;
    *)
      printf '%s' "$product" | jq --raw-output '"launch ended in \(.status): \(.statusReason // "no reason given")"' >&2
      exit 1 ;;
  esac

  [ "$(date +%s)" -lt "$deadline" ] || { echo 'timed out waiting for RUNNING' >&2; exit 1; }
  sleep 30
done
```

Matching "still working" rather than listing the terminal states is deliberate:
a status added later stops the job with a clear message instead of leaving it to
poll until the CI runner's own timeout. `statusReason` carries the reason a
launch failed, which is why the failure branch prints it.

### 4. Stop or remove it

Stopping keeps the storage and ends the compute charges; removing terminates it.

```bash
# stop, keeping the instance's storage
curl --fail-with-body --silent --request PATCH \
  --header "Authorization: Bearer $ACCESS_TOKEN" \
  "$API_BASE_URL/clients/provisioning/v1/projects/$PROJECT_ID/products/provisioned/$PROVISIONED_PRODUCT_ID/stop"

# remove, which terminates it and loses anything not stored elsewhere
curl --fail-with-body --silent --request PUT \
  --header "Authorization: Bearer $ACCESS_TOKEN" \
  "$API_BASE_URL/clients/provisioning/v1/projects/$PROJECT_ID/products/provisioned/$PROVISIONED_PRODUCT_ID/remove"
```

A CI job that launches a target for a build should remove it in a step that runs
whether the build passed or failed, or the project's per-user limit fills up
with abandoned products.

## Related

- [Packaging service-to-service API](packaging-s2s-api.md) — the same pattern
  for components, recipes, pipelines and image builds, including how OAuth
  clients are created and assigned to a project.
- [Authorization model](authorization-model.md) — the three authorization paths
  and which check each API applies.
- [Launch a product](launch-a-product.md) — the same workflow in the portal.
