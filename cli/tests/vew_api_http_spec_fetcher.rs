use wiremock::matchers::{header, method};
use wiremock::{Mock, MockServer, ResponseTemplate};

use vew::shared::constants::USER_AGENT;
use vew::vew_api::adapters::http_spec_fetcher::HttpSpecFetcher;
use vew::vew_api::domain::error::VewApiError;
use vew::vew_api::ports::outbound::SpecFetcher;

fn run_blocking<F, R>(f: F) -> R
where
    F: FnOnce() -> R + Send + 'static,
    R: Send + 'static,
{
    std::thread::spawn(f).join().unwrap()
}

#[tokio::test]
async fn test_fetch_success_returns_parsed_json() {
    // Arrange
    let mock_server = MockServer::start().await;
    Mock::given(method("GET"))
        .respond_with(
            ResponseTemplate::new(200)
                .set_body_json(serde_json::json!({"openapi": "3.1.0", "paths": {}})),
        )
        .mount(&mock_server)
        .await;
    let url = format!("{}/spec", mock_server.uri());

    // Act
    let result = run_blocking(move || {
        let fetcher = HttpSpecFetcher::new();
        fetcher.fetch(&url, "test-token")
    });

    // Assert
    let json = result.unwrap();
    assert_eq!(json["openapi"], "3.1.0");
}

#[tokio::test]
async fn test_fetch_non_200_returns_spec_fetch_error() {
    // Arrange
    let mock_server = MockServer::start().await;
    Mock::given(method("GET"))
        .respond_with(ResponseTemplate::new(401).set_body_string("Unauthorized"))
        .mount(&mock_server)
        .await;
    let url = format!("{}/spec", mock_server.uri());

    // Act
    let result = run_blocking(move || {
        let fetcher = HttpSpecFetcher::new();
        fetcher.fetch(&url, "bad-token")
    });

    // Assert
    match result {
        Err(VewApiError::SpecFetchError { reason, .. }) => {
            assert!(reason.contains("401"));
        }
        other => panic!("expected SpecFetchError, got {:?}", other),
    }
}

#[tokio::test]
async fn test_fetch_sends_bearer_auth_header() {
    // Arrange
    let mock_server = MockServer::start().await;
    Mock::given(method("GET"))
        .and(header("Authorization", "Bearer my-secret-token"))
        .respond_with(ResponseTemplate::new(200).set_body_json(serde_json::json!({"paths": {}})))
        .mount(&mock_server)
        .await;
    let url = format!("{}/spec", mock_server.uri());

    // Act
    let result = run_blocking(move || {
        let fetcher = HttpSpecFetcher::new();
        fetcher.fetch(&url, "my-secret-token")
    });

    // Assert
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_fetch_sends_user_agent_header() {
    // Arrange
    let mock_server = MockServer::start().await;
    Mock::given(method("GET"))
        .and(header("User-Agent", USER_AGENT))
        .respond_with(ResponseTemplate::new(200).set_body_json(serde_json::json!({"paths": {}})))
        .mount(&mock_server)
        .await;
    let url = format!("{}/spec", mock_server.uri());

    // Act
    let result = run_blocking(move || {
        let fetcher = HttpSpecFetcher::new();
        fetcher.fetch(&url, "token")
    });

    // Assert
    assert!(result.is_ok());
}
