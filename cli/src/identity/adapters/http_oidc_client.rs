use crate::debug_log;
use crate::identity::adapters::oauth_error::describe_http_failure;
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
            // The token endpoint's error body can contain a refresh token, and
            // error_description is provider-controlled free text, so only the
            // status and an RFC-defined error code are reported or logged.
            let body = resp.text().unwrap_or_default();
            let safe = describe_http_failure(status, &body);
            debug_log!("exchange_code: failed, {safe}");
            return Err(IdentityError::TokenExchange(safe));
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
            // A serde error quotes the value it rejected, e.g.
            // `invalid type: string "<access token>"`, so only its position is
            // reported — never the message.
            debug_log!(
                "exchange_code: malformed token response at line {} column {}",
                e.line(),
                e.column()
            );
            IdentityError::TokenExchange("malformed token response".into())
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
            let safe = describe_http_failure(status, &body);
            debug_log!("refresh_tokens: failed, {safe}");
            return Err(IdentityError::RefreshFailed(safe));
        }

        resp.json::<TokenResponse>().map_err(|_| {
            debug_log!("refresh_tokens: malformed token response");
            IdentityError::RefreshFailed("malformed token response".into())
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
            // A revocation error body echoes the submitted token
            // (`token=<value>`), so it is never logged or surfaced.
            let body = resp.text().unwrap_or_default();
            let safe = describe_http_failure(status, &body);
            debug_log!("revoke_token: failed, {safe}");
            return Err(IdentityError::TokenExchange(safe));
        }

        Ok(())
    }
}
