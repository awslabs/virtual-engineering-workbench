# Deployment Findings

This document records issues discovered while deploying the Virtual Engineering Workbench. It is intended as a running troubleshooting log, not as confirmation that the proposed remediations have been implemented.

Last updated: 2026-09-07

## 1. Public frontend deploy uses the backend region for edge resources

**Status:** Confirmed; not fixed.

**Observed failure:**

```text
AWS::WAFv2::WebACL ... The scope is not valid ... parameter: CLOUDFRONT
```

**Cause:**

`deploy.sh` passes the configured `AWS_REGION` to the frontend CDK app as `region`. The public `InfrastructureStack` always creates a WAF ACL with `scope: CLOUDFRONT`, so a deployment configured for `eu-north-1` attempts to create that ACL in `eu-north-1`.

AWS requires CloudFront-scoped WAF resources to be created in `us-east-1`. Bootstrapping `us-east-1` does not change the deployment region of a stack; it only installs the CDK bootstrap resources in that region.

The CDK app supports a separate `be-region` context, but the deployment script does not currently pass it.

**Relevant code:**

- `deploy.sh`: frontend context sets `region=$AWS_REGION`.
- `frontend/infrastructure/bin/infrastructure.ts`: assigns `region` to `InfrastructureStack` and reads the optional `be-region` context.
- `frontend/infrastructure/lib/constructs/waf/waf-infrastructure.ts`: creates the CloudFront ACL with `scope: CLOUDFRONT`.

**Remediation options:**

1. With the current combined public frontend stack, deploy it in `us-east-1` and pass the backend region separately as `be-region=eu-north-1`.
2. Split the public frontend into regional and edge stacks. S3, Cognito, and the Cognito regional WAF can remain in `eu-north-1`; the CloudFront WAF, Lambda@Edge, and CloudFront certificate resources must be managed through `us-east-1`.
3. Use the private deployment flow if private/VPN-only access is appropriate. This avoids CloudFront and Lambda@Edge, allowing the frontend resources to remain regional.

**Important distinction:**

Cognito itself is not restricted to `us-east-1`. The current stack must deploy there because it combines regional frontend resources with CloudFront-specific edge resources in one regional CloudFormation stack.

## 2. Lambda concurrency quota is too low in `us-east-1`

**Status:** Confirmed; quota increase required or code must stop reserving concurrency.

**Observed failure:**

```text
Specified ReservedConcurrentExecutions for function decreases account's
UnreservedConcurrentExecution below its minimum value of [10].
```

**Cause:**

The target account currently has a Lambda `Concurrent executions` quota of 10 in `us-east-1`, with all 10 executions unreserved.

This is a new AWS account. AWS applies reduced Lambda concurrency and memory quotas to new accounts and raises them automatically as usage is established. The reduced limit is therefore an account maturity restriction, not a VEW-specific AWS configuration error. See [AWS Lambda quotas](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html).

The frontend stack requests:

- 10 reserved executions for the Cognito post-authentication trigger.
- 1 reserved execution for the Lambda@Edge monitoring configurator.

Lambda requires capacity to remain in the unreserved pool. With a total quota of 10, any positive reserved concurrency allocation fails. The stack requires at least 21 total executions to satisfy its current reservations and retain the observed minimum of 10 unreserved executions. The requested quota of 1,000 provides practical headroom and matches AWS's normal documented default.

**Relevant code:**

- `frontend/infrastructure/lib/constructs/app-user-pool.ts`: `reservedConcurrentExecutions: 10`.
- `frontend/infrastructure/lib/constructs/cloudwatch/lambda-edge-monitoring.ts`: `reservedConcurrentExecutions: 1`.

**Recommended remediation:**

Request an increase for AWS Lambda's `Concurrent executions` quota. The Service Quotas identifier is `L-B99A9384`. The console requires a requested quota value of at least 1,000, which is also AWS's normal documented default.

Lambda concurrent-execution quotas apply per account and per region. This deployment therefore needs separate requests for:

- `us-east-1`, for the public frontend and edge-supporting Lambdas.
- `eu-north-1`, for the backend Lambdas.

Requesting a quota increase and configuring reserved concurrency do not themselves incur charges; normal Lambda invocation and duration charges still apply.

Example request:

```bash
aws service-quotas request-service-quota-increase \
  --service-code lambda \
  --quota-code L-B99A9384 \
  --desired-value 1000 \
  --region us-east-1 \
  --profile <hub-profile>
```

## 3. Teardown command is broad and may miss failed stacks

**Status:** Confirmed by script review; not fixed.

The script provides:

```bash
./deploy.sh --destroy --config .deploy-config-dev
```

This is not a frontend-only teardown. It targets all CloudFormation stacks whose names begin with `${ORG_PREFIX}-${APP_PREFIX}` in the configured `AWS_REGION`, then attempts to clean matching log groups, ECR repositories, and S3 buckets.

