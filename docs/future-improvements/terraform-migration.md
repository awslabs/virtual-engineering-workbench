# Terraform migration

**Status:** Research

**Last updated:** 2026-09-04

## Conclusion

Most of VEW's statically deployed platform infrastructure can move from AWS CDK/CloudFormation to Terraform. There is no fundamental Terraform provider gap for the core platform: networking, IAM, storage, Cognito, Lambda, API Gateway, EventBridge, Step Functions, Service Catalog administration, CloudFront, WAF, and Verified Permissions are all representable with the HashiCorp AWS provider. The AWS Cloud Control (`awscc`) provider can cover uncommon CloudFormation resource types, although native `aws` resources are preferable because `awscc` has weaker default and drift handling.

The recommended boundary is:

- **Move the static VEW platform and spoke-account baseline to Terraform.**
- **Keep VEW's runtime-created Image Builder resources, catalog objects, and workbenches application-managed.**
- **Keep existing Service Catalog workbench products CloudFormation-based initially.** Moving those products to Terraform is possible, but it requires a Service Catalog external provisioning engine and changes to VEW's publishing and provisioning behavior; it is not part of a mechanical CDK migration.

A clean deployment under a new prefix is much safer than importing the existing development environment. A production environment that must preserve data would require a controlled, stack-by-stack ownership transfer.

## Evidence from the current deployment

The currently synthesized public development deployment contains:

| Item | Count |
| --- | ---: |
| CloudFormation templates | 15 |
| Synthesized resources | 774 |
| Resources with `DeletionPolicy` or `UpdateReplacePolicy` set to `Retain` | 80 |
| CloudFormation custom resources | 18 |

These numbers are a point-in-time inventory of `backend/cdk.out` and `frontend/infrastructure/cdk.out`. They do not include every optional configuration. Private mode additionally creates ALBs, listeners, target groups, private DNS, and related networking; backup, AppConfig, RAM, and other conditional resources are also present in source but not necessarily in this synthesis.

The orphan problem is therefore not solely a CDK defect. VEW deliberately retains a significant set of resources:

- every backend Lambda's published versions use `RemovalPolicy.RETAIN`;
- API access log groups and several Step Functions/Pipes log groups are retained;
- artifact S3 buckets and the artifact ECR repository are retained;
- several KMS keys are retained;
- both Lambda@Edge handlers are retained;
- production-like environments retain additional databases and event buses.

CloudFormation documents that a retained resource remains after stack deletion, is removed from CloudFormation's ownership, and can continue incurring charges. The current `deploy.sh --destroy` then compensates with name-prefix cleanup, but only searches selected stack statuses and the configured region. That cannot reliably find retained resources in another region, failed stacks, service-managed replicas, dynamically onboarded accounts, or resources whose names do not match the prefix.

Terraform improves this by producing an explicit destruction plan for resources in its state. It does not guarantee an orphan-free environment: resources deliberately removed from state, excluded from a root module, created by the application, protected with lifecycle rules, or created as service-managed children will still remain.

## What can move directly

The following static areas can be modeled with normal Terraform resources and data sources.

