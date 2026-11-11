//! A secret must not reach the debug log or an error message.
//!
//! Each test plants a recognisable marker in the value a provider controls, runs
//! the adapter against a mock endpoint, and asserts the marker appears in
//! neither `debug_log!` output nor the returned error. `debug_log!` writes to
//! stderr, which a test cannot read back, so the assertions depend on the
//! in-memory capture compiled by the `log-capture` feature. Without the feature
//! this file compiles to nothing, so CI runs `cargo test --features log-capture`.
#![cfg(feature = "log-capture")]

use url::Url;
use wiremock::matchers::{method, path};
use wiremock::{Mock, MockServer, ResponseTemplate};

use vew::identity::adapters::http_oidc_client::HttpOidcClient;
use vew::identity::domain::model::{AuthorizationCode, OidcProvider};
use vew::identity::ports::outbound::OidcClient;
use vew::shared::verbose::capture;

// One marker per test: the capture buffer is shared by the whole binary, so a
// test asserts only that its own marker never appears. Unique markers remove any
// need to serialise the tests.
const EXCHANGE_ERROR: &str = "MARKER-exchange-error-7f1a";
const EXCHANGE_CODE_ECHO: &str = "MARKER-exchange-code-9c2b";
const EXCHANGE_PARSE: &str = "MARKER-exchange-parse-3d4e";
const EXCHANGE_SUCCESS: &str = "MARKER-exchange-success-5a6f";
const REVOKE_ECHO: &str = "MARKER-revoke-echo-8b7c";
const REFRESH_ECHO: &str = "MARKER-refresh-echo-2e9d";

fn provider(base: &str) -> OidcProvider {
    OidcProvider {
        issuer: Url::parse(base).unwrap(),
        authorization_endpoint: Url::parse(&format!("{base}/authorize")).unwrap(),
        token_endpoint: Url::parse(&format!("{base}/token")).unwrap(),
        revocation_endpoint: Some(Url::parse(&format!("{base}/revoke")).unwrap()),
        jwks_uri: Url::parse(&format!("{base}/.well-known/jwks.json")).unwrap(),
        client_id: "client123".to_string(),
        scopes: vec!["openid".to_string()],
    }
}

/// Runs a blocking adapter call off the tokio worker thread, since the adapters
/// use reqwest::blocking.
fn blocking<F, R>(f: F) -> R
where
    F: FnOnce() -> R + Send + 'static,
    R: Send + 'static,
{
    std::thread::spawn(f).join().unwrap()
}

fn assert_no_secret(context: &str, marker: &str, error_text: &str) {
    let log = capture::joined();
    assert!(
        !log.contains(marker),
        "{context}: the secret reached the debug log:\n{log}"
    );
    assert!(
        !error_text.contains(marker),
        "{context}: the secret reached the error text: {error_text}"
    );
}

#[tokio::test]
async fn token_exchange_error_body_is_not_logged_or_surfaced() {
    capture::enable();
    let server = MockServer::start().await;
    // A real token-endpoint failure echoes the submitted grant, and
    // error_description is free text the provider chooses.
    let body = format!(
        r#"{{"error":"invalid_grant","error_description":"refresh_token={EXCHANGE_ERROR}"}}"#
    );
    Mock::given(method("POST"))
        .and(path("/token"))
        .respond_with(ResponseTemplate::new(400).set_body_string(body))
        .mount(&server)
        .await;

    let p = provider(&server.uri());
    let err = blocking(move || {
        HttpOidcClient::new().exchange_code(&p, &AuthorizationCode("c".into()), "v", "http://x")
    })
    .expect_err("a 400 must fail");

    let text = err.to_string();
    assert_no_secret("exchange_code", EXCHANGE_ERROR, &text);
    assert!(
        text.contains("invalid_grant"),
        "the standard error code should survive: {text}"
    );
}

