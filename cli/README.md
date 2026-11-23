# VEW CLI

Command-line client for the Virtual Engineering Workbench (VEW) platform. Authenticates against any OIDC-compliant identity provider and drives the VEW REST APIs for managing projects, images, publishing, provisioning, and any other bounded context exposed by the platform.

Written in Rust as a single self-contained binary. Cross-platform: macOS (Intel/Apple Silicon), Linux (x86_64/aarch64), Windows (x86_64).

## Highlights

- **Any OIDC provider** — auto-discovers endpoints via OpenID Connect Discovery 1.0 (RFC 8414). Tested with AWS Cognito, Keycloak, Auth0, Azure AD, and Okta. No provider-specific code or configuration. A VEW deployment accepts only tokens from its own Cognito user pool, so against VEW the `issuer_url` is that pool. See [Using an external identity provider](#using-an-external-identity-provider).
- **Headless-friendly** — `--no-browser` (or `VEW_NO_BROWSER=1`) prints the login URL to stdout so you can authenticate from SSH sessions, containers, or CI runners.
- **Scriptable** — `vew auth token` writes a raw access or ID token to stdout, ready to pipe into `curl` or any HTTP client.
- **Discovers commands dynamically** — subcommands per bounded context are resolved from each service's OpenAPI spec at runtime; no CLI update needed when the backend adds an endpoint.

## Install

Requires [Rust](https://rustup.rs/) 1.95.0 or newer.

### macOS / Linux

```bash
./install.sh
```

Builds the release binary and installs it to `~/.local/bin/vew`. Add `~/.local/bin` to your `PATH` if it isn't already.

### Windows

```powershell
.\install.ps1
```

Builds the release binary and installs it to `%LOCALAPPDATA%\vew\vew.exe`, adding it to your `PATH`.

### Via cargo

```bash
cargo install --path .
```

## Configuration

Create `~/.vew/config` in TOML. Each profile points at a VEW API endpoint and an OIDC issuer URL. The CLI does OIDC Discovery against the issuer to resolve the rest of the auth endpoints automatically.

```toml
default_profile = "dev"

[profiles.dev]
api_endpoint = "https://api.dev.example.com"
issuer_url = "https://cognito-idp.eu-west-1.amazonaws.com/eu-west-1_XXXXXXX"
oidc_client_id = "your-client-id"

[profiles.prod]
api_endpoint = "https://api.prod.example.com"
issuer_url = "https://cognito-idp.eu-west-1.amazonaws.com/eu-west-1_YYYYYYY"
oidc_client_id = "vew-cli-prod"
scopes = ["openid", "profile", "email", "vew:read"]
```

**Required per profile:** `api_endpoint`, `issuer_url`, `oidc_client_id`.
**Optional:** `scopes` — defaults to `["openid", "profile", "email"]` when omitted.

The `issuer_url` is the OIDC issuer, matching the `iss` claim in ID tokens. For Cognito that's `https://cognito-idp.<region>.amazonaws.com/<user-pool-id>`; for Keycloak that's `https://<host>/realms/<realm>`; and so on for any OIDC provider. Against a VEW deployment, use the Cognito form (see below).

### Using an external identity provider

The CLI itself works with any OIDC provider. A VEW deployment does not: the API router validates tokens against VEW's own Cognito user pool and the `vew-cli` app client, both read from SSM (`backend/infra/backend/vew_api_router_stack.py:188-195`). A token from Keycloak, Auth0, Azure AD or Okta is rejected. To sign in with an external provider, federate it into the Cognito user pool, and keep `issuer_url` pointing at the pool. Pointing `issuer_url` directly at an external provider applies only to non-VEW APIs.

### Finding these values in a VEW deployment

The platform's `deploy.sh` provisions the unified API endpoint that path-routes `/<bc>/*` to each backend bounded-context API Gateway, and publishes the values the CLI needs as SSM parameters.

It does **not** create a Cognito app client for the CLI. That client comes from the
frontend deployment's `ADDITIONAL_APP_CLIENTS` list: add an entry named `vew-cli`
(public client, PKCE, callback `http://localhost:17823/callback`) and the frontend
stack creates it and publishes its id. Without that entry there is no CLI client
and the router's authorizer has nothing to read.

The deployment uses one shared `-ui` prefix for all three parameters.
`deploy.sh` sets `APP_NAME` to `<app-name>-ui`, then appends `-<env>` once;
`<app-name>` below means `${ORG_PREFIX}-${APP_PREFIX}` and does not itself
include `-ui`.

| Config field | SSM parameter |
|---|---|
| `api_endpoint` | `/<app-name>-ui-<env>/vew-api-endpoint` |
| `oidc_client_id` | `/<app-name>-ui-<env>/app-client-id/vew-cli` |
| `issuer_url` | `/<app-name>-ui-<env>/user-pool-id` — read the pool ID, then construct `https://cognito-idp.<region>.amazonaws.com/<pool-id>` |

Read `api_endpoint` from the SSM parameter rather than from a stack output. Which
stack provides it depends on how the platform was deployed: without a custom API
domain it comes from the `VewApiEndpoint` output of the
`<org>-<app>-vew-api-router-<env>` stack in the backend app, and with one there is
no such stack — `deploy.sh` writes the custom domain into the parameter instead.
The parameter is the same in both cases, which is why it is the value to use.

```bash
# Example: fetch all three values after deploy
# (<app-name> is ORG_PREFIX-APP_PREFIX; deploy.sh adds -ui once)
AWS_PROFILE=<profile> aws ssm get-parameters \
  --names "/<app-name>-ui-<env>/vew-api-endpoint" \
          "/<app-name>-ui-<env>/app-client-id/vew-cli" \
          "/<app-name>-ui-<env>/user-pool-id" \
  --query 'Parameters[].[Name,Value]' --output table
```

## Usage

### Authentication

```bash
vew auth login                  # login with the default profile (opens browser)
vew auth login -p prod          # login with a specific profile
vew auth login --no-browser     # print the login URL to stdout (headless)
vew auth logout                 # revoke session and remove local tokens
```

Setting `VEW_NO_BROWSER=1` in the environment is equivalent to passing `--no-browser`.

### Get a token for piping

```bash
vew auth token                  # access token to stdout (default)
vew auth token --type id        # id token to stdout

# pipe into curl or any HTTP client
curl -H "Authorization: Bearer $(vew auth token)" https://api.example.com/resource
```

The token is written to stdout without a trailing newline so it composes cleanly with command substitution.

### Bounded-context commands

Commands follow the pattern `vew <bounded-context> <operation> [options]`. Operations and their parameters are discovered dynamically from each service's OpenAPI spec — the CLI fetches and caches these on first use. A VEW deployment serves four contexts: `projects`, `packaging`, `publishing` and `provisioning` (`backend/infra/constants.py:101-106`). Pipelines are operations of `packaging`.

```bash
vew init                                          # fetch and cache API specs for all enabled contexts
vew packaging                                     # list operations for the packaging context
vew packaging get-pipelines --help                # show parameters for a specific operation
vew packaging get-pipelines --project-id abc123   # run an operation
vew publishing get-products --project-id abc123 -p prod   # target a specific profile
```

Output is pretty-printed JSON on stdout. Errors and debug output go to stderr.

### Global flags

| Flag | Environment variable | Description |
|---|---|---|
| `-p`, `--profile <name>` | `VEW_PROFILE` | Override the default profile |
| `-v`, `--verbose` | | Enable debug output on stderr |
| `--refresh-cache` | | Force re-fetch of the API spec for the targeted context |

Global flags can appear anywhere on the command line — `vew packaging --profile prod get-pipelines --project-id abc123` and `vew --profile prod packaging get-pipelines --project-id abc123` behave identically.

## Build

```bash
cargo check              # type check
cargo build              # debug build
cargo build --release    # release build
cargo test               # run all tests
cargo clippy             # lint
cargo fmt                # format
```

## Cross-platform release builds

`scripts/build.sh` produces release archives and SHA-256 checksums in `dist/` for a given target triple:

```bash
./scripts/build.sh x86_64-unknown-linux-gnu
./scripts/build.sh aarch64-apple-darwin
./scripts/build.sh x86_64-pc-windows-gnu
```

Install the corresponding cross-compilation toolchain and `rustup target add <triple>` first. See `scripts/build.sh` for the target list this repo currently ships.

## Project layout

```
src/
├── main.rs                # Parse CLI, delegate to bootstrap
├── bootstrap.rs           # Wire adapters into the domain
├── lib.rs                 # Module declarations
├── cli/                   # Clap subcommands, arg normalization, output rendering
├── shared/                # Cross-cutting: constants, HTTP client, auth trait, verbose logging
├── identity/              # OIDC authentication (PKCE, discovery, token store, JWT validation)
├── configuration/         # Reads ~/.vew/config, resolves the active profile
└── vew_api/               # Fetches OpenAPI specs, renders per-context help, invokes operations
tests/                     # Integration tests (wiremock + tempfile, no real services)
scripts/build.sh           # Cross-platform release build helper
```

The codebase uses **ports and adapters**: each folder under `src/` (other than `cli/`, `shared/`, `main.rs`, `bootstrap.rs`, `lib.rs`) is a self-contained bounded context with its own domain (models, services), ports (trait interfaces), and adapters (concrete implementations wrapping external crates). Wiring lives in `bootstrap.rs`.
