use crate::debug_log;
use crate::shared::auth::{AuthProvider, BearerAuthProvider};
use crate::shared::http::blocking_client;
use crate::vew_api::domain::error::VewApiError;
use crate::vew_api::ports::outbound::SpecFetcher;

pub struct HttpSpecFetcher<A: AuthProvider = BearerAuthProvider> {
    http: reqwest::blocking::Client,
    auth: A,
}

impl Default for HttpSpecFetcher<BearerAuthProvider> {
    fn default() -> Self {
        Self::new()
    }
}

impl HttpSpecFetcher<BearerAuthProvider> {
    pub fn new() -> Self {
        Self::with_auth(BearerAuthProvider)
    }
}

impl<A: AuthProvider> HttpSpecFetcher<A> {
    pub fn with_auth(auth: A) -> Self {
        Self {
            http: blocking_client(),
            auth,
        }
    }
}

impl<A: AuthProvider + Send + Sync> SpecFetcher for HttpSpecFetcher<A> {
    fn fetch(&self, url: &str, token: &str) -> Result<serde_json::Value, VewApiError> {
        debug_log!("GET {}", url);
        let (header, value) = self.auth.auth_header(token);
        let resp = self
            .http
            .get(url)
            .header(header, value)
            .send()
            .map_err(|e| VewApiError::NetworkError(e.to_string()))?;

        let status = resp.status().as_u16();
        if status != 200 {
            let body = resp.text().unwrap_or_default();
            debug_log!("spec fetch failed: {} {}", status, body);
            return Err(VewApiError::SpecFetchError {
                url: url.to_string(),
                reason: format!("HTTP {}: {}", status, body),
            });
        }

        resp.json::<serde_json::Value>()
            .map_err(|e| VewApiError::SpecParseError(e.to_string()))
    }
}