**Problems:**

- It searches CloudFormation only in the configured region, so a teardown configured for `eu-north-1` will not remove a frontend stack deployed in `us-east-1`.
- Its stack-status filter omits `ROLLBACK_COMPLETE`, which is a common status after a failed initial deployment. It can therefore miss the failed stack that prompted the teardown.
- Its prefix matching can include working backend stacks, making it unsafe as a targeted frontend cleanup command.
- The destroy path calls `activate_hub_credentials` before that function is defined in the script and suppresses the resulting error. It may therefore continue using whichever AWS credentials are already active.

**Recommended remediation:**

Provide explicit, region-aware teardown targets for frontend, backend, and failed stacks. Include failed stack states such as `ROLLBACK_COMPLETE`, and validate the active AWS account before deleting anything.

## 4. Failed frontend rollbacks can retain orphaned resources

**Status:** Observed in deployment logs.

During failed stack creation, CloudFormation reported `DELETE_SKIPPED` for WAF log groups and an S3 access-log bucket. These resources can remain after the stack rolls back.

Deploying a same-named stack in another region does not migrate, adopt, or remove resources from the original region. Before repeated deployments or final cleanup, inspect both `eu-north-1` and `us-east-1` for retained resources.

Do not use the broad `--destroy` flow solely to remove these artifacts without first confirming its exact targets.

## 5. Cognito-created users require the generated temporary password

**Status:** Confirmed by frontend and infrastructure review.

An administrator-created Cognito user in `FORCE_CHANGE_PASSWORD` status must first sign in with their temporary password. Cognito then requires the user to choose a permanent password before completing authentication.

The frontend does not implement its own `NEW_PASSWORD_REQUIRED`, forgot-password, or reset-password screen. Its sign-in action calls Amplify's `signInWithRedirect()`, so Cognito's hosted/managed login is responsible for displaying the forced password-change form and redirecting the authenticated user back to the application.

The deployment supports this flow when Cognito-native login is enabled:

- `frontend/infrastructure/cdk.json` sets `AllowCustomUserLogin` to `true` for the development environment.
- `frontend/infrastructure/lib/constructs/app-user-pool.ts` adds Cognito as a supported identity provider and enables SRP authentication.
- The configured password policy requires at least 12 characters, including uppercase, lowercase, numeric, and symbol characters.
- Temporary passwords expire after three days.

If `admin-create-user` is called without `--temporary-password`, Cognito generates a temporary password and attempts to deliver it in the invitation email. Cognito does not provide a way to retrieve that generated password afterward. If the invitation was not received, an administrator must resend the invitation or assign a new temporary password.

Example of assigning a replacement temporary password:

```bash
aws cognito-idp admin-set-user-password \
  --user-pool-id <user-pool-id> \
  --username <email-address> \
  --password '<temporary-password>' \
  --no-permanent \
  --region <user-pool-region>
```

Afterward, the user signs in through the application's normal sign-in button with the replacement temporary password. Cognito should automatically prompt them to set a new permanent password. Passing `--permanent` instead would immediately confirm the user and bypass the first-login password-change prompt.

## 6. Component dependencies are omitted from recipe image builds

**Status:** Confirmed by code review and the generated Image Builder recipe; not fixed.

**Observed failure:**

A DCV component version declared the AWS CLI component as a dependency. The DCV component test succeeded, but the AMI built from a recipe containing DCV did not contain AWS CLI. At first boot, the product user-data script failed before setting the generated workstation password:

```text
/var/lib/cloud/instance/scripts/part-001: line 9: /usr/local/bin/aws: No such file or directory
```

The `ubuntu` account consequently remained locked, and DCV's PAM-based system authentication rejected the credentials displayed by VEW.

**Cause:**

VEW handles component dependencies differently in component testing and recipe deployment:

- Component testing prepends the selected component version's direct dependencies before running the component itself.
- Recipe deployment iterates only over the component versions explicitly stored on the recipe. It retrieves each selected component's Image Builder ARN but never reads or expands `componentVersionDependencies`.

The generated nested Image Builder component therefore contained only the explicitly selected code-server and DCV component ARNs. The AWS CLI dependency was absent from both the nested component and the resulting AMI.

**Relevant code:**

- `backend/app/packaging/domain/command_handlers/component/run_component_version_testing_command_handler.py`: `__get_components_versions_definitions_s3_uris` includes direct dependencies during component testing.
- `backend/app/packaging/domain/command_handlers/recipe/deploy_recipe_version_command_handler.py`: `__create_recipe_component_list` only resolves entries from the recipe's explicit component list.
- `backend/app/packaging/domain/command_handlers/recipe/templates/recipe.yaml.j2`: executes only the component ARNs passed by recipe deployment.

