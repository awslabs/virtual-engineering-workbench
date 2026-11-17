use wiremock::matchers::{body_json, header, method};
use wiremock::{Mock, MockServer, ResponseTemplate};

use vew::shared::constants::USER_AGENT;
use vew::vew_api::adapters::http_api_invoker::HttpApiInvoker;
use vew::vew_api::ports::outbound::ApiInvoker;

fn run_blocking<F, R>(f: F) -> R
where
    F: FnOnce() -> R + Send + 'static,
    R: Send + 'static,
{
    std::thread::spawn(f).join().unwrap()
}

#[tokio::test]
async fn test_invoke_get_returns_status_and_body() {
    // Arrange
    let mock_server = MockServer::start().await;
    Mock::given(method("GET"))
        .respond_with(
            ResponseTemplate::new(200).set_body_json(serde_json::json!({"items": [1, 2, 3]})),
        )
        .mount(&mock_server)
        .await;
    let url = format!("{}/items", mock_server.uri());

    // Act
    let (status, body) = run_blocking(move || {
        let invoker = HttpApiInvoker::new();
        invoker.invoke("GET", &url, "token", None)
    })
    .unwrap();

    // Assert
    assert_eq!(status, 200);
    assert_eq!(body["items"], serde_json::json!([1, 2, 3]));
}

#[tokio::test]
async fn test_invoke_post_sends_json_body() {
    // Arrange
    let mock_server = MockServer::start().await;
    let payload = serde_json::json!({"name": "test"});
    Mock::given(method("POST"))
        .and(header("Content-Type", "application/json"))
        .and(body_json(&payload))
        .respond_with(ResponseTemplate::new(201).set_body_json(serde_json::json!({"id": "abc"})))
        .mount(&mock_server)
        .await;
    let url = format!("{}/items", mock_server.uri());

    // Act
    let (status, body) = run_blocking(move || {
        let invoker = HttpApiInvoker::new();
        let payload = serde_json::json!({"name": "test"});
        invoker.invoke("POST", &url, "token", Some(&payload))
    })
    .unwrap();

    // Assert
    assert_eq!(status, 201);
    assert_eq!(body["id"], "abc");
}

#[tokio::test]
async fn test_invoke_put_and_delete_work() {
    // Arrange
    let mock_server = MockServer::start().await;
    Mock::given(method("PUT"))
        .respond_with(ResponseTemplate::new(200).set_body_json(serde_json::json!({})))
        .mount(&mock_server)
        .await;
    Mock::given(method("DELETE"))
        .respond_with(ResponseTemplate::new(204).set_body_json(serde_json::json!({})))
        .mount(&mock_server)
        .await;
    let url_put = format!("{}/item/1", mock_server.uri());
    let url_del = url_put.clone();

    // Act
    let (put_status, _) = run_blocking(move || {
        HttpApiInvoker::new().invoke("PUT", &url_put, "t", Some(&serde_json::json!({})))
    })
    .unwrap();
    let (del_status, _) =
        run_blocking(move || HttpApiInvoker::new().invoke("DELETE", &url_del, "t", None)).unwrap();

    // Assert
    assert_eq!(put_status, 200);
    assert_eq!(del_status, 204);
}

#[tokio::test]
async fn test_invoke_sends_bearer_auth_and_user_agent() {
    // Arrange
    let mock_server = MockServer::start().await;
    Mock::given(method("GET"))
        .and(header("Authorization", "Bearer my-token"))
        .and(header("User-Agent", USER_AGENT))
        .respond_with(ResponseTemplate::new(200).set_body_json(serde_json::json!({})))
        .mount(&mock_server)
        .await;
    let url = format!("{}/test", mock_server.uri());

    // Act
    let result = run_blocking(move || HttpApiInvoker::new().invoke("GET", &url, "my-token", None));

    // Assert
    assert!(result.is_ok());
}
