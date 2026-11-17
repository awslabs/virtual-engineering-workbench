use std::io::{BufRead, BufReader, Read, Write};
use std::net::{TcpListener, TcpStream};
use std::time::Duration;

use socket2::{Domain, Protocol, Socket, Type};

use crate::debug_log;
use crate::identity::adapters::oauth_error::safe_error_code;
use crate::identity::domain::error::IdentityError;
use crate::identity::domain::model::{AuthorizationCode, CallbackResult, StateParam};
use crate::identity::ports::outbound::{CallbackReceiver, CallbackServer};

pub const CALLBACK_PORT: u16 = 17823;

pub struct TcpCallbackServer {
    timeout: Duration,
}

impl TcpCallbackServer {
    pub fn new(timeout: Duration) -> Self {
        Self { timeout }
    }
}

impl CallbackServer for TcpCallbackServer {
    fn start(&self) -> Result<(u16, Box<dyn CallbackReceiver + Send>), IdentityError> {
        let socket = Socket::new(Domain::IPV4, Type::STREAM, Some(Protocol::TCP))
            .map_err(|e| IdentityError::CallbackError(e.to_string()))?;

        let addr: std::net::SocketAddr = format!("127.0.0.1:{CALLBACK_PORT}")
            .parse()
            .map_err(|e| IdentityError::CallbackError(format!("invalid socket address: {e}")))?;
        socket
            .set_reuse_address(true)
            .map_err(|e| IdentityError::CallbackError(e.to_string()))?;
        socket.bind(&addr.into()).map_err(|e| {
            IdentityError::CallbackError(format!("failed to bind port {CALLBACK_PORT}: {e}"))
        })?;
        socket
            .listen(1)
            .map_err(|e| IdentityError::CallbackError(e.to_string()))?;
        socket
            .set_nonblocking(false)
            .map_err(|e| IdentityError::CallbackError(e.to_string()))?;
        // Set accept timeout at the socket level
        socket
            .set_read_timeout(Some(self.timeout))
            .map_err(|e| IdentityError::CallbackError(e.to_string()))?;

        let listener: TcpListener = socket.into();
        let port = listener
            .local_addr()
            .map_err(|e| IdentityError::CallbackError(e.to_string()))?
            .port();

        Ok((
            port,
            Box::new(TcpCallbackReceiverImpl {
                listener,
                timeout: self.timeout,
            }),
        ))
    }
}

pub struct TcpCallbackReceiverImpl {
    listener: TcpListener,
    timeout: Duration,
}

const RESPONSE_BODY: &str =
    "<html><body>Authentication complete. You may close this tab.</body></html>";

