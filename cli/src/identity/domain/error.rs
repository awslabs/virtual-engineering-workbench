#[derive(Debug, thiserror::Error)]
pub enum IdentityError {
    #[error("not authenticated for profile '{0}'. Run `vew auth login`")]
    NotAuthenticated(String),

    #[error("callback state mismatch: expected '{expected}', got '{actual}'")]
    StateMismatch { expected: String, actual: String },

    #[error("ID token nonce mismatch")]
    NonceMismatch,

    #[error("ID token validation failed: {0}")]
    TokenValidation(String),

    #[error("token exchange failed: {0}")]
    TokenExchange(String),

    #[error("token refresh failed: {0}. Run `vew auth login`")]
    RefreshFailed(String),

    #[error("callback server error: {0}")]
    CallbackError(String),

    #[error("callback timed out after {0} seconds")]
    CallbackTimeout(u64),

    #[error("authentication error from provider: {0}")]
    ProviderError(String),

    #[error("failed to open browser: {0}")]
    BrowserError(String),

    #[error("token store error: {0}")]
    StoreError(#[from] anyhow::Error),

    #[error("OIDC discovery failed: {0}")]
    DiscoveryError(String),
}
