use base64::Engine;
use jsonwebtoken::{Algorithm, EncodingKey, Header, encode};
use rsa::traits::PublicKeyParts;
use serde::Serialize;
use wiremock::matchers::{method, path};
use wiremock::{Mock, MockServer, ResponseTemplate};

use vew::identity::adapters::jwt_token_validator::JwtTokenValidator;
use vew::identity::domain::error::IdentityError;
use vew::identity::domain::model::{Nonce, ValidationParams};
use vew::identity::ports::outbound::TokenValidator;

/// Run a blocking closure outside the tokio runtime.
fn run_blocking<F, R>(f: F) -> R
where
    F: FnOnce() -> R + Send + 'static,
    R: Send + 'static,
{
    std::thread::spawn(f).join().unwrap()
}

#[derive(Serialize)]
struct TestClaims {
    sub: String,
    iss: String,
    aud: String,
    exp: i64,
    nonce: Option<String>,
}

fn generate_rsa_keys() -> (EncodingKey, jsonwebtoken::jwk::Jwk) {
    use rsa::RsaPrivateKey;
    use rsa::pkcs1::EncodeRsaPrivateKey;

    let mut rng = rand::thread_rng();
    let private_key = RsaPrivateKey::new(&mut rng, 2048).unwrap();
    let private_pem = private_key
        .to_pkcs1_pem(rsa::pkcs1::LineEnding::LF)
        .unwrap();
    let encoding_key = EncodingKey::from_rsa_pem(private_pem.as_bytes()).unwrap();

    let public_key = private_key.to_public_key();
    let n = base64::engine::general_purpose::URL_SAFE_NO_PAD.encode(public_key.n().to_bytes_be());
    let e = base64::engine::general_purpose::URL_SAFE_NO_PAD.encode(public_key.e().to_bytes_be());

    let jwk = serde_json::from_value(serde_json::json!({
        "kty": "RSA",
        "kid": "test-kid",
        "use": "sig",
        "alg": "RS256",
        "n": n,
        "e": e,
    }))
    .unwrap();

    (encoding_key, jwk)
}

fn sign_jwt(key: &EncodingKey, claims: &TestClaims) -> String {
    let mut header = Header::new(Algorithm::RS256);
    header.kid = Some("test-kid".into());
    encode(&header, claims, key).unwrap()
}

async fn setup_jwks_server(jwk: &jsonwebtoken::jwk::Jwk) -> MockServer {
    let mock_server = MockServer::start().await;
    let jwks = serde_json::json!({ "keys": [jwk] });
    Mock::given(method("GET"))
        .and(path("/certs"))
        .respond_with(ResponseTemplate::new(200).set_body_json(jwks))
        .mount(&mock_server)
        .await;
    mock_server
}

#[tokio::test]
async fn test_validate_valid_id_token() {
    // Arrange
    let (key, jwk) = generate_rsa_keys();
    let server = setup_jwks_server(&jwk).await;
    let issuer = server.uri();
    let token = sign_jwt(
        &key,
        &TestClaims {
            sub: "user123".into(),
            iss: issuer.clone(),
            aud: "client123".into(),
            exp: chrono::Utc::now().timestamp() + 3600,
            nonce: Some("test_nonce".into()),
        },
    );

    // Act
    let result = run_blocking(move || {
        JwtTokenValidator::new().validate_id_token(
            &token,
            &ValidationParams {
                issuer: issuer.clone(),
                audience: "client123".into(),
                nonce: Some(Nonce("test_nonce".into())),
                jwks_uri: format!("{issuer}/certs"),
            },
        )
    });

    // Assert
    assert_eq!(result.unwrap().sub, "user123");
}

#[tokio::test]
async fn test_validate_expired_token() {
    // Arrange
    let (key, jwk) = generate_rsa_keys();
    let server = setup_jwks_server(&jwk).await;
    let issuer = server.uri();
    let token = sign_jwt(
        &key,
        &TestClaims {
            sub: "user".into(),
            iss: issuer.clone(),
            aud: "client".into(),
            exp: 1000,
            nonce: None,
        },
    );

    // Act
    let result = run_blocking(move || {
        JwtTokenValidator::new().validate_id_token(
            &token,
            &ValidationParams {
                issuer: issuer.clone(),
                audience: "client".into(),
                nonce: None,
                jwks_uri: format!("{issuer}/certs"),
            },
        )
    });

    // Assert
    assert!(matches!(result, Err(IdentityError::TokenValidation(_))));
}

