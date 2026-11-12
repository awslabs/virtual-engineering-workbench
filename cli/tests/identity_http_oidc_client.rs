use url::Url;
use wiremock::matchers::{body_string_contains, method, path};
use wiremock::{Mock, MockServer, ResponseTemplate};

use vew::identity::adapters::http_oidc_client::HttpOidcClient;
use vew::identity::domain::error::IdentityError;
use vew::identity::domain::model::{AuthorizationCode, OidcProvider};
use vew::identity::ports::outbound::OidcClient;

fn provider(base_url: &str) -> OidcProvider {
    let base = Url::parse(base_url).unwrap();
    OidcProvider {
        issuer: base.clone(),
        client_id: "test_client".into(),
        authorization_endpoint: base.join("/authorize").unwrap(),
        token_endpoint: base.join("/token").unwrap(),
        revocation_endpoint: Some(base.join("/revoke").unwrap()),
        jwks_uri: base.join("/certs").unwrap(),
        scopes: vec!["openid".into()],
    }
}

fn run_blocking<F, R>(f: F) -> R
where
    F: FnOnce() -> R + Send + 'static,
    R: Send + 'static,
{
    std::thread::spawn(f).join().unwrap()
}

#[tokio::test]
async fn test_exchange_code_success() {
    // Arrange
    let mock_server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/token"))
        .and(body_string_contains("grant_type=authorization_code"))
        .and(body_string_contains("code=auth_code_123"))
        .and(body_string_contains("code_verifier=test_verifier"))
        .respond_with(ResponseTemplate::new(200).set_body_json(serde_json::json!({
            "access_token": "access_tok",
            "id_token": "id_tok",
            "refresh_token": "refresh_tok",
            "expires_in": 3600
        })))
        .mount(&mock_server)
        .await;
    let uri = mock_server.uri();

    // Act
    let resp = run_blocking(move || {
        let client = HttpOidcClient::new();
        client.exchange_code(
            &provider(&uri),
            &AuthorizationCode("auth_code_123".into()),
            "test_verifier",
            "http://localhost/callback",
        )
    })
    .unwrap();

    // Assert
    assert_eq!(resp.access_token, "access_tok");
    assert_eq!(resp.refresh_token, Some("refresh_tok".into()));
}

#[tokio::test]
async fn test_exchange_code_error_response() {
    // Arrange
    let mock_server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/token"))
        .respond_with(ResponseTemplate::new(400).set_body_string("invalid_grant"))
        .mount(&mock_server)
        .await;
    let uri = mock_server.uri();

    // Act
    let result = run_blocking(move || {
        let client = HttpOidcClient::new();
        client.exchange_code(
            &provider(&uri),
            &AuthorizationCode("bad".into()),
            "v",
            "http://localhost/cb",
        )
    });

    // Assert
    assert!(matches!(result, Err(IdentityError::TokenExchange(_))));
}

#[tokio::test]
async fn test_refresh_tokens_success() {
    // Arrange
    let mock_server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/token"))
        .and(body_string_contains("grant_type=refresh_token"))
        .and(body_string_contains("refresh_token=old_refresh"))
        .respond_with(ResponseTemplate::new(200).set_body_json(serde_json::json!({
            "access_token": "new_access",
            "id_token": "new_id",
            "refresh_token": "new_refresh",
            "expires_in": 3600
        })))
        .mount(&mock_server)
        .await;
    let uri = mock_server.uri();

    // Act
    let resp = run_blocking(move || {
        let client = HttpOidcClient::new();
        client.refresh_tokens(&provider(&uri), "old_refresh")
    })
    .unwrap();

    // Assert
    assert_eq!(resp.access_token, "new_access");
}

#[tokio::test]
async fn test_refresh_tokens_without_new_refresh_token() {
    // Arrange
    let mock_server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/token"))
        .respond_with(ResponseTemplate::new(200).set_body_json(serde_json::json!({
            "access_token": "new_access",
            "id_token": "new_id",
            "expires_in": 3600
        })))
        .mount(&mock_server)
        .await;
    let uri = mock_server.uri();

    // Act
    let resp = run_blocking(move || {
        let client = HttpOidcClient::new();
        client.refresh_tokens(&provider(&uri), "old_refresh")
    })
    .unwrap();

    // Assert
    assert!(resp.refresh_token.is_none());
}

#[tokio::test]
async fn test_revoke_token_success() {
    // Arrange
    let mock_server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/revoke"))
        .and(body_string_contains("token=refresh_tok"))
        .respond_with(ResponseTemplate::new(200))
        .mount(&mock_server)
        .await;
    let uri = mock_server.uri();

    // Act
    let result = run_blocking(move || {
        let client = HttpOidcClient::new();
        client.revoke_token(&provider(&uri), "refresh_tok")
    });

    // Assert
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_revoke_token_failure() {
    // Arrange
    let mock_server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/revoke"))
        .respond_with(ResponseTemplate::new(400).set_body_string("invalid_token"))
        .mount(&mock_server)
        .await;
    let uri = mock_server.uri();

    // Act
    let result = run_blocking(move || {
        let client = HttpOidcClient::new();
        client.revoke_token(&provider(&uri), "bad_token")
    });

    // Assert
    assert!(result.is_err());
}

#[test]
fn test_revoke_token_skips_when_no_revocation_endpoint() {
    // Arrange
    let provider = OidcProvider {
        issuer: Url::parse("https://auth.example.com").unwrap(),
        client_id: "test_client".into(),
        authorization_endpoint: Url::parse("https://auth.example.com/authorize").unwrap(),
        token_endpoint: Url::parse("https://auth.example.com/token").unwrap(),
        revocation_endpoint: None,
        jwks_uri: Url::parse("https://auth.example.com/certs").unwrap(),
        scopes: vec!["openid".into()],
    };
    let client = HttpOidcClient::new();

    // Act
    let result = client.revoke_token(&provider, "some_token");

    // Assert
    assert!(result.is_ok());
}
