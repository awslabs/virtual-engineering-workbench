# Changelog

## 1.2.0 (2026-05-12)

### Features

- **Auth:** `--no-browser` flag on `vew auth login` prints the login URL to stdout instead of opening a browser (also settable via the `VEW_NO_BROWSER` environment variable). Enables headless login from SSH sessions, containers, and CI.

## 1.1.0 (2026-04-29)

### Features

- **Init:** new `vew init` command fetches and caches API specs for all enabled bounded contexts.

### Fixes

- **Help:** each bounded context's help now includes summary and description text pulled from its OpenAPI spec.
- **Help:** cleaner formatting and improved readability.
- **Security:** profile names are validated against shell metacharacters before use.

## 1.0.2 (2026-04-24)

### Fixes

- **Auth:** login now works with any OIDC-compliant provider. Endpoints are resolved automatically via OIDC Discovery 1.0 (RFC 8414); previously the CLI hardcoded Cognito-specific URL paths.