#[tokio::test]
async fn token_exchange_rejects_a_nonstandard_error_code_verbatim() {
    capture::enable();
    let server = MockServer::start().await;
    let body = format!(r#"{{"error":"{EXCHANGE_CODE_ECHO}"}}"#);
    Mock::given(method("POST"))
        .and(path("/token"))
        .respond_with(ResponseTemplate::new(400).set_body_string(body))
        .mount(&server)
        .await;

    let p = provider(&server.uri());
    let err = blocking(move || {
        HttpOidcClient::new().exchange_code(&p, &AuthorizationCode("c".into()), "v", "http://x")
    })
    .expect_err("a 400 must fail");

    let text = err.to_string();
    assert_no_secret("exchange_code non-standard code", EXCHANGE_CODE_ECHO, &text);
    assert!(
        text.contains("unrecognised_error"),
        "a non-RFC code should collapse to the placeholder: {text}"
    );
}

#[tokio::test]
async fn a_malformed_token_response_does_not_quote_the_rejected_value() {
    capture::enable();
    let server = MockServer::start().await;
    // serde reports `invalid type: string "<value>", expected i64`, which quotes
    // whatever sat in the field — here a token-shaped marker in expires_in.
    let body = format!(r#"{{"access_token":"a","id_token":"b","expires_in":"{EXCHANGE_PARSE}"}}"#);
    Mock::given(method("POST"))
        .and(path("/token"))
        .respond_with(ResponseTemplate::new(200).set_body_string(body))
        .mount(&server)
        .await;

    let p = provider(&server.uri());
    let err = blocking(move || {
        HttpOidcClient::new().exchange_code(&p, &AuthorizationCode("c".into()), "v", "http://x")
    })
    .expect_err("a malformed body must fail");

    assert_no_secret(
        "exchange_code parse failure",
        EXCHANGE_PARSE,
        &err.to_string(),
    );
}

#[tokio::test]
async fn a_successful_token_response_body_is_never_logged() {
    capture::enable();
    let server = MockServer::start().await;
    let body = format!(
        r#"{{"access_token":"{EXCHANGE_SUCCESS}","id_token":"{EXCHANGE_SUCCESS}","refresh_token":"{EXCHANGE_SUCCESS}","expires_in":3600,"token_type":"Bearer"}}"#
    );
    Mock::given(method("POST"))
        .and(path("/token"))
        .respond_with(ResponseTemplate::new(200).set_body_string(body))
        .mount(&server)
        .await;

    let p = provider(&server.uri());
    let result = blocking(move || {
        HttpOidcClient::new().exchange_code(&p, &AuthorizationCode("c".into()), "v", "http://x")
    });
    assert!(result.is_ok(), "the response should parse: {result:?}");

    let log = capture::joined();
    assert!(
        !log.contains(EXCHANGE_SUCCESS),
        "a token reached the debug log:\n{log}"
    );
}

#[tokio::test]
async fn revocation_error_body_does_not_echo_the_token() {
    capture::enable();
    let server = MockServer::start().await;
    let body =
        format!(r#"{{"error":"invalid_request","error_description":"token={REVOKE_ECHO}"}}"#);
    Mock::given(method("POST"))
        .and(path("/revoke"))
        .respond_with(ResponseTemplate::new(400).set_body_string(body))
        .mount(&server)
        .await;

    let p = provider(&server.uri());
    let err = blocking(move || HttpOidcClient::new().revoke_token(&p, REVOKE_ECHO))
        .expect_err("a 400 must fail");

    assert_no_secret("revoke_token", REVOKE_ECHO, &err.to_string());
}

#[tokio::test]
async fn refresh_error_body_does_not_echo_the_refresh_token() {
    capture::enable();
    let server = MockServer::start().await;
    let body = format!(r#"{{"error":"invalid_grant","error_description":"was {REFRESH_ECHO}"}}"#);
    Mock::given(method("POST"))
        .and(path("/token"))
        .respond_with(ResponseTemplate::new(400).set_body_string(body))
        .mount(&server)
        .await;

    let p = provider(&server.uri());
    let err = blocking(move || HttpOidcClient::new().refresh_tokens(&p, REFRESH_ECHO))
        .expect_err("a 400 must fail");

    assert_no_secret("refresh_tokens", REFRESH_ECHO, &err.to_string());
}
