use url::Url;

use super::model::BoundedContext;

pub struct ExecuteCommand {
    pub bounded_context: BoundedContext,
    pub operation: Option<String>,
    pub raw_args: Vec<String>,
    pub api_endpoint: Url,
    pub access_token: String,
    pub refresh_cache: bool,
    pub profile_name: String,
}

pub struct InitAllCaches {
    pub api_endpoint: Url,
    pub access_token: String,
    pub profile_name: String,
}

pub struct ListEnabledContexts {
    pub profile_name: String,
}