#[tokio::test]
async fn test_validate_wrong_issuer() {
    // Arrange
    let (key, jwk) = generate_rsa_keys();
    let server = setup_jwks_server(&jwk).await;
    let token = sign_jwt(
        &key,
        &TestClaims {
            sub: "user".into(),
            iss: "https://wrong-issuer.com".into(),
            aud: "client".into(),
            exp: chrono::Utc::now().timestamp() + 3600,
            nonce: None,
        },
    );
    let issuer = server.uri();

    // Act
    let result = run_blocking(move || {
        JwtTokenValidator::new().validate_id_token(
            &token,
            &ValidationParams {
                issuer: issuer.clone(),
                audience: "client".into(),
                nonce: None,
                jwks_uri: format!("{issuer}/certs"),
            },
        )
    });

    // Assert
    assert!(matches!(result, Err(IdentityError::TokenValidation(_))));
}

#[tokio::test]
async fn test_validate_wrong_audience() {
    // Arrange
    let (key, jwk) = generate_rsa_keys();
    let server = setup_jwks_server(&jwk).await;
    let issuer = server.uri();
    let token = sign_jwt(
        &key,
        &TestClaims {
            sub: "user".into(),
            iss: issuer.clone(),
            aud: "wrong_client".into(),
            exp: chrono::Utc::now().timestamp() + 3600,
            nonce: None,
        },
    );

    // Act
    let result = run_blocking(move || {
        JwtTokenValidator::new().validate_id_token(
            &token,
            &ValidationParams {
                issuer: issuer.clone(),
                audience: "correct_client".into(),
                nonce: None,
                jwks_uri: format!("{issuer}/certs"),
            },
        )
    });

    // Assert
    assert!(matches!(result, Err(IdentityError::TokenValidation(_))));
}

#[tokio::test]
async fn test_validate_nonce_mismatch() {
    // Arrange
    let (key, jwk) = generate_rsa_keys();
    let server = setup_jwks_server(&jwk).await;
    let issuer = server.uri();
    let token = sign_jwt(
        &key,
        &TestClaims {
            sub: "user".into(),
            iss: issuer.clone(),
            aud: "client".into(),
            exp: chrono::Utc::now().timestamp() + 3600,
            nonce: Some("actual_nonce".into()),
        },
    );

    // Act
    let result = run_blocking(move || {
        JwtTokenValidator::new().validate_id_token(
            &token,
            &ValidationParams {
                issuer: issuer.clone(),
                audience: "client".into(),
                nonce: Some(Nonce("expected_nonce".into())),
                jwks_uri: format!("{issuer}/certs"),
            },
        )
    });

    // Assert
    assert!(matches!(result, Err(IdentityError::NonceMismatch)));
}

#[tokio::test]
async fn test_validate_rejects_hs256() {
    // Arrange
    let (_, jwk) = generate_rsa_keys();
    let server = setup_jwks_server(&jwk).await;
    let issuer = server.uri();
    let token = encode(
        &Header::new(Algorithm::HS256),
        &TestClaims {
            sub: "user".into(),
            iss: issuer.clone(),
            aud: "client".into(),
            exp: chrono::Utc::now().timestamp() + 3600,
            nonce: None,
        },
        &EncodingKey::from_secret(b"secret"),
    )
    .unwrap();

    // Act
    let result = run_blocking(move || {
        JwtTokenValidator::new().validate_id_token(
            &token,
            &ValidationParams {
                issuer: issuer.clone(),
                audience: "client".into(),
                nonce: None,
                jwks_uri: format!("{issuer}/certs"),
            },
        )
    });

    // Assert
    assert!(matches!(result, Err(IdentityError::TokenValidation(_))));
}
