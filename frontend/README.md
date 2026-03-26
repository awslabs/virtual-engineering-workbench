# VEW Frontend

## Architecture

The frontend supports two deployment modes:

**Public deployment** (default) — Static SPA served through CloudFront with Lambda@Edge authentication. **Private deployment** — ALB within a VPC, no internet exposure.

See the [root README architecture diagrams](../README.md#public-deployment) for the full deployment architecture.

Set `PrivateDeployment: true` in `infrastructure/cdk.json` to use private mode. Private deployment requires a custom domain and TLS certificate.

In both modes:

1. User navigates to the web application
1. Lambda@Edge checks for a valid JWT token in the request cookie
1. If no valid JWT, redirects to Cognito login (corporate directory or manual user)
1. Valid JWT allows serving static resources from S3
1. The React app calls backend APIs with `Authorization: Bearer <token>` headers

### Technology stack

| Layer | Technology |
| ------- | ----------- |
| Framework | React 18 |
| Language | TypeScript |
| Build tool | Vite 7 |
| UI library | Cloudscape Design System |
| State management | Recoil |
| Authentication | Amazon Cognito (aws-amplify) |
| HTTP client | Axios, SWR |
| Testing | Vitest (unit), Cypress (E2E) |
| Package manager | Yarn 4 (Corepack) |
| CDK infrastructure | TypeScript (CDK v2) |

## Structure

```text
frontend/
├── infrastructure/       # CDK stacks (TypeScript)
│   ├── lib/              # Stack definitions
│   │   ├── public-access-deployment-stack.ts   # CloudFront + S3 + WAF
│   │   ├── cognito-stack.ts                    # User pool + OIDC federation
│   │   └── ...
│   ├── bin/              # CDK app entry point
│   ├── cdk.json          # CDK configuration and context
│   └── package.json
│
├── web/                  # Main web application
│   ├── src/
│   │   ├── components/   # Reusable UI components
│   │   ├── pages/        # Page-level components (routing targets)
│   │   ├── services/     # API clients (generated from OpenAPI)
│   │   ├── hooks/        # Custom React hooks
│   │   ├── state/        # Recoil atoms and selectors
│   │   └── utils/        # Shared utilities
│   ├── public/           # Static assets
│   ├── testing/          # Test utilities and fixtures
│   ├── configure_auth.sh # Generates auth config from deployed stacks
│   ├── generate_clients.sh # Generates API clients from OpenAPI specs
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── package.json
│
├── ci/                   # CI/CD scripts
│   ├── build.sh          # Build script
│   └── deploy.sh         # Deploy script (S3 upload + CF invalidation)
│
├── docs/                 # Frontend architecture diagrams
│   └── architecture.drawio
│
└── scripts/
    └── security-scan.sh  # Dependency vulnerability scanning
```

## Setup

### Prerequisites

- Node.js 18+
- Yarn 4.x (via Corepack: `corepack enable`)

### Install dependencies

```bash
cd web
yarn install --frozen-lockfile
```

## Local development

To run the frontend locally against deployed backend stacks:

Generate the auth configuration from your deployed CloudFormation stacks:

```bash
cd web
./configure_auth.sh <APP_NAME> <BACKEND_APP_NAME> <ENV> <FE_REGION> <BE_REGION> [FE_PROFILE] [BE_PROFILE]
```

For example, with default naming:

```bash
./configure_auth.sh proserve-wb-ui proserve-wb dev us-east-1 us-east-1
```

This reads Cognito and API Gateway outputs from CloudFormation and writes `aws-exports.js`.

Then start the dev server:

```bash
REACT_APP_ENVIRONMENT=local yarn dev
```

Open <http://localhost:3000>.

### Environment variables

| Variable | Description |
| ---------- | ------------- |
| `REACT_APP_ENVIRONMENT` | `local` for dev server, environment name for builds |

## Build

```bash
cd web
yarn build
```

Output goes to `web/dist/`. The deploy script uploads this to S3 and invalidates CloudFront.

## Tests

### Unit tests

```bash
cd web
yarn test          # Single run
yarn test:ci       # With coverage report
```

Uses Vitest with React Testing Library.

### E2E tests

```bash
cd web
yarn test:cypress:run              # Headless (default browser)
yarn test:cypress:chrome           # Chrome
yarn test:cypress:parallel:chrome  # Parallel execution (4 threads)
yarn test:cypress:open             # Interactive mode
```

Uses Cypress against a built preview server.

## API client generation

API clients are generated from OpenAPI specifications exported by the backend:

```bash
cd web
./generate_clients.sh
```

This uses `@openapitools/openapi-generator-cli` to produce TypeScript clients in `src/services/api-src/`.

## CDK infrastructure

The frontend infrastructure deploys Cognito, CloudFront, S3, WAF, and Lambda@Edge:

```bash
cd infrastructure
yarn install --frozen-lockfile

cdk deploy --all --require-approval never \
  -c environment=dev \
  -c account=<ACCOUNT_ID> \
  -c region=<REGION> \
  -c app-name=<APP_NAME> \
  -c deployment-qualifier=<QUALIFIER>
```

### CDK context parameters

| Parameter | Default | Description |
| --- | --- | --- |
| `app-name` | `proserve-wb-ui` | Application name (must match backend: `{org}-{app}-ui`) |
| `deployment-qualifier` | derived from account ID | Unique qualifier for S3 bucket naming |
| `environment` | — | `dev`, `qa`, or `prod` |
| `OIDCSecretName` | — | Secrets Manager secret with OIDC credentials (omit for manual Cognito users) |
| `AllowCustomUserLogin` | `true` | Allow Cognito-native users (no OIDC) |
| `RequireCustomUserLogin2FA` | `true` | Require MFA for Cognito-native users |
| `PrivateDeployment` | `false` | `true` for ALB-based private access (no CloudFront) |
| `VPCName` | `default-vpc` | VPC name for ALB placement (private deployment only) |
| `CustomLoginDNSEnabled` | `false` | Enable custom DNS for Cognito login page |
| `cert-arn` | — | TLS certificate ARN for custom domain |
| `cert-arn-login` | — | TLS certificate ARN in us-east-1 for Cognito (if deploying to another region) |
| `use-custom-domain` | — | Custom domain name |

### Stack cleanup

Lambda@Edge functions cannot be deleted immediately — CloudFront must first remove all replicas. After running `cdk destroy`:

1. Wait a few hours for Lambda@Edge replica cleanup
1. Manually delete the Lambda@Edge function
1. Manually delete the S3 logs bucket (`{stack_name}-logs`)
1. Manually delete the Cognito user pool
1. Remove the OIDC secret from Secrets Manager

See `infrastructure/README.md` for detailed cleanup steps.

## Extending the frontend

### Adding a new page

1. Create a page component in `web/src/pages/{feature}/`
1. Add a route in the app router
1. If the feature needs a new backend API:
   - Generate the API client: `./generate_clients.sh`
   - Create a custom hook in `web/src/hooks/{feature}/`
1. Use Cloudscape components for consistent UI

### Code quality

```bash
cd web
yarn lint          # ESLint with TypeScript rules
```

For full automated deployment, use `deploy.sh` from the repository root.
