use url::Url;

use vew::identity::adapters::http_oidc_discovery::HttpOidcDiscovery;
use vew::identity::domain::error::IdentityError;
use vew::identity::ports::outbound::OidcDiscovery;

// A success-path test against a mock server is not possible here: the adapter
// requires an https issuer and wiremock serves plain http. The happy path is
// covered where the document is parsed, in the adapter's own unit tests; these
// two cover the rejections the adapter is responsible for.

#[test]
fn test_discovery_rejects_http_issuer() {
    // Arrange
    let discovery = HttpOidcDiscovery::new();
    let issuer = Url::parse("http://insecure.example.com").unwrap();

    // Act
    let result = discovery.resolve(&issuer, "client123");

    // Assert
    match result {
        Err(IdentityError::DiscoveryError(msg)) => {
            assert!(msg.contains("HTTPS"), "expected HTTPS error, got: {msg}");
        }
        other => panic!("expected DiscoveryError, got {:?}", other),
    }
}

#[test]
fn test_discovery_network_error() {
    // Arrange
    let discovery = HttpOidcDiscovery::new();
    let issuer = Url::parse("https://localhost:1").unwrap(); // nothing listening

    // Act
    let result = discovery.resolve(&issuer, "client123");

    // Assert
    assert!(matches!(result, Err(IdentityError::DiscoveryError(_))));
}
