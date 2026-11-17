use crate::debug_log;
use crate::shared::auth::{AuthProvider, BearerAuthProvider};
use crate::shared::http::blocking_client;
use crate::vew_api::domain::error::VewApiError;
use crate::vew_api::ports::outbound::ApiInvoker;

pub struct HttpApiInvoker<A: AuthProvider = BearerAuthProvider> {
    http: reqwest::blocking::Client,
    auth: A,
}

impl Default for HttpApiInvoker<BearerAuthProvider> {
    fn default() -> Self {
        Self::new()
    }
}

impl HttpApiInvoker<BearerAuthProvider> {
    pub fn new() -> Self {
        Self::with_auth(BearerAuthProvider)
    }
}

impl<A: AuthProvider> HttpApiInvoker<A> {
    pub fn with_auth(auth: A) -> Self {
        Self {
            http: blocking_client(),
            auth,
        }
    }
}

impl<A: AuthProvider + Send + Sync> ApiInvoker for HttpApiInvoker<A> {
    fn invoke(
        &self,
        method: &str,
        url: &str,
        token: &str,
        body: Option<&serde_json::Value>,
    ) -> Result<(u16, serde_json::Value), VewApiError> {
        debug_log!("{} {}", method, url);
        let mut req = match method {
            "GET" => self.http.get(url),
            "POST" => self.http.post(url),
            "PUT" => self.http.put(url),
            "DELETE" => self.http.delete(url),
            "PATCH" => self.http.patch(url),
            _ => {
                return Err(VewApiError::InvocationError {
                    status: 0,
                    body: format!("unsupported method: {}", method),
                });
            }
        };
        let (header, value) = self.auth.auth_header(token);
        req = req.header(header, value);
        if let Some(body) = body {
            req = req.json(body);
        }
        let resp = req
            .send()
            .map_err(|e| VewApiError::NetworkError(e.to_string()))?;
        let status = resp.status().as_u16();
        let body = resp
            .json::<serde_json::Value>()
            .unwrap_or(serde_json::Value::Null);
        debug_log!("response: {} {}", status, body);
        Ok((status, body))
    }
}