**Expected behavior:**

Recipe assembly should expand every selected component version's dependency graph and place each dependency before the component that requires it. Expansion should be recursive, deduplicate shared dependencies, preserve deterministic ordering, detect dependency cycles, and reject incompatible versions of the same component.

Component testing and recipe deployment should use the same dependency-resolution logic so a component cannot pass testing with dependencies that are later omitted from the production image.

After implementing the resolver, affected recipe versions and AMIs must be rebuilt. Existing AMIs do not gain newly resolved dependencies automatically.

## 7. Component validation can fail on transient Ubuntu package-mirror errors

**Status:** Observed during QEMU/KVM component validation; rebuild required.

**Observed failure:**

The runtime validation of the `QEMU KVM Nested Virtualization` component spent approximately 70 minutes in its package-installation step and then failed with APT exit code `100`. The regional Ubuntu mirror returned repeated HTTP `503 Service Unavailable` responses and connection failures while downloading packages:

```text
E: Failed to fetch http://us-east-1.ec2.archive.ubuntu.com/ubuntu/... 503 Service Unavailable
E: Unable to fetch some archives, maybe run apt-get update or try with --fix-missing?
```

The EC2 instance, SSM agent, private-subnet route, NAT gateway, and disk remained healthy. The NAT gateway reported no packet drops or port-allocation errors, and downloads from `security.ubuntu.com` continued to succeed. The failure was therefore caused by the regional package mirror rather than by the component's QEMU/KVM validation logic or VEW's network infrastructure.

The component runs `apt-get update` and `apt-get install` without explicit retry handling. A sustained mirror outage therefore causes the AWSTOE step to abort and marks the component version as `FAILED`.

**Rebuild workflow:**

VEW does not expose a dedicated reset or retry action for a failed component validation. To start another build, open the failed component version, select **Update details**, make any change, and submit the update. VEW creates the next release-candidate revision and automatically runs a new build and validation.

This is not a retry of the same immutable revision. Even when the update is operationally intended only to recover from a transient external failure, it advances the component's release-candidate version.

**Recommended remediation:**

- Add bounded retries and connection timeouts around package index refreshes and package installation.
- Consider a controlled package proxy or mirror for reproducible builds.
- Add an explicit **Retry validation** operation that starts a new test execution without requiring a component-content change or release-candidate version bump.

## 8. An immediate post-launch EC2 lookup can leave component tests stuck in `PENDING`

**Status:** Confirmed in the development environment; not fixed.

**Observed failure:**

The test execution for component version `comp-qihuhevj/vers-xzf52si4` created EC2 instance `i-00c515711d62e2685` at `2026-09-07T06:36:28Z`. The workflow checked the new instance immediately after the launch task completed. The check failed with:

```text
InvalidInstanceID.NotFound: The instance ID 'i-00c515711d62e2685' does not exist
```

The Step Functions execution then followed its error path, terminated the instance, marked the parent component version as `FAILED`, and ended in `FAILED`. The test-execution record itself remained:

```text
status: PENDING
instanceStatus: DISCONNECTED
setupCommandId: null
testCommandId: null
```

This stale child record is why the component page can continue to display a pending test even though no test is running. The EC2 instance is terminated and the parent component version is already `FAILED`.

**Cause:**

The component testing state machine transitions directly from `LaunchTestEnvironment` to `CheckTestEnvironmentLaunchStatus`. There is no initial wait or retry policy between the two tasks. On this execution, the status check ran within a fraction of a second of `RunInstances` and encountered EC2's eventual-consistency window.

When SSM reports the new instance as disconnected, the launch-status handler calls `DescribeInstances` to calculate whether the five-minute connection timeout has elapsed. It does not treat `InvalidInstanceID.NotFound` as a transient response. The exception is therefore caught by the state machine and routed directly to `CompleteComponentVersionTest`.

The completion handler calculates the aggregate test as failed and updates the parent component version, but it does not update pending test-execution entities. Because the launch-status handler failed before writing a terminal status, the child execution remains permanently `PENDING`.

**Relevant code:**

- `backend/infra/constructs/component_version_testing/component_version_testing_state_machine.py`: chains `LaunchTestEnvironment` directly to `CheckTestEnvironmentLaunchStatus`; its 15-second wait is used only after a successful disconnected response.
- `backend/app/packaging/domain/command_handlers/component/check_component_version_testing_environment_launch_status_command_handler.py`: calls the creation-time lookup when SSM reports `DISCONNECTED`.
- `backend/app/packaging/adapters/services/aws_component_version_testing_service.py`: calls `DescribeInstances` without retrying `InvalidInstanceID.NotFound`.
- `backend/app/packaging/domain/command_handlers/component/complete_component_version_testing_command_handler.py`: terminates environments and updates only the parent component version status.

