use crate::debug_log;
use crate::identity::domain::error::IdentityError;
use crate::identity::domain::model::{AuthorizationCode, OidcProvider, TokenResponse};
use crate::identity::ports::outbound::OidcClient;
use crate::shared::http::blocking_client;

pub struct HttpOidcClient {
    http: reqwest::blocking::Client,
}

impl Default for HttpOidcClient {
    fn default() -> Self {
        Self::new()
    }
}

impl HttpOidcClient {
    pub fn new() -> Self {
        Self {
            http: blocking_client(),
        }
    }
}

impl OidcClient for HttpOidcClient {
    fn exchange_code(
        &self,
        provider: &OidcProvider,
        code: &AuthorizationCode,
        verifier: &str,
        redirect_uri: &str,
    ) -> Result<TokenResponse, IdentityError> {
        let url = provider.token_endpoint.as_str();
        debug_log!("exchange_code: POST {url}");
        debug_log!("exchange_code: redirect_uri={redirect_uri}");
        debug_log!("exchange_code: client_id={}", provider.client_id);

        let resp = self
            .http
            .post(url)
            .form(&[
                ("grant_type", "authorization_code"),
                ("client_id", provider.client_id.as_str()),
                ("code", &code.0),
                ("code_verifier", verifier),
                ("redirect_uri", redirect_uri),
            ])
            .send()
            .map_err(|e| {
                debug_log!("exchange_code: request failed: {e}");
                IdentityError::TokenExchange(e.to_string())
            })?;

        let status = resp.status();
        debug_log!("exchange_code: response status={status}");

        if !status.is_success() {
            let body = resp.text().unwrap_or_default();
            debug_log!("exchange_code: error body={body}");
            return Err(IdentityError::TokenExchange(format!(
                "HTTP {status}: {body}"
            )));
        }

        // The response body carries access, ID and refresh tokens, so it is
        // never logged. Parse failures below report the error, not the body.
        let body = resp.text().map_err(|e| {
            debug_log!("exchange_code: failed to read response body: {e}");
            IdentityError::TokenExchange(e.to_string())
        })?;
        debug_log!(
            "exchange_code: response body received, {} bytes",
            body.len()
        );

        serde_json::from_str::<TokenResponse>(&body).map_err(|e| {
            debug_log!("exchange_code: failed to parse response: {e}");
            IdentityError::TokenExchange(e.to_string())
        })
    }

    fn refresh_tokens(
        &self,
        provider: &OidcProvider,
        refresh_token: &str,
    ) -> Result<TokenResponse, IdentityError> {
        let url = provider.token_endpoint.as_str();
        debug_log!("refresh_tokens: POST {url}");

        let resp = self
            .http
            .post(url)
            .form(&[
                ("grant_type", "refresh_token"),
                ("client_id", provider.client_id.as_str()),
                ("refresh_token", refresh_token),
            ])
            .send()
            .map_err(|e| {
                debug_log!("refresh_tokens: request failed: {e}");
                IdentityError::RefreshFailed(e.to_string())
            })?;

        let status = resp.status();
        debug_log!("refresh_tokens: response status={status}");

        if !status.is_success() {
            let body = resp.text().unwrap_or_default();
            debug_log!("refresh_tokens: error body={body}");
            return Err(IdentityError::RefreshFailed(format!(
                "HTTP {status}: {body}"
            )));
        }

        resp.json::<TokenResponse>().map_err(|e| {
            debug_log!("refresh_tokens: failed to parse response: {e}");
            IdentityError::RefreshFailed(e.to_string())
        })
    }

    fn revoke_token(&self, provider: &OidcProvider, token: &str) -> Result<(), IdentityError> {
        let url = match &provider.revocation_endpoint {
            Some(u) => u.as_str().to_string(),
            None => {
                debug_log!("revoke_token: provider has no revocation endpoint, skipping");
                return Ok(());
            }
        };
        debug_log!("revoke_token: POST {url}");

        let resp = self
            .http
            .post(&url)
            .form(&[("token", token), ("client_id", provider.client_id.as_str())])
            .send()
            .map_err(|e| {
                debug_log!("revoke_token: request failed: {e}");
                IdentityError::TokenExchange(e.to_string())
            })?;

        let status = resp.status();
        if !status.is_success() {
            let body = resp.text().unwrap_or_default();
            debug_log!("revoke_token: error status={status} body={body}");
            return Err(IdentityError::TokenExchange(format!(
                "HTTP {status}: {body}"
            )));
        }

        Ok(())
    }
}
