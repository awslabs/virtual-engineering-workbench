//! Safe rendering of an OAuth 2.0 / OIDC error response.
//!
//! A token, revocation or callback error response is attacker-influenced: the
//! provider chooses `error`, and `error_description` is free text that an
//! attacker who can steer the redirect may control. Echoing either verbatim puts
//! arbitrary text — and, on the token endpoint, the response body including a
//! refresh token — into the CLI's output and log.
//!
//! So nothing from the response reaches the user except an error code that
//! appears on the RFC allow-list below. Anything else collapses to
//! `unrecognised_error`, and `error_description` is dropped entirely.

/// Error codes defined by RFC 6749 §4.1.2.1 and §5.2 (authorization and token
/// endpoints) and RFC 7009 §2.2.1 (revocation).
const KNOWN_ERROR_CODES: &[&str] = &[
    // RFC 6749 §4.1.2.1 — authorization endpoint
    "invalid_request",
    "unauthorized_client",
    "access_denied",
    "unsupported_response_type",
    "invalid_scope",
    "server_error",
    "temporarily_unavailable",
    // RFC 6749 §5.2 — token endpoint
    "invalid_client",
    "invalid_grant",
    "unsupported_grant_type",
    // RFC 7009 §2.2.1 — revocation endpoint
    "unsupported_token_type",
];

/// The error code if it is one the RFCs define, otherwise a fixed placeholder.
/// Never returns provider-supplied text.
pub fn safe_error_code(code: &str) -> &'static str {
    KNOWN_ERROR_CODES
        .iter()
        .find(|known| **known == code)
        .copied()
        .unwrap_or("unrecognised_error")
}

/// A description of a failed HTTP call built only from the status and, when the
/// body parses as an OAuth error object, its allow-listed code. The body itself
/// is never included.
pub fn describe_http_failure(status: reqwest::StatusCode, body: &str) -> String {
    match extract_error_code(body) {
        Some(code) => format!("HTTP {}: {}", status.as_u16(), code),
        None => format!("HTTP {}", status.as_u16()),
    }
}

fn extract_error_code(body: &str) -> Option<&'static str> {
    let parsed: serde_json::Value = serde_json::from_str(body).ok()?;
    let code = parsed.get("error")?.as_str()?;
    Some(safe_error_code(code))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn known_codes_pass_through() {
        assert_eq!(safe_error_code("invalid_grant"), "invalid_grant");
        assert_eq!(
            safe_error_code("unsupported_token_type"),
            "unsupported_token_type"
        );
    }

    #[test]
    fn unknown_code_is_replaced_rather_than_echoed() {
        assert_eq!(
            safe_error_code("<script>alert(1)</script>"),
            "unrecognised_error"
        );
        assert_eq!(safe_error_code(""), "unrecognised_error");
    }

    #[test]
    fn http_failure_never_includes_the_body() {
        let body = r#"{"error":"invalid_grant","error_description":"refresh_token=SECRET-abc"}"#;
        let rendered = describe_http_failure(reqwest::StatusCode::BAD_REQUEST, body);
        assert_eq!(rendered, "HTTP 400: invalid_grant");
        assert!(!rendered.contains("SECRET-abc"));
        assert!(!rendered.contains("error_description"));
    }

    #[test]
    fn unparseable_body_yields_status_only() {
        let rendered = describe_http_failure(
            reqwest::StatusCode::INTERNAL_SERVER_ERROR,
            "access_token=SECRET-xyz",
        );
        assert_eq!(rendered, "HTTP 500");
        assert!(!rendered.contains("SECRET-xyz"));
    }
}
