# VEW CLI

Command-line client for the Virtual Engineering Workbench (VEW) platform. Authenticates against any OIDC-compliant identity provider and drives the VEW REST APIs for managing projects, images, publishing, provisioning, and any other bounded context exposed by the platform.

Written in Rust as a single self-contained binary. Cross-platform: macOS (Intel/Apple Silicon), Linux (x86_64/aarch64), Windows (x86_64).

## Highlights

- **Any OIDC provider** — auto-discovers endpoints via OpenID Connect Discovery 1.0 (RFC 8414). Tested with AWS Cognito, Keycloak, Auth0, Azure AD, and Okta. No provider-specific code or configuration.
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
issuer_url = "https://keycloak.example.com/realms/vew"
oidc_client_id = "vew-cli-prod"
scopes = ["openid", "profile", "email", "vew:read"]
```

**Required per profile:** `api_endpoint`, `issuer_url`, `oidc_client_id`.
**Optional:** `scopes` — defaults to `["openid", "profile", "email"]` when omitted.

The `issuer_url` is the OIDC issuer, matching the `iss` claim in ID tokens. For Cognito that's `https://cognito-idp.<region>.amazonaws.com/<user-pool-id>`; for Keycloak that's `https://<host>/realms/<realm>`; and so on for any OIDC provider.

### Finding these values in a VEW deployment

The platform's `deploy.sh` provisions everything the CLI needs — a dedicated Cognito app client (public client, PKCE, `http://localhost:17823/callback`) and a unified API endpoint that path-routes `/<bc>/*` to each backend bounded-context API Gateway. All three config values are exposed as SSM parameters:

| Config field | SSM parameter | CloudFormation output |
|---|---|---|
| `api_endpoint` | `/<app-name>-<env>/vew-api-endpoint` | see note below |
| `oidc_client_id` | `/<app-name>-<env>/vew-cli-client-id` | `VewCliClientId` (on the frontend deployment stack) |
| `issuer_url` | `/<app-name>-<env>/user-pool-id` — read the pool ID, then construct `https://cognito-idp.<region>.amazonaws.com/<pool-id>` | `UserPoolId` (on the frontend deployment stack) |

Read `api_endpoint` from the SSM parameter rather than from a stack output. Which
stack provides it depends on how the platform was deployed: without a custom API
domain it comes from the `VewApiEndpoint` output of the
`<org>-<app>-vew-api-router-<env>` stack in the backend app, and with one there is
no such stack — `deploy.sh` writes the custom domain into the parameter instead.
The parameter is the same in both cases, which is why it is the value to use.

```bash
# Example: fetch all three values after deploy (adjust <app-name>-<env> to match your deployment)
AWS_PROFILE=<profile> aws ssm get-parameters \
  --names "/<app-name>-<env>/vew-api-endpoint" \
          "/<app-name>-<env>/vew-cli-client-id" \
          "/<app-name>-<env>/user-pool-id" \
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

Commands follow the pattern `vew <bounded-context> <operation> [options]`. Operations and their parameters are discovered dynamically from each service's OpenAPI spec — the CLI fetches and caches these on first use.

```bash
vew init                                          # fetch and cache API specs for all enabled contexts
vew pipelines                                     # list operations for the pipelines context
vew pipelines get-items --help                    # show parameters for a specific operation
vew pipelines get-items --project-id abc123       # run an operation
vew publishing list-products -p prod              # target a specific profile
```

Output is pretty-printed JSON on stdout. Errors and debug output go to stderr.

### Global flags

| Flag | Environment variable | Description |
|---|---|---|
| `-p`, `--profile <name>` | `VEW_PROFILE` | Override the default profile |
| `-v`, `--verbose` | | Enable debug output on stderr |
| `--refresh-cache` | | Force re-fetch of the API spec for the targeted context |

Global flags can appear anywhere on the command line — `vew pipelines --profile prod get-items` and `vew --profile prod pipelines get-items` behave identically.

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
