use crate::shared::constants::USER_AGENT;

/// Builds the shared `reqwest::blocking::Client` used by every HTTP adapter.
///
/// Centralising construction guarantees the `User-Agent` header is always set
/// (WAF rules block empty UAs) and keeps adapters free of reqwest boilerplate.
pub fn blocking_client() -> reqwest::blocking::Client {
    reqwest::blocking::Client::builder()
        .user_agent(USER_AGENT)
        .build()
        .expect("failed to build HTTP client")
}