**Recommended remediation:**

- Insert an initial wait after `LaunchTestEnvironment`, before the first status check.
- Retry `InvalidInstanceID.NotFound` with bounded exponential backoff during the EC2 eventual-consistency window.
- Make the error/completion path update every non-terminal test-execution entity to `FAILED`, including its `lastUpdateDate`, before terminating the environment.
- Add tests covering an initially invisible EC2 instance and verifying that every terminal state-machine outcome leaves both the parent component version and its test-execution records in terminal states.

## 9. Android Cuttlefish exposes a different HTTPS port than the operator uses

**Status:** Confirmed on deployed virtual target `i-05a5785f08d57bae6`; not fixed.

**Observed failure:**

Opening the documented operator URL at `https://<public-ip>:8443` failed. A connection test to public port `8443` returned `Connection refused` even though SSH to the same instance succeeded.

**Cause:**

The Android Cuttlefish product template and its connection documentation disagree about the operator's HTTPS port:

- `examples/android-cuttlefish/README.md` instructs users to connect on port `8443`.
- `examples/android-cuttlefish/product.yaml` writes `operator_https_port=1443` to `/etc/default/cuttlefish-operator` during first boot.
- The user security group permits public TCP traffic to `8443` from the user's configured source IP, but it does not permit public TCP traffic to `1443`.

Live inspection confirmed that the instance's routing and network ACL were healthy, TCP `8443` reached the host, and no process was listening on that port. The Cuttlefish operator was active, listening on all interfaces at TCP `1443`, and returned HTTP `200` when accessed locally. A public connection to `1443` timed out at the security-group boundary.

**Recommended remediation:**

Change the product template to configure `operator_https_port=8443`, matching the README and the existing user security-group rule, then rebuild the product image or redeploy the virtual target as required by the product lifecycle.

For an already running instance, the operator can be aligned temporarily by changing `/etc/default/cuttlefish-operator` from port `1443` to `8443` and restarting `cuttlefish-operator`. An SSH tunnel from a local port to the instance's loopback port `1443` is a non-persistent workaround that does not require changing security-group ingress.

The operator uses a self-signed TLS certificate, so browsers may display a certificate warning after connectivity is restored.

**Separate device-startup observation:**

At the time of inspection, the operator service itself was healthy, but the Android guest had not become ready. `launch_cvd` remained in the `assemble_cvd` stage, no ADB or WebRTC device ports were listening, and `/var/log/cuttlefish-userdata.log` contained protobuf fatal messages. This condition does not cause the TCP `8443` refusal, because the operator is a separate service, but it may prevent a device from appearing after the web UI becomes reachable and requires separate investigation if assembly does not complete.

## 10. Public deployment output gives incorrect or incomplete DNS guidance

**Status:** Confirmed by deployment-script and synthesized-template review; not fixed.

For a public deployment with custom domains, the completion output says:

```text
<web-domain> -> CNAME to CloudFront distribution
<api-domain> -> CNAME to API ALB
```

This guidance does not distinguish Route 53 from external DNS providers, and the public API target is incorrectly identified.

**Actual public targets:**

- The web domain targets the CloudFront distribution created by the frontend stack.
- The API domain targets the regional API Gateway custom domain created by `ApiIntegrationStack`; a public API ALB is not created.
- The deployment script creates Route 53 alias records only for private deployments. Public DNS records must currently be created separately.

When the public zone is hosted in Route 53, both records should be `A` alias records:

- The web `A` alias targets the CloudFront distribution.
- The API `A` alias targets the API Gateway custom domain's `RegionalDomainName`, using its `RegionalHostedZoneId`.
- The frontend distribution has IPv6 disabled, so an `AAAA` alias should not be created for it under the current configuration.

For a DNS provider outside Route 53, CNAME records are appropriate for these subdomains, but the API CNAME must point to API Gateway's regional domain name—not to an ALB.

**Relevant code:**

- `deploy.sh`: the public-deployment summary prints generic CNAME instructions and describes the API target as an API ALB.
- `frontend/infrastructure/lib/constructs/app-cdn.ts`: attaches the certificate and alternate domain to CloudFront but creates no Route 53 record.
- `backend/infra/backend/integration_stack.py`: creates an `AWS::ApiGateway::DomainName` and base-path mappings but creates no public Route 53 record or output for the regional DNS target and hosted-zone ID.

**Recommended remediation:**

- If the configured public zone is in Route 53, optionally automate `A` alias creation for the web and API domains.
- Export the API Gateway `RegionalDomainName` and `RegionalHostedZoneId` from `ApiIntegrationStack` so the DNS target is explicit.
- Make the completion output provider-aware: show Route 53 alias instructions when applicable and external-provider CNAME instructions otherwise.
- Correct the public API description from `API ALB` to `regional API Gateway custom domain`.
