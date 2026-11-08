use jsonwebtoken::{Algorithm, DecodingKey, Validation, decode};
use serde::Deserialize;

use crate::debug_log;
use crate::identity::domain::error::IdentityError;
use crate::identity::domain::model::{IdTokenClaims, ValidationParams};
use crate::identity::ports::outbound::TokenValidator;
use crate::shared::http::blocking_client;

#[derive(Debug, Deserialize)]
struct Claims {
    sub: String,
    iss: String,
    aud: StringOrVec,
    nonce: Option<String>,
}

#[derive(Debug, Deserialize)]
#[serde(untagged)]
enum StringOrVec {
    Single(String),
    Multiple(Vec<String>),
}

impl StringOrVec {
    fn first(&self) -> &str {
        match self {
            Self::Single(s) => s,
            Self::Multiple(v) => v.first().map(|s| s.as_str()).unwrap_or(""),
        }
    }
}

pub struct JwtTokenValidator {
    http: reqwest::blocking::Client,
}

impl Default for JwtTokenValidator {
    fn default() -> Self {
        Self::new()
    }
}

impl JwtTokenValidator {
    pub fn new() -> Self {
        Self {
            http: blocking_client(),
        }
    }
}

impl TokenValidator for JwtTokenValidator {
    fn validate_id_token(
        &self,
        id_token: &str,
        params: &ValidationParams,
    ) -> Result<IdTokenClaims, IdentityError> {
        let mut validation = Validation::new(Algorithm::RS256);
        validation.set_issuer(&[&params.issuer]);
        validation.set_audience(&[&params.audience]);
        validation.set_required_spec_claims(&["exp", "iss", "aud"]);

        let header = jsonwebtoken::decode_header(id_token)
            .map_err(|e| IdentityError::TokenValidation(e.to_string()))?;
        debug_log!("validate_id_token: kid={:?}", header.kid);

        let jwks_url = &params.jwks_uri;
        debug_log!("validate_id_token: fetching JWKS from {jwks_url}");

        let jwks_resp = self
            .http
            .get(jwks_url)
            .send()
            .map_err(|e| IdentityError::TokenValidation(format!("JWKS fetch failed: {e}")))?;

        let status = jwks_resp.status();
        debug_log!("validate_id_token: JWKS response status={status}");

        if !status.is_success() {
            return Err(IdentityError::TokenValidation(format!(
                "JWKS endpoint returned error status: {status}"
            )));
        }

        let body = jwks_resp
            .text()
            .map_err(|e| IdentityError::TokenValidation(format!("JWKS read failed: {e}")))?;
        debug_log!("validate_id_token: JWKS body={body}");

        let jwks: jsonwebtoken::jwk::JwkSet = serde_json::from_str(&body)
            .map_err(|e| IdentityError::TokenValidation(format!("JWKS parse failed: {e}")))?;

        let kid = header.kid.as_deref().unwrap_or("");
        let jwk = jwks.find(kid).ok_or_else(|| {
            IdentityError::TokenValidation(format!("no JWK found for kid '{kid}'"))
        })?;

        let key = DecodingKey::from_jwk(jwk)
            .map_err(|e| IdentityError::TokenValidation(e.to_string()))?;

        let token_data = decode::<Claims>(id_token, &key, &validation).map_err(|e| {
            debug_log!("validate_id_token: decode failed: {e}");
            IdentityError::TokenValidation(e.to_string())
        })?;

        let claims = token_data.claims;

        if let Some(ref expected_nonce) = params.nonce {
            match &claims.nonce {
                Some(actual) if actual == &expected_nonce.0 => {}
                _ => return Err(IdentityError::NonceMismatch),
            }
        }

        debug_log!("validate_id_token: success, sub={}", claims.sub);
        Ok(IdTokenClaims {
            sub: claims.sub,
            iss: claims.iss,
            aud: claims.aud.first().to_string(),
            nonce: claims.nonce,
        })
    }
}
