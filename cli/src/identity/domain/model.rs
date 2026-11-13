use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use url::Url;

#[derive(Debug, Clone)]
pub struct OidcProvider {
    pub issuer: Url,
    pub client_id: String,
    pub authorization_endpoint: Url,
    pub token_endpoint: Url,
    pub revocation_endpoint: Option<Url>,
    pub jwks_uri: Url,
    pub scopes: Vec<String>,
}

#[derive(Debug)]
pub struct PkceChallenge {
    pub verifier: String,
    pub challenge: String,
}

#[derive(Debug, Clone, PartialEq)]
pub struct StateParam(pub String);

#[derive(Debug, Clone, PartialEq)]
pub struct Nonce(pub String);

#[derive(Debug)]
pub struct AuthorizationCode(pub String);

#[derive(Debug)]
pub struct CallbackResult {
    pub code: AuthorizationCode,
    pub state: StateParam,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TokenSet {
    pub access_token: String,
    pub id_token: String,
    pub refresh_token: String,
    pub expires_at: DateTime<Utc>,
}

impl TokenSet {
    pub fn is_expired(&self) -> bool {
        Utc::now() >= self.expires_at
    }
}

#[derive(Debug, Deserialize)]
pub struct TokenResponse {
    pub access_token: String,
    pub id_token: String,
    pub refresh_token: Option<String>,
    pub expires_in: i64,
}

#[derive(Debug)]
pub struct IdTokenClaims {
    pub sub: String,
    pub iss: String,
    pub aud: String,
    pub nonce: Option<String>,
}

#[derive(Debug)]
pub struct ValidationParams {
    pub issuer: String,
    pub audience: String,
    pub nonce: Option<Nonce>,
    pub jwks_uri: String,
}

/// Discriminator for which token to return from the store.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TokenType {
    Access,
    Id,
}

/// Result of a login operation, returned to the CLI layer for rendering.
#[derive(Debug, Clone, Serialize)]
pub struct LoginResult {
    /// Access token validity in seconds
    pub access_token_expires_in: i64,
}

impl std::fmt::Display for LoginResult {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "access_token_expires_in: {}s",
            self.access_token_expires_in
        )
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct LogoutResult {
    pub was_logged_in: bool,
}

impl std::fmt::Display for LogoutResult {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "was_logged_in: {}", self.was_logged_in)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::Duration;

    #[test]
    fn test_token_set_is_expired_when_past() {
        // Arrange
        let tokens = TokenSet {
            access_token: "access".to_string(),
            id_token: "id".to_string(),
            refresh_token: "refresh".to_string(),
            expires_at: Utc::now() - Duration::seconds(60),
        };

        // Act
        let expired = tokens.is_expired();

        // Assert
        assert!(expired);
    }

    #[test]
    fn test_token_set_is_not_expired_when_future() {
        // Arrange
        let tokens = TokenSet {
            access_token: "access".to_string(),
            id_token: "id".to_string(),
            refresh_token: "refresh".to_string(),
            expires_at: Utc::now() + Duration::seconds(3600),
        };

        // Act
        let expired = tokens.is_expired();

        // Assert
        assert!(!expired);
    }
}
