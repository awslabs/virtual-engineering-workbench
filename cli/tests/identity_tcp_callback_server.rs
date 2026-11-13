use std::io::{Read, Write};
use std::net::TcpStream;
use std::time::Duration;
use vew::identity::adapters::tcp_callback_server::{CALLBACK_PORT, TcpCallbackServer};
use vew::identity::domain::error::IdentityError;
use vew::identity::ports::outbound::CallbackServer;

/// All callback server tests run sequentially in one test to avoid port conflicts
/// since we use a static port.
#[test]
fn test_callback_server() {
    test_start_binds_to_loopback();
    test_callback_receives_code_and_state();
    test_callback_rejects_non_callback_path();
    test_callback_handles_error_param();
    test_callback_returns_html_with_security_headers();
}

fn test_start_binds_to_loopback() {
    // Arrange
    let server = TcpCallbackServer::new(Duration::from_secs(5));

    // Act
    let (port, _receiver) = server.start().unwrap();

    // Assert
    assert_eq!(port, CALLBACK_PORT);
    assert!(TcpStream::connect(format!("127.0.0.1:{port}")).is_ok());
}

fn test_callback_receives_code_and_state() {
    // Arrange
    let server = TcpCallbackServer::new(Duration::from_secs(5));
    let (port, receiver) = server.start().unwrap();
    let handle = std::thread::spawn(move || receiver.wait_for_callback());
    std::thread::sleep(Duration::from_millis(50));

    // Act
    let mut stream = TcpStream::connect(format!("127.0.0.1:{port}")).unwrap();
    write!(
        stream,
        "GET /callback?code=abc123&state=xyz789 HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n\r\n"
    )
    .unwrap();
    stream.flush().unwrap();
    let mut response = String::new();
    stream
        .set_read_timeout(Some(Duration::from_secs(2)))
        .unwrap();
    let _ = stream.read_to_string(&mut response);
    let result = handle.join().unwrap().unwrap();

    // Assert
    assert_eq!(result.code.0, "abc123");
    assert_eq!(result.state.0, "xyz789");
}

fn test_callback_rejects_non_callback_path() {
    // Arrange
    let server = TcpCallbackServer::new(Duration::from_secs(5));
    let (port, receiver) = server.start().unwrap();
    let handle = std::thread::spawn(move || receiver.wait_for_callback());
    std::thread::sleep(Duration::from_millis(50));

    // Act
    let mut stream = TcpStream::connect(format!("127.0.0.1:{port}")).unwrap();
    write!(
        stream,
        "GET /other HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n\r\n"
    )
    .unwrap();
    stream.flush().unwrap();
    let mut response = String::new();
    stream
        .set_read_timeout(Some(Duration::from_secs(2)))
        .unwrap();
    let _ = stream.read_to_string(&mut response);
    let result = handle.join().unwrap();

    // Assert
    assert!(response.contains("404 Not Found"));
    assert!(result.is_err());
}

fn test_callback_handles_error_param() {
    // Arrange
    let server = TcpCallbackServer::new(Duration::from_secs(5));
    let (port, receiver) = server.start().unwrap();
    let handle = std::thread::spawn(move || receiver.wait_for_callback());
    std::thread::sleep(Duration::from_millis(50));

    // Act
    let mut stream = TcpStream::connect(format!("127.0.0.1:{port}")).unwrap();
    write!(stream, "GET /callback?error=access_denied&error_description=user+cancelled HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n").unwrap();
    stream.flush().unwrap();
    let mut response = String::new();
    stream
        .set_read_timeout(Some(Duration::from_secs(2)))
        .unwrap();
    let _ = stream.read_to_string(&mut response);
    let result = handle.join().unwrap();

    // Assert
    assert!(matches!(result, Err(IdentityError::ProviderError(_))));
}

fn test_callback_returns_html_with_security_headers() {
    // Arrange
    let server = TcpCallbackServer::new(Duration::from_secs(5));
    let (port, receiver) = server.start().unwrap();
    let handle = std::thread::spawn(move || receiver.wait_for_callback());
    std::thread::sleep(Duration::from_millis(50));

    // Act
    let mut stream = TcpStream::connect(format!("127.0.0.1:{port}")).unwrap();
    write!(
        stream,
        "GET /callback?code=test&state=test HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n"
    )
    .unwrap();
    stream.flush().unwrap();
    let mut response = String::new();
    stream
        .set_read_timeout(Some(Duration::from_secs(2)))
        .unwrap();
    let _ = stream.read_to_string(&mut response);
    let _ = handle.join().unwrap();

    // Assert
    assert!(response.contains("Content-Security-Policy: default-src 'none'"));
    assert!(response.contains("Cache-Control: no-store"));
    assert!(response.contains("Content-Type: text/html"));
    assert!(response.contains("Authentication complete"));
}
