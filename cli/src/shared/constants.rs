pub const VEW_DIR: &str = ".vew";
pub const CACHE_DIR: &str = "cache";
pub const SWAGGER_SUFFIX: &str = "/_swagger?format=json";
pub const ENABLED_CONTEXTS_FILE: &str = "_enabled.json";

macro_rules! user_agent {
    () => {
        concat!("vew-cli/", env!("CARGO_PKG_VERSION"))
    };
}
pub const USER_AGENT: &str = user_agent!();
