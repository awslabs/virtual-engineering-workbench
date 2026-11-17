#[derive(Debug, thiserror::Error)]
pub enum VewApiError {
    #[error("unknown bounded context '{name}'. Available: {available:?}")]
    UnknownBoundedContext {
        name: String,
        available: Vec<String>,
    },

    #[error("unknown operation '{name}' for {bc}. Run `vew {bc}` to list available operations")]
    UnknownOperation { name: String, bc: String },

    #[error("missing required parameter '{param}' for operation '{operation}'")]
    MissingRequiredParam { param: String, operation: String },

    #[error("failed to fetch spec from {url}: {reason}")]
    SpecFetchError { url: String, reason: String },

    #[error("failed to parse OpenAPI spec: {0}")]
    SpecParseError(String),

    #[error("cache error: {0}")]
    CacheError(String),

    #[error("API call failed: {status} {body}")]
    InvocationError { status: u16, body: String },

    #[error("network error: {0}")]
    NetworkError(String),

    #[error(
        "no enabled bounded contexts found for profile '{profile}'. Run `vew init` to discover available services"
    )]
    NoEnabledContexts { profile: String },
}