| Area | VEW resources | Migration assessment |
| --- | --- | --- |
| Networking | VPC lookup/creation, subnets, security groups, VPC endpoints, ALBs, listeners, target groups, Route 53 records | Direct. Use explicit hub/spoke account and region provider configurations. |
| Identity | Cognito user pool, app clients, domain, OIDC provider, resource servers, Lambda triggers | Direct. Importing an active pool requires particular care because replacement would affect every user. |
| Authorization | IAM roles/policies/instance profiles and Verified Permissions stores/policies | Direct. Current AWS provider versions include native Verified Permissions resources. |
| Storage and encryption | DynamoDB, S3, ECR, KMS keys/aliases, Secrets Manager, SSM parameters, backups | Direct. Destruction and retention must be environment-specific and explicit. |
| Backend compute | Lambda functions, versions, aliases, layers, concurrency, DLQs, ECS cluster/task definition | Direct after separating artifact builds from infrastructure application. Current AWS provider versions also expose Lambda durable configuration. |
| APIs | REST API Gateway APIs from OpenAPI, stages, deployments, domains, base-path mappings, resource policies, authorizers | Direct. Render the OpenAPI document before `terraform apply` or with Terraform template functions. Manage the regional API Gateway account/CloudWatch role once rather than once per bounded context. |
| Events | EventBridge buses/rules/policies, SNS, SQS, EventBridge Pipes, Scheduler groups/schedules | Direct. EventBridge Pipes have native provider support. |
| Orchestration | Step Functions definitions, logging and IAM | Direct. Generate Amazon States Language with `jsonencode` or template files. |
| Frontend, public | CloudFront, origins/OAC, S3, WAF, alarms, Cognito integration | Direct, with the edge resources managed in `us-east-1`. |
| Frontend, private | Internal ALB, S3 origin handler, private DNS and certificates | Direct. Avoid storing a generated private certificate key in Terraform state. Prefer an organization-issued or imported ACM certificate. |
| Monitoring | CloudWatch alarms, dashboards, log groups, SNS actions and anomaly detectors | Direct. Explicit resource definitions will be verbose but predictable. |
| Cross-account sharing | AWS RAM shares/associations/acceptance, cross-account IAM and SSM parameters | Direct for known accounts. Dynamic onboarding needs separate state per account and region. |
| Static Service Catalog administration | Portfolios, associations, constraints and supporting roles | Direct where these are platform-owned rather than created dynamically by VEW. |