impl CallbackReceiver for TcpCallbackReceiverImpl {
    fn wait_for_callback(&self) -> Result<CallbackResult, IdentityError> {
        // Blocking accept — timeout is set on the socket via SO_RCVTIMEO
        let (stream, _) = self.listener.accept().map_err(|e| {
            if e.kind() == std::io::ErrorKind::WouldBlock
                || e.kind() == std::io::ErrorKind::TimedOut
                || e.raw_os_error() == Some(35)
            {
                IdentityError::CallbackTimeout(self.timeout.as_secs())
            } else {
                IdentityError::CallbackError(e.to_string())
            }
        })?;

        stream
            .set_read_timeout(Some(Duration::from_secs(5)))
            .map_err(|e| IdentityError::CallbackError(e.to_string()))?;

        // Anything on this port is unauthenticated input, so the whole request
        // is read under a fixed cap. Without one, a client that never sends a
        // newline makes read_line grow until the process is out of memory.
        const MAX_REQUEST_BYTES: u64 = 64 * 1024;
        let mut reader = BufReader::with_capacity(8192, (&stream).take(MAX_REQUEST_BYTES));
        let mut request_line = String::new();
        reader
            .read_line(&mut request_line)
            .map_err(|e| IdentityError::CallbackError(e.to_string()))?;

        // Consume remaining headers
        let mut header_line = String::new();
        loop {
            header_line.clear();
            let n = reader
                .read_line(&mut header_line)
                .map_err(|e| IdentityError::CallbackError(e.to_string()))?;
            if n == 0 || header_line.trim().is_empty() {
                break;
            }
        }

        let parts: Vec<&str> = request_line.split_whitespace().collect();
        if parts.len() < 2 || parts[0] != "GET" {
            // The request line is unauthenticated input. Do not quote any part
            // of a malformed line because either token may contain secrets.
            debug_log!("callback: received malformed request");
            send_response(&stream, "404 Not Found", "Not Found");
            return Err(IdentityError::CallbackError("expected GET request".into()));
        }

        let path_and_query = parts[1];
        // The request target carries the authorization code in its query
        // string, so log only the fixed method and query-free path.
        debug_log!(
            "callback: received GET {}",
            path_and_query.split('?').next().unwrap_or("?")
        );
        if !path_and_query.starts_with("/callback") {
            send_response(&stream, "404 Not Found", "Not Found");
            // The request target carries code and state in its query string, so
            // the error names the path only.
            let path_only = path_and_query.split('?').next().unwrap_or("?");
            return Err(IdentityError::CallbackError(format!(
                "unexpected path: {path_only}"
            )));
        }

        let params = parse_query(path_and_query);

        if let Some(error) = params.get("error") {
            send_response(&stream, "200 OK", RESPONSE_BODY);
            // error_description is free text chosen by whoever drove the
            // redirect, and a non-standard error code is equally unconstrained,
            // so only an RFC-defined code is shown and the description dropped.
            return Err(IdentityError::ProviderError(
                safe_error_code(error).to_string(),
            ));
        }

        let code = params
            .get("code")
            .ok_or_else(|| IdentityError::CallbackError("missing 'code' parameter".into()))?
            .clone();
        let state = params
            .get("state")
            .ok_or_else(|| IdentityError::CallbackError("missing 'state' parameter".into()))?
            .clone();

        send_response(&stream, "200 OK", RESPONSE_BODY);

        Ok(CallbackResult {
            code: AuthorizationCode(code),
            state: StateParam(state),
        })
    }
}

fn send_response(mut stream: &TcpStream, status: &str, body: &str) {
    let response = format!(
        "HTTP/1.1 {status}\r\n\
         Content-Type: text/html\r\n\
         Content-Security-Policy: default-src 'none'\r\n\
         Cache-Control: no-store\r\n\
         Content-Length: {}\r\n\
         Connection: close\r\n\
         \r\n\
         {body}",
        body.len()
    );
    let _ = stream.write_all(response.as_bytes());
    let _ = stream.flush();
}

fn parse_query(path_and_query: &str) -> std::collections::HashMap<String, String> {
    let mut map = std::collections::HashMap::new();
    if let Some(query) = path_and_query.split('?').nth(1) {
        for pair in query.split('&') {
            if let Some((k, v)) = pair.split_once('=') {
                map.insert(urldecode(k), urldecode(v));
            }
        }
    }
    map
}

fn urldecode(s: &str) -> String {
    let mut result = String::with_capacity(s.len());
    let mut chars = s.bytes();
    while let Some(b) = chars.next() {
        match b {
            b'%' => {
                let hi = chars.next().unwrap_or(b'0');
                let lo = chars.next().unwrap_or(b'0');
                if let Ok(val) =
                    u8::from_str_radix(std::str::from_utf8(&[hi, lo]).unwrap_or("00"), 16)
                {
                    // Map bytes >= 128 to the Unicode replacement character; the OAuth
                    // code/state params from Cognito are URL-safe base64 (ASCII), so this
                    // branch shouldn't be reached in practice, but keeps the decoder safe
                    // against non-UTF-8 input from any other query params.
                    result.push(char::from_u32(val as u32).unwrap_or('\u{FFFD}'));
                }
            }
            b'+' => result.push(' '),
            _ => result.push(b as char),
        }
    }
    result
}
