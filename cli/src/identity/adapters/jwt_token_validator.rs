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

/// A fixed name for a jsonwebtoken error, safe to log and show.
///
/// Neither the error's Display nor its kind's Debug output is safe: several
/// variants carry text, and `Json` wraps the serde error, which quotes the
/// rejected claim value ("invalid type: integer 4242, expected a string").
/// Name the variant and drop whatever it carries.
fn error_kind_label(kind: &jsonwebtoken::errors::ErrorKind) -> &'static str {
    use jsonwebtoken::errors::ErrorKind;
    match kind {
        ErrorKind::InvalidToken => "InvalidToken",
        ErrorKind::InvalidSignature => "InvalidSignature",
        ErrorKind::InvalidEcdsaKey => "InvalidEcdsaKey",
        ErrorKind::InvalidEddsaKey => "InvalidEddsaKey",
        ErrorKind::InvalidRsaKey(_) => "InvalidRsaKey",
        ErrorKind::RsaFailedSigning => "RsaFailedSigning",
        ErrorKind::Signing(_) => "Signing",
        ErrorKind::InvalidAlgorithmName => "InvalidAlgorithmName",
        ErrorKind::InvalidKeyFormat => "InvalidKeyFormat",
        ErrorKind::MissingRequiredClaim(_) => "MissingRequiredClaim",
        ErrorKind::InvalidClaimFormat(_) => "InvalidClaimFormat",
        ErrorKind::ExpiredSignature => "ExpiredSignature",
        ErrorKind::InvalidIssuer => "InvalidIssuer",
        ErrorKind::InvalidAudience => "InvalidAudience",
        ErrorKind::InvalidSubject => "InvalidSubject",
        ErrorKind::ImmatureSignature => "ImmatureSignature",
        ErrorKind::InvalidAlgorithm => "InvalidAlgorithm",
        ErrorKind::MissingAlgorithm => "MissingAlgorithm",
        ErrorKind::Base64(_) => "Base64",
        ErrorKind::Json(_) => "Json",
        ErrorKind::Utf8(_) => "Utf8",
        ErrorKind::Provider(_) => "Provider",
        // ErrorKind is #[non_exhaustive].
        _ => "Other",
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

        // jsonwebtoken error messages can quote token content, and the kid
        // identifies the signing key, so neither is logged or surfaced.
        let header = jsonwebtoken::decode_header(id_token)
            .map_err(|_| IdentityError::TokenValidation("malformed token header".into()))?;
        debug_log!("validate_id_token: token header parsed");

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
        // The JWKS is public key material, but logging it wholesale is noise
        // and it is attacker-controlled when the endpoint is; log its size only.
        debug_log!(
            "validate_id_token: JWKS body received, {} bytes",
            body.len()
        );

        let jwks: jsonwebtoken::jwk::JwkSet = serde_json::from_str(&body)
            .map_err(|_| IdentityError::TokenValidation("malformed JWKS".into()))?;

        let kid = header.kid.as_deref().unwrap_or("");
        let jwk = jwks
            .find(kid)
            .ok_or_else(|| IdentityError::TokenValidation("no matching JWK for token".into()))?;

        let key = DecodingKey::from_jwk(jwk)
            .map_err(|_| IdentityError::TokenValidation("unusable signing key".into()))?;

        let token_data = decode::<Claims>(id_token, &key, &validation).map_err(|e| {
            let kind = error_kind_label(e.kind());
            debug_log!("validate_id_token: decode failed, kind={kind}");
            IdentityError::TokenValidation(format!("token rejected: {kind}"))
        })?;

        let claims = token_data.claims;

        if let Some(ref expected_nonce) = params.nonce {
            match &claims.nonce {
                Some(actual) if actual == &expected_nonce.0 => {}
                _ => return Err(IdentityError::NonceMismatch),
            }
        }

        // sub identifies the user; the success line carries no claim values.
        debug_log!("validate_id_token: success");
        Ok(IdTokenClaims {
            sub: claims.sub,
            iss: claims.iss,
            aud: claims.aud.first().to_string(),
            nonce: claims.nonce,
        })
    }
}
