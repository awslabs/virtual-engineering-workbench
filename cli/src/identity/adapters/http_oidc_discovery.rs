use serde::Deserialize;
use url::Url;

use crate::debug_log;
use crate::identity::domain::error::IdentityError;
use crate::identity::domain::model::OidcProvider;
use crate::identity::ports::outbound::OidcDiscovery;
use crate::shared::http::blocking_client;

#[derive(Deserialize)]
struct DiscoveryDocument {
    issuer: String,
    authorization_endpoint: String,
    token_endpoint: String,
    revocation_endpoint: Option<String>,
    jwks_uri: String,
}

pub struct HttpOidcDiscovery {
    http: reqwest::blocking::Client,
}

impl Default for HttpOidcDiscovery {
    fn default() -> Self {
        Self::new()
    }
}

impl HttpOidcDiscovery {
    pub fn new() -> Self {
        Self {
            http: blocking_client(),
        }
    }
}

impl OidcDiscovery for HttpOidcDiscovery {
    fn resolve(&self, issuer: &Url, client_id: &str) -> Result<OidcProvider, IdentityError> {
        if issuer.scheme() != "https" {
            return Err(IdentityError::DiscoveryError(format!(
                "issuer must use HTTPS: {issuer}"
            )));
        }

        let discovery_url = format!(
            "{}/.well-known/openid-configuration",
            issuer.as_str().trim_end_matches('/')
        );
        debug_log!("discovery: GET {discovery_url}");

        let resp = self.http.get(&discovery_url).send().map_err(|e| {
            debug_log!("discovery: fetch failed: {e}");
            IdentityError::DiscoveryError(format!("fetch failed: {e}"))
        })?;

        let status = resp.status();
        debug_log!("discovery: response status={status}");

        if !status.is_success() {
            let body = resp.text().unwrap_or_default();
            debug_log!("discovery: error body={body}");
            return Err(IdentityError::DiscoveryError(format!(
                "HTTP {status}: {body}"
            )));
        }

        let doc: DiscoveryDocument = resp.json().map_err(|e| {
            debug_log!("discovery: invalid JSON: {e}");
            IdentityError::DiscoveryError(format!("invalid JSON: {e}"))
        })?;

        let expected = issuer.as_str().trim_end_matches('/');
        let actual = doc.issuer.trim_end_matches('/');
        if actual != expected {
            return Err(IdentityError::DiscoveryError(format!(
                "issuer mismatch: expected '{expected}', got '{actual}'"
            )));
        }

        let authorization_endpoint =
            parse_url(&doc.authorization_endpoint, "authorization_endpoint")?;
        let token_endpoint = parse_url(&doc.token_endpoint, "token_endpoint")?;
        let revocation_endpoint = doc
            .revocation_endpoint
            .map(|u| parse_url(&u, "revocation_endpoint"))
            .transpose()?;
        let jwks_uri = parse_url(&doc.jwks_uri, "jwks_uri")?;

        Ok(OidcProvider {
            issuer: issuer.clone(),
            client_id: client_id.to_string(),
            authorization_endpoint,
            token_endpoint,
            revocation_endpoint,
            jwks_uri,
            scopes: vec!["openid".into(), "profile".into(), "email".into()],
        })
    }
}

fn parse_url(raw: &str, field: &str) -> Result<Url, IdentityError> {
    let url = Url::parse(raw)
        .map_err(|e| IdentityError::DiscoveryError(format!("invalid {field} URL: {e}")))?;
    if url.scheme() != "https" {
        return Err(IdentityError::DiscoveryError(format!(
            "{field} must use HTTPS: {url}"
        )));
    }
    Ok(url)
}
