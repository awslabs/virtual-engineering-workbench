# Marketplace rollback runbook

How to roll back a deploy that broke the AWS Marketplace features of the packaging module (browse, subscribe, agreements, Import AMI from Marketplace). The procedures apply to any packaging deploy, not only Marketplace changes.

A rollback is only fast if you recorded the known-good state around the deploy. Do [Record state with every deploy](#record-state-with-every-deploy) each time.

## Conventions

Replace these placeholders. All commands are AWS CLI v2 and assume credentials for the hub account.

| Placeholder | Meaning |
|---|---|
| `<env>` | Deployment environment, for example `dev` (the `ENVIRONMENT` in `.deploy-config-<env>`). |
| `<region>` | Region of the backend stacks (`AWS_REGION` in `.deploy-config-<env>`). |
| `<fe-region>` | Region of the UI stack. `deploy.sh` uses `us-east-1` for public deployments and `<region>` for private ones. |
| `<hub-account-id>` | The hub (web application) account ID. Confirm it with `aws sts get-caller-identity` before you change anything. |
| `<ui-bucket>` | The UI bucket: output `icfrontends3output` of stack `proserve-wb-ui-<env>`. |
| `<distribution-id>` | The CloudFront distribution: output `cdndistributionidoutput` of stack `proserve-wb-ui-<env>`. |
| `<rest-api-id>` | The packaging REST API ID (see [API Gateway rollback](#api-gateway-rollback)). |
| `<release-bucket>` | A bucket you own for frontend release archives. **Not** `<ui-bucket>`; see [Archive the frontend build](#2-archive-the-frontend-build). |
| `<known-good-sha>` | The git commit that was deployed and working before the bad deploy. |

Set up the shell once per session:

```bash
export AWS_PROFILE=<hub-profile>
ENV=<env>
REGION=<region>
FE_REGION=<fe-region>
STACK="proserve-wb-packaging-${ENV}"
aws sts get-caller-identity --query Account --output text   # must print <hub-account-id>
```

Look up the UI bucket and distribution:

```bash
UI_BUCKET=$(aws cloudformation describe-stacks --stack-name "proserve-wb-ui-${ENV}" --region "$FE_REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='icfrontends3output'].OutputValue | [0]" --output text)
DISTRIBUTION_ID=$(aws cloudformation describe-stacks --stack-name "proserve-wb-ui-${ENV}" --region "$FE_REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='cdndistributionidoutput'].OutputValue | [0]" --output text)
echo "$UI_BUCKET $DISTRIBUTION_ID"
```

## Symptom triage

| Symptom | Likely layer | Go to |
|---|---|---|
| Subscribe wizard shows "AWS Marketplace rejected the agreement request ..." or another new error | Packaging API Lambda | [Backend rollback](#backend-rollback) |
| Import AMI shows no Marketplace subscriptions although the account has active agreements | Packaging API Lambda | [Backend rollback](#backend-rollback) |
| API returns 500 with no useful body | Packaging API Lambda | [Backend rollback](#backend-rollback), then check the logs |
| Agreement lifecycle events fail or pile up in the DLQ | `marketplace-agreement-events` Lambda | [Event-driven Lambdas](#event-driven-lambdas) |
| CORS preflight fails, or authorizer or throttling errors after a deploy | API Gateway stage | [API Gateway rollback](#api-gateway-rollback) |
| Blank page, stale bundle, or a broken wizard with healthy APIs | Frontend | [Frontend rollback](#frontend-rollback) |
| Cognito login broken | UI stack (Cognito) | Not covered here. Do not run a teardown to fix it. |

## Record state with every deploy

Record the backend version map before the deploy, while the environment still runs the known-good version, and archive the frontend build after each successful deploy. Keep the files with the deploy record.

### 1. Record the backend version map

Every packaging Lambda has an alias named `live_v2` (`LAMBDA_ALIAS_NAME` in `backend/infra/constants.py`; it is not configurable per deploy). CDK publishes a new version on each code change and moves the alias to it. Record where each alias points now, one row per Lambda:

```bash
SHA=<known-good-sha>
mkdir -p rollback
MAP="rollback/packaging-${ENV}-${SHA}.tsv"
: > "$MAP"
for fn in $(aws cloudformation list-stack-resources --stack-name "$STACK" --region "$REGION" \
    --query "StackResourceSummaries[?ResourceType=='AWS::Lambda::Function'].PhysicalResourceId" \
    --output text); do
  version=$(aws lambda list-aliases --function-name "$fn" --region "$REGION" \
    --query "Aliases[?Name=='live_v2'].FunctionVersion | [0]" --output text </dev/null)
  printf '%s\t%s\n' "$fn" "$version" >> "$MAP"
done
cat "$MAP"
```

The function list comes from the stack, so it stays correct when Lambdas are added or removed. Functions that CDK creates for its own custom resources have no `live_v2` alias; their rows show `None` and the rollback skips them.

Also record the API Gateway stage's current deployment, for each REST API in the stack:

```bash
for api in $(aws cloudformation list-stack-resources --stack-name "$STACK" --region "$REGION" \
    --query "StackResourceSummaries[?ResourceType=='AWS::ApiGateway::RestApi'].PhysicalResourceId" \
    --output text); do
  dep=$(aws apigateway get-stage --rest-api-id "$api" --stage-name v1 --region "$REGION" \
    --query deploymentId --output text </dev/null)
  printf 'apigw\t%s\t%s\n' "$api" "$dep" >> "rollback/apigw-${ENV}-${SHA}.tsv"
done
```

### 2. Archive the frontend build

`deploy.sh` builds `frontend/web/dist` and uploads it with `aws s3 sync ... --delete`, which removes every object in `<ui-bucket>` that is not in the new build, including the previous release's hashed bundles. The bucket has no object versioning (the CDK in `frontend/infrastructure/lib/constructs/app-cdn.ts` does not enable it), so after a deploy the previous release is gone from S3. Keep a copy of every release you deploy.

Right after a successful deploy, while `frontend/web/dist` still holds the build that was uploaded, archive it under the deployed commit:

```bash
SHA=$(git rev-parse HEAD)
aws s3 cp frontend/web/dist "s3://<release-bucket>/vew-ui/${ENV}/${SHA}/" --recursive --region "$REGION"
```

Or keep it locally:

```bash
mkdir -p "rollback/ui-${ENV}-${SHA}"
cp -R frontend/web/dist/. "rollback/ui-${ENV}-${SHA}/"
```

Do not archive into `<ui-bucket>` itself, for example under `releases/`. The next `deploy.sh` run deletes that prefix with `--delete`, and CloudFront would serve old builds from it in the meantime.

The build is specific to its environment: `configure_auth.sh` writes the Cognito and API settings into `src/aws-exports.js`, which Vite compiles into the bundle. Restore an archive only to the environment it was built for.

## Backend rollback

### Packaging API Lambdas

The packaging REST APIs invoke their Lambdas (`proserve-wb-packaging-api-<env>` and `proserve-wb-packaging-s2s-api-<env>`) through the `live_v2` alias. Pointing the alias back at the recorded version rolls back the code those APIs run:

```bash
MAP=rollback/packaging-<env>-<known-good-sha>.tsv
while IFS=$'\t' read -r fn version; do
  [ "$version" = "None" ] && continue
  echo "$fn: live_v2 -> $version"
  aws lambda update-alias --function-name "$fn" --name live_v2 \
    --function-version "$version" --region "$REGION" --output text --query FunctionVersion </dev/null
done < "$MAP"
```

`update-alias` takes effect immediately. Requests in flight finish on the old version, and new requests use the new target. No API Gateway change is needed.

Verify that every alias matches the map:

```bash
while IFS=$'\t' read -r fn version; do
  [ "$version" = "None" ] && continue
  current=$(aws lambda get-alias --function-name "$fn" --name live_v2 --region "$REGION" \
    --query FunctionVersion --output text </dev/null)
  if [ "$current" = "$version" ]; then echo "OK   $fn $current"; else echo "DIFF $fn $current (want $version)"; fi
done < "$MAP"
```

The next CDK deploy of the packaging stack moves the aliases forward again. Fix forward or redeploy `<known-good-sha>` before the next regular deploy.

If you have no version map, list the published versions of the function and choose by date and code hash (the version description holds the first five characters of the asset hash):

```bash
aws lambda list-versions-by-function --function-name "proserve-wb-packaging-api-${ENV}" --region "$REGION" \
  --query "Versions[?Version!='\$LATEST'].[Version,LastModified,Description]" --output table
```

Pick the version that was live before the bad deploy. Never point an alias at `$LATEST`; that is the unpublished, mutable code.

### Event-driven Lambdas

The other packaging Lambdas, including `proserve-wb-packaging-marketplace-agreement-events-<env>`, are invoked by EventBridge rules, Step Functions and schedules **without a qualifier**. They run `$LATEST`, so moving their alias changes nothing. To roll them back, redeploy the backend from the known-good commit:

```bash
git worktree add ../vew-rollback <known-good-sha>
cd ../vew-rollback
./deploy.sh --config /path/to/.deploy-config-<env>
```

`deploy.sh` writes `.deploy-config-<env>` next to itself in the original checkout; pass that file. Its phases are idempotent, so unchanged stacks are no-ops.

While the agreement-events Lambda is broken, failed events wait in its dead-letter queue `proserve-wb-packaging-marketplace-agreement-events-<env>-dlq` after their retries. Check the queue depth:

```bash
DLQ_URL=$(aws sqs get-queue-url --queue-name "proserve-wb-packaging-marketplace-agreement-events-${ENV}-dlq" \
  --region "$REGION" --query QueueUrl --output text)
aws sqs get-queue-attributes --queue-url "$DLQ_URL" --attribute-names ApproximateNumberOfMessages --region "$REGION"
```

Nothing in VEW consumes the republished agreement events today, so a backlog delays no user-visible behaviour. If the Lambda is failing loudly, you can stop deliveries by disabling its rule. Events that arrive while the rule is disabled are not delivered later.

```bash
aws events disable-rule --name "proserve-wb-packaging-marketplace-agreement-event-rule-${ENV}" --region "$REGION"
# after the fix:
aws events enable-rule --name "proserve-wb-packaging-marketplace-agreement-event-rule-${ENV}" --region "$REGION"
```

AWS publishes Marketplace agreement events only in `us-east-1`, and the Lambda refuses to start in any other region, so this path only matters when `<region>` is `us-east-1`.

## API Gateway rollback

Use this for CORS, throttling or authorizer regressions after a stage was redeployed. Point stage `v1` back at the deployment you recorded:

```bash
aws apigateway update-stage --rest-api-id <rest-api-id> --stage-name v1 --region "$REGION" \
  --patch-operations op=replace,path=/deploymentId,value=<recorded-deployment-id>
```

Without a record, list the deployments and pick the one that was live before the bad deploy:

```bash
aws apigateway get-deployments --rest-api-id <rest-api-id> --region "$REGION" \
  --query "items[].[id,createdDate,description]" --output table
```

To find `<rest-api-id>`:

```bash
aws cloudformation list-stack-resources --stack-name "$STACK" --region "$REGION" \
  --query "StackResourceSummaries[?ResourceType=='AWS::ApiGateway::RestApi'].[LogicalResourceId,PhysicalResourceId]" \
  --output table
```

## Frontend rollback

### From the archive

Copy the archived release back into the bucket, then invalidate CloudFront:

```bash
aws s3 cp "s3://<release-bucket>/vew-ui/${ENV}/<known-good-sha>/" "s3://${UI_BUCKET}/" --recursive --region "$FE_REGION"
# or, from a local archive:
aws s3 cp "rollback/ui-${ENV}-<known-good-sha>/" "s3://${UI_BUCKET}/" --recursive --region "$FE_REGION"

aws cloudfront create-invalidation --distribution-id "$DISTRIBUTION_ID" --paths "/*"
```

Use `cp --recursive`, not `sync`. `sync` skips a file whose size matches and whose destination copy is newer, and two `index.html` files from different builds often have the same size, because Vite's hashed file names have a fixed length. `sync` would then leave the bad `index.html` in place.

Do not add `--delete`. Without it, the bad release's hashed assets stay in the bucket next to the restored ones, and `index.html` decides which bundle loads. That leaves you able to roll forward again by restoring the newer archive.

The invalidation usually reaches all edge locations within a few minutes.

### Rebuild from git (fallback)

If no archive exists, rebuild the known-good commit from a full checkout. Do not check out only `src/`: `package.json`, `yarn.lock` and `vite.config.ts` must match the commit too.

```bash
git worktree add ../vew-ui-rollback <known-good-sha>
cd ../vew-ui-rollback/frontend/web
yarn install --immutable
APP_NAME=proserve-wb-ui BACKEND_APP_NAME=proserve-wb ENVIRONMENT_NAME="$ENV" \
  AWS_DEFAULT_REGION="$FE_REGION" AWS_REGION_BE_API="$REGION" UPLOAD_ENV=remote \
  bash configure_auth.sh
REACT_APP_ENVIRONMENT="$ENV" yarn build
aws s3 cp dist "s3://${UI_BUCKET}/" --recursive --region "$FE_REGION"
aws cloudfront create-invalidation --distribution-id "$DISTRIBUTION_ID" --paths "/*"
```

These are the same settings `deploy.sh` uses in its frontend phase. Two of them are easy to get wrong:

- `UPLOAD_ENV=remote` is required. Without it, `configure_auth.sh` sets the Cognito redirect URLs to `http://localhost:3000` and login fails.
- `REACT_APP_ENVIRONMENT` is required. `vite.config.ts` compiles it into the bundle. A build without it produces a page that never renders, while every stack, API and asset looks healthy.

Remove the worktree afterwards with `git worktree remove ../vew-ui-rollback`.

### Recommended follow-up

Enable versioning on the UI bucket (`versioned: true` on the `frontend-bucket` construct in `app-cdn.ts`). With versioning, a `--delete` sync no longer destroys the previous release, and an archive becomes a second line of defence instead of the only one. Check the actual setting of your bucket with:

```bash
aws s3api get-bucket-versioning --bucket "$UI_BUCKET"
```

Note that the bucket is created with `RemovalPolicy.DESTROY` and `autoDeleteObjects: true`, so deleting the UI stack empties it.

## Full teardown and redeploy

Last resort, only with approval from whoever owns the environment:

```bash
./deploy.sh --config .deploy-config-<env> --destroy
git checkout <known-good-sha>
./deploy.sh --config .deploy-config-<env> --yes
```

What teardown destroys depends on the environment's removal policies. In `dev` the Cognito user pool is deleted with all its users; other environments retain it. The DynamoDB tables (images, recipes, imports and every other record) are deleted unless the environment config sets `retain_resources`. The CloudFront distribution is recreated, so the URL changes. Marketplace agreements are AWS account resources and survive. Expect at least 30 to 60 minutes to recover.

## Recovery checklist

After any rollback:

1. The alias check in [Packaging API Lambdas](#packaging-api-lambdas) prints `OK` for every row.
2. `index.html` loads and references the expected bundle:

   ```bash
   curl -sS -o /dev/null -w '%{http_code}\n' "https://<cloudfront-domain>/index.html"
   curl -sS "https://<cloudfront-domain>/index.html" | grep -oE 'assets/index-[A-Za-z0-9_-]+\.js'
   grep -oE 'assets/index-[A-Za-z0-9_-]+\.js' "rollback/ui-${ENV}-<known-good-sha>/index.html"
   ```

   The first command prints `200`. The second and third print the same file name.
3. You can log in, and **Marketplace → Browse catalog** shows listings.
4. **Marketplace → Agreements** loads. Its request, `GET /marketplace/agreements` on the packaging API, returns 200 (check the browser's network tab).
5. One Marketplace flow behaves like the known-good version, for example a subscribe attempt on an offer the account already has, which must be refused with the "already have an active subscription" message.
6. The API Lambda logs show no new errors for 10 minutes:

   ```bash
   aws logs tail "/aws/lambda/proserve-wb-packaging-api-${ENV}" --since 10m --region "$REGION" \
     | grep -E 'ERROR|Task timed out'
   ```

## After a rollback

- Record the failure mode and the fix in the incident or bug ticket.
- If the agreement-events DLQ has messages, inspect them and replay them once the Lambda is fixed.
- Check for `MarketplaceEventPublishFailed` metrics in the window: each one is an AWS write (quote, accept or cancel) that succeeded without its domain event. The ERROR log entry next to it names the agreement.

## Related docs

- [Use AWS Marketplace images](../marketplace-integration.md): what the Marketplace features do, the routes, IAM and limitations.
- [Deploy notes](../deploy-notes.md): practical notes on running `deploy.sh`.