Representative current provider documentation confirms support for [Lambda functions](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_function), [EventBridge Pipes](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/pipes_pipe), [Verified Permissions policy stores](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/verifiedpermissions_policy_store), and [CloudFront distributions with Lambda associations](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudfront_distribution.html). The generated [AWS Cloud Control provider](https://registry.terraform.io/providers/hashicorp/awscc/latest/docs) is available as a fallback for uncommon resource types, but its documented schema/default limitations make it a second choice.

## What requires replacement glue

CDK currently performs build steps and imperative API calls in addition to declaring resources. Those behaviors need deliberate replacements rather than literal translation.

### Application artifacts

CDK fingerprints and bundles Python Lambda code, Lambda layers, Node.js edge functions, frontend files, and the account-onboarding ECS image. Terraform can reference ZIP files, S3 objects, and container image digests, but it should not become the build system.

CI should produce immutable artifacts first, publish them to S3/ECR, and pass URIs plus content hashes into Terraform. Frontend publication should similarly use a build and `aws s3 sync` step, followed by CloudFront invalidation where applicable. This keeps infrastructure plans independent from local Docker, Node, Python, and `uv` behavior.

### Current custom resources

Most of the 18 custom resources can disappear:

| Current custom behavior | Terraform replacement |
| --- | --- |
| Event bus "upsert" shared across stacks | Give each bus one owning root module; other modules read outputs or query it as data. |
| SSM parameter lookup | `data "aws_ssm_parameter"`. |
| VPC endpoint ENI/IP discovery | VPC endpoint attributes plus network-interface data sources. |
| RAM resource association and invitation acceptance | Native RAM association/accepter resources with an appropriate account provider. |
| Empty S3 buckets during deletion | `force_destroy` only for disposable environments; retain/protect production data explicitly. |
| Upload product template assets to S3 | CI upload or managed S3 objects. |
| Publish an EventBridge event during deployment | A post-deployment CI action, not a long-lived Terraform resource. |
| Configure Lambda@Edge log subscriptions across regions | Explicit resources for supported regions, or retain the operational Lambda as a separately managed tool. |

The last item is awkward rather than impossible. Lambda@Edge functions must live in `us-east-1`, use numbered versions, and create service-managed replicas. AWS states that replicas cannot be deleted manually and typically disappear only hours after the final CloudFront association is removed. Terraform can manage the source function, version, and CloudFront association, but it cannot make AWS delete those replicas immediately.

### Security checks

`cdk-nag` does not translate to Terraform. Replace it with a combination of Terraform validation, TFLint, Checkov or Trivy configuration scanning, provider-level default tags, and policy-as-code checks in CI. Existing suppressions must be reviewed and either expressed in the replacement tool or removed; copying every suppression would preserve historical weaknesses without confirming that it still applies.

## What should not move in the initial migration

### Application-managed packaging resources

VEW creates and versions EC2 Image Builder components, recipes, pipelines, and images in response to UI/API activity. These are application data with dynamic identifiers and asynchronous lifecycle state. Terraform should provision the IAM, storage, queues, functions, and Step Functions that power this workflow, but it should not also own the component/recipe/image objects created by those functions. Two controllers managing the same objects would cause drift and deletion risk.

### Dynamically published products and workbenches

VEW's publishing service calls Service Catalog at runtime and explicitly creates products and provisioning artifacts of type `CLOUD_FORMATION_TEMPLATE`. The provisioning service then monitors the Service Catalog-created CloudFormation stacks. These product versions and provisioned workbenches should remain application-managed.

Terraform is supported as an AWS Service Catalog product through the `EXTERNAL` product type, but AWS requires a separate provisioning engine in the administrator account. Service Catalog sends operations to that engine, and each provisioned product has its own Terraform state. Adopting it would require changes to VEW's template validation, product creation, parameter metadata, status/event handling, permissions, termination, and debugging paths. It is a viable later product feature, not a prerequisite for moving the VEW platform itself.

See AWS's documentation for [Service Catalog external engines](https://docs.aws.amazon.com/servicecatalog/latest/adminguide/external-engine.html), [configuring the Terraform provisioning engine](https://docs.aws.amazon.com/servicecatalog/latest/adminguide/getstarted-terraform-engine.html), and [per-product state](https://docs.aws.amazon.com/servicecatalog/latest/adminguide/getstarted-terraform-engine-state.html).

### Imperative installation and seed actions

The deployment script performs one-time actions such as CDK bootstrapping, dependency installation, frontend upload, DynamoDB seed writes, Cognito user creation, private DNS upserts, and spoke bootstrap deployment. Terraform can technically model some of these, but not all should become resources:

- CDK bootstrap disappears once nothing depends on CDK asset roles/buckets.
- DNS belongs in Terraform.
- Stable initial records may be Terraform-managed, but mutable application data and administrator users should be created through a versioned migration/seed command.
- Dependency installation and builds remain CI concerns.
- User invitations remain an operational identity-management action.

## Runtime account onboarding

Account onboarding is the second major architectural boundary. VEW currently launches an ECS task that assumes a role in the target account, runs `cdk bootstrap`, and then runs `cdk deploy` for prerequisite, publishing-enablement, and provisioning-enablement stacks.

This can move to Terraform, but not as a source-only conversion. The replacement needs:

- a remote state key per account, region, environment, and onboarding layer;
- state locking and versioning;
- a runner that assumes the target account role;
- concurrency control so two onboarding requests cannot apply the same state;
- plan/apply logging surfaced in VEW;
- retry and partial-failure recovery;
- an explicit offboarding/destroy workflow;
- migration of the current Step Functions/ECS task contract from CDK context arguments to Terraform variables and outputs.

Terraform's S3 backend supports state locking with `use_lockfile = true`, and HashiCorp recommends bucket versioning for state recovery. This is a good fit, but the bootstrap state bucket and KMS key must be created separately before the main roots use them.

## Destruction and retention policy

The Terraform implementation should make lifecycle intent visible instead of applying broad retention defaults.

Recommended rules:

- Disposable development environments delete log groups, Lambda versions, S3 objects/buckets, and ECR images on destroy.
- Production data stores, artifact stores, and KMS keys use explicit protection and a documented decommissioning procedure.
- Never use a blanket retain/protect rule for all Lambda versions or logs.
- Tag every platform resource with environment, owning root module, and `ManagedBy=Terraform`.
- Treat KMS scheduled deletion and Lambda@Edge replica cleanup as asynchronous expected states, not immediate destroy success.
- Run a post-destroy inventory by account, region, and management tag; fail the teardown report when unexpected resources remain.
- Keep application-managed resources out of platform state and report them separately during environment decommissioning.

Terraform destroys objects it manages when they are removed from configuration or included in `terraform destroy`, subject to lifecycle and provider behavior. It can also intentionally forget objects with a `removed` block. Those are useful controls, but they mean state discipline is still essential. See HashiCorp's [resource destruction](https://developer.hashicorp.com/terraform/language/resources/destroy), [lifecycle](https://developer.hashicorp.com/terraform/language/meta-arguments/lifecycle), and [S3 backend](https://developer.hashicorp.com/terraform/language/backend/s3) documentation.

## State layout

Do not place all 774 resources into one state. A reasonable initial split is:

1. **State bootstrap:** versioned/encrypted state bucket, lock configuration, CI roles.
2. **Regional foundation:** VPC/endpoints, shared KMS, S3/ECR, shared event buses and cross-account foundations.
3. **Identity and edge:** Cognito plus a separate `us-east-1` edge module for public CloudFront/WAF/Lambda@Edge resources.
4. **Backend services:** modules per bounded context, grouped into one or a small number of roots to avoid excessive cross-state dependencies.
5. **Frontend regional/private:** regional WAF, frontend storage, or private ALB/DNS resources.
6. **Spoke baseline:** one state per spoke account, region, and environment.

Prefer explicit module outputs and stable SSM discovery parameters over copying CDK's large collection of CloudFormation exports. Avoid making every bounded context its own state unless teams truly require separate deployment authority; excessive remote-state coupling is another form of distributed monolith.

## Migration strategies

### Recommended: rebuild a clean environment

For the current development deployment, create a Terraform-managed environment under a new environment name or resource prefix, verify it end-to-end, migrate only required data, switch DNS, and then decommission the CDK environment using a complete cross-region inventory. This avoids importing hundreds of CDK-generated logical resources and untangling CloudFormation exports.

### Required when an environment must be preserved: staged ownership transfer

Migrate one bounded stack at a time:

1. Write Terraform configuration matching the physical resources.
2. Add declarative import blocks and obtain a no-change Terraform plan.
3. Configure CloudFormation to retain the resources being transferred.
4. Remove those resources from the CloudFormation stack so CloudFormation relinquishes ownership without deleting them.
5. Apply Terraform and confirm a no-change plan again.
6. Remove obsolete exports/custom-resource providers only after all consumers have moved.

Terraform cannot import a CloudFormation stack as one managed object and then manage every child resource. Each supported physical resource must be mapped to one Terraform address. HashiCorp warns that importing the same object to multiple addresses can cause unwanted behavior and that complex imports require all secondary resources to be declared, or Terraform may propose deleting them. See [Import existing resources](https://developer.hashicorp.com/terraform/cli/import/usage).

### Not recommended: big-bang import

Importing the entire live deployment at once would combine hundreds of resources, multiple accounts/regions, CloudFormation exports, retained Lambda versions, and custom-resource side effects into one cutover. A syntactically successful import would not prove behavioral equivalence and would make rollback difficult.

## Suggested delivery sequence

1. Correct the existing CDK teardown and retention behavior so the current environment remains manageable during migration.
2. Establish the Terraform state backend, provider conventions, naming/tags, CI validation, and artifact-build contract.
3. Implement a clean Terraform deployment of shared foundations and the frontend/identity plane.
4. Port backend infrastructure by bounded context, replacing custom resources as their owners move.
5. Port the spoke-account baseline and replace the runtime CDK onboarding container with a Terraform runner.
6. Cut over a clean development environment and perform an orphan audit across all involved regions/accounts.
7. Decide separately whether Service Catalog workbench templates should remain CloudFormation or adopt the external Terraform engine.

## Final assessment

| Question | Answer |
| --- | --- |
| Can the static VEW platform move to Terraform? | Yes, almost entirely. |
| Is there a blocking AWS provider gap? | No known blocker; a few uncommon resources may need `awscc` or small operational glue. |
| Will Terraform automatically eliminate all orphans? | No. It will improve visibility and state-based deletion, but retention policy, service-managed resources, dynamic application resources, and cross-account state still require explicit handling. |
| Can current CloudFormation stacks be imported wholesale? | No. Physical resources must be transferred individually or the environment must be rebuilt. |
| Can workbench product templates become Terraform? | Yes, through Service Catalog's external engine, but that is a separate VEW application redesign. |
| Should runtime Image Builder/catalog/workbench objects enter the platform Terraform state? | No. Keep them owned by VEW. |
