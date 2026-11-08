#[derive(Debug, thiserror::Error)]
pub enum ConfigError {
    #[error("profile name cannot be empty")]
    EmptyProfileName,

    #[error("invalid profile name '{name}': must not contain path separators")]
    InvalidProfileName { name: String },

    #[error("no --profile specified and no default_profile set in ~/.vew/config")]
    NoProfileSpecified,

    #[error("profile '{name}' not found. Available: {available:?}")]
    ProfileNotFound {
        name: String,
        available: Vec<String>,
    },

    #[error("profile '{profile}' is missing required property '{property}'")]
    MissingProperty { profile: String, property: String },

    #[error("failed to read config: {0}")]
    ReadError(#[from] anyhow::Error),
}
