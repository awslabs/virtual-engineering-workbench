use base64::Engine;
use base64::engine::general_purpose::URL_SAFE_NO_PAD;
use sha2::{Digest, Sha256};
use vew::identity::adapters::system_crypto_provider::SystemCryptoProvider;
use vew::identity::ports::outbound::CryptoProvider;

#[test]
fn test_pkce_verifier_length() {
    // Arrange
    let crypto = SystemCryptoProvider::new();

    // Act
    let pkce = crypto.generate_pkce_challenge();

    // Assert
    assert_eq!(pkce.verifier.len(), 128);
}

#[test]
fn test_pkce_challenge_is_valid_base64url_sha256() {
    // Arrange
    let crypto = SystemCryptoProvider::new();

    // Act
    let pkce = crypto.generate_pkce_challenge();

    // Assert
    let expected = URL_SAFE_NO_PAD.encode(Sha256::digest(pkce.verifier.as_bytes()));
    assert_eq!(pkce.challenge, expected);
}

#[test]
fn test_state_is_at_least_32_bytes_encoded() {
    // Arrange
    let crypto = SystemCryptoProvider::new();

    // Act
    let state = crypto.generate_state();

    // Assert
    let decoded = URL_SAFE_NO_PAD.decode(&state.0).unwrap();
    assert!(decoded.len() >= 32);
}

#[test]
fn test_nonce_is_at_least_32_bytes_encoded() {
    // Arrange
    let crypto = SystemCryptoProvider::new();

    // Act
    let nonce = crypto.generate_nonce();

    // Assert
    let decoded = URL_SAFE_NO_PAD.decode(&nonce.0).unwrap();
    assert!(decoded.len() >= 32);
}

#[test]
fn test_pkce_generates_unique_values() {
    // Arrange
    let crypto = SystemCryptoProvider::new();

    // Act
    let a = crypto.generate_pkce_challenge();
    let b = crypto.generate_pkce_challenge();

    // Assert
    assert_ne!(a.verifier, b.verifier);
}
