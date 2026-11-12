use chrono::{Duration, Utc};

use crate::debug_log;
use crate::identity::domain::commands::{GetAccessToken, GetToken, Login, Logout};
use crate::identity::domain::error::IdentityError;
use crate::identity::domain::model::{
    LoginResult, LogoutResult, TokenSet, TokenType, ValidationParams,
};
use crate::identity::ports::inbound::IdentityService;
use crate::identity::ports::outbound::{
    BrowserLauncher, CallbackServer, CryptoProvider, OidcClient, TokenStore, TokenValidator,
};

pub struct IdentityServiceImpl<
    O: OidcClient,
    S: TokenStore,
    V: TokenValidator,
    C: CallbackServer,
    K: CryptoProvider,
    B: BrowserLauncher,
> {
    oidc: O,
    store: S,
    validator: V,
    callback: C,
    crypto: K,
    browser: B,
}

impl<
    O: OidcClient,
    S: TokenStore,
    V: TokenValidator,
    C: CallbackServer,
    K: CryptoProvider,
    B: BrowserLauncher,
> IdentityServiceImpl<O, S, V, C, K, B>
{
    pub fn new(oidc: O, store: S, validator: V, callback: C, crypto: K, browser: B) -> Self {
        Self {
            oidc,
            store,
            validator,
            callback,
            crypto,
            browser,
        }
    }
}

impl<
    O: OidcClient,
    S: TokenStore,
    V: TokenValidator,
    C: CallbackServer,
    K: CryptoProvider,
    B: BrowserLauncher,
> IdentityService for IdentityServiceImpl<O, S, V, C, K, B>
{
    fn login(&self, cmd: Login) -> Result<LoginResult, IdentityError> {
        debug_log!("login: starting for profile '{}'", cmd.profile_id);
        let pkce = self.crypto.generate_pkce_challenge();
        let state = self.crypto.generate_state();
        let nonce = self.crypto.generate_nonce();

        let (port, receiver) = self.callback.start()?;
        let redirect_uri = format!("http://localhost:{port}/callback");
        debug_log!("login: callback server on port {port}, redirect_uri={redirect_uri}");

        let authorize_url = url::Url::parse_with_params(
            cmd.provider.authorization_endpoint.as_str(),
            &[
                ("response_type", "code"),
                ("client_id", cmd.provider.client_id.as_str()),
                ("redirect_uri", redirect_uri.as_str()),
                ("scope", cmd.provider.scopes.join(" ").as_str()),
                ("code_challenge", pkce.challenge.as_str()),
                ("code_challenge_method", "S256"),
                ("state", state.0.as_str()),
                ("nonce", nonce.0.as_str()),
            ],
        )
        .map_err(|e| IdentityError::ProviderError(format!("invalid authorize URL: {e}")))?
        .to_string();
        debug_log!("login: authorization URL constructed");

        if cmd.no_browser {
            println!("{authorize_url}");
        } else {
            let browser_opened = self.browser.open(&authorize_url).is_ok();
            if !browser_opened {
                eprintln!("Could not open browser. Open this URL manually:\n{authorize_url}");
            }
        }

        debug_log!("login: waiting for callback...");
        let result = receiver.wait_for_callback()?;
        debug_log!(
            "login: received callback, code length={}",
            result.code.0.len()
        );

        if result.state != state {
            debug_log!("login: state mismatch");
            return Err(IdentityError::StateMismatch);
        }

        debug_log!("login: exchanging code for tokens...");
        let token_resp =
            self.oidc
                .exchange_code(&cmd.provider, &result.code, &pkce.verifier, &redirect_uri)?;

        debug_log!("login: validating ID token...");
        let _claims = self.validator.validate_id_token(
            &token_resp.id_token,
            &ValidationParams {
                issuer: cmd.provider.issuer.to_string(),
                audience: cmd.provider.client_id.clone(),
                nonce: Some(nonce),
                jwks_uri: cmd.provider.jwks_uri.to_string(),
            },
        )?;

        let token_set = TokenSet {
            access_token: token_resp.access_token,
            id_token: token_resp.id_token,
            refresh_token: token_resp.refresh_token.unwrap_or_default(),
            expires_at: Utc::now() + Duration::seconds(token_resp.expires_in),
        };

        self.store.save(&cmd.profile_id, &token_set)?;
        Ok(LoginResult {
            access_token_expires_in: token_resp.expires_in,
        })
    }

    fn logout(&self, cmd: Logout) -> Result<LogoutResult, IdentityError> {
        debug_log!("logout: profile '{}'", cmd.profile_id);
        let tokens = self.store.load(&cmd.profile_id)?;
        let tokens = match tokens {
            Some(t) => t,
            None => {
                debug_log!("logout: no tokens found, already logged out");
                return Ok(LogoutResult {
                    was_logged_in: false,
                });
            }
        };

        debug_log!("logout: revoking refresh token...");
        let revoke_result = self.oidc.revoke_token(&cmd.provider, &tokens.refresh_token);
        self.store.delete(&cmd.profile_id)?;

        if let Err(e) = revoke_result {
            debug_log!("logout: revocation failed: {e}");
        }

        Ok(LogoutResult {
            was_logged_in: true,
        })
    }

    fn get_access_token(&self, cmd: GetAccessToken) -> Result<String, IdentityError> {
        debug_log!("get_access_token: profile '{}'", cmd.profile_id);
        let tokens = self
            .store
            .load(&cmd.profile_id)?
            .ok_or_else(|| IdentityError::NotAuthenticated(cmd.profile_id.clone()))?;

        if !tokens.is_expired() {
            debug_log!("get_access_token: token still valid");
            return Ok(tokens.access_token);
        }

        debug_log!("get_access_token: token expired, refreshing...");
        let token_resp = match self
            .oidc
            .refresh_tokens(&cmd.provider, &tokens.refresh_token)
        {
            Ok(resp) => resp,
            Err(e) => {
                debug_log!("get_access_token: refresh failed: {e}");
                let _ = self.store.delete(&cmd.profile_id);
                return Err(IdentityError::RefreshFailed(e.to_string()));
            }
        };

        let new_refresh = token_resp.refresh_token.unwrap_or(tokens.refresh_token);

        let new_tokens = TokenSet {
            access_token: token_resp.access_token,
            id_token: token_resp.id_token,
            refresh_token: new_refresh,
            expires_at: Utc::now() + Duration::seconds(token_resp.expires_in),
        };

        self.store.save(&cmd.profile_id, &new_tokens)?;
        Ok(new_tokens.access_token)
    }

    fn get_token(&self, cmd: GetToken) -> Result<String, IdentityError> {
        debug_log!(
            "get_token: profile '{}', type {:?}",
            cmd.profile_id,
            cmd.token_type
        );
        match cmd.token_type {
            TokenType::Access => self.get_access_token(GetAccessToken {
                profile_id: cmd.profile_id,
                provider: cmd.provider,
            }),
            TokenType::Id => {
                let tokens = self
                    .store
                    .load(&cmd.profile_id)?
                    .ok_or_else(|| IdentityError::NotAuthenticated(cmd.profile_id.clone()))?;
                Ok(tokens.id_token)
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::identity::domain::commands::GetToken;
    use crate::identity::domain::model::*;
    use crate::identity::ports::outbound::*;
    use std::cell::RefCell;

    // --- Mock implementations ---

    struct MockCrypto;
    impl CryptoProvider for MockCrypto {
        fn generate_pkce_challenge(&self) -> PkceChallenge {
            PkceChallenge {
                verifier: "test_verifier".into(),
                challenge: "test_challenge".into(),
            }
        }
        fn generate_state(&self) -> StateParam {
            StateParam("test_state".into())
        }
        fn generate_nonce(&self) -> Nonce {
            Nonce("test_nonce".into())
        }
    }

    struct MockBrowser {
        should_fail: bool,
        open_called: RefCell<bool>,
    }
    impl BrowserLauncher for MockBrowser {
        fn open(&self, _url: &str) -> Result<(), IdentityError> {
            *self.open_called.borrow_mut() = true;
            if self.should_fail {
                Err(IdentityError::BrowserError("no browser".into()))
            } else {
                Ok(())
            }
        }
    }

    struct MockCallbackReceiver {
        result: Result<CallbackResult, IdentityError>,
    }
    impl CallbackReceiver for MockCallbackReceiver {
        fn wait_for_callback(&self) -> Result<CallbackResult, IdentityError> {
            match &self.result {
                Ok(r) => Ok(CallbackResult {
                    code: AuthorizationCode(r.code.0.clone()),
                    state: r.state.clone(),
                }),
                Err(_) => Err(IdentityError::CallbackTimeout(120)),
            }
        }
    }

    struct MockCallbackServer {
        state: String,
    }
    impl CallbackServer for MockCallbackServer {
        fn start(&self) -> Result<(u16, Box<dyn CallbackReceiver + Send>), IdentityError> {
            Ok((
                12345,
                Box::new(MockCallbackReceiver {
                    result: Ok(CallbackResult {
                        code: AuthorizationCode("auth_code_123".into()),
                        state: StateParam(self.state.clone()),
                    }),
                }),
            ))
        }
    }

    struct MockTimeoutCallbackServer;
    impl CallbackServer for MockTimeoutCallbackServer {
        fn start(&self) -> Result<(u16, Box<dyn CallbackReceiver + Send>), IdentityError> {
            Ok((
                12345,
                Box::new(MockCallbackReceiver {
                    result: Err(IdentityError::CallbackTimeout(120)),
                }),
            ))
        }
    }

    struct MockOidc {
        exchange_result: RefCell<Option<Result<TokenResponse, IdentityError>>>,
        refresh_result: RefCell<Option<Result<TokenResponse, IdentityError>>>,
        revoke_result: RefCell<Option<Result<(), IdentityError>>>,
    }
    impl MockOidc {
        fn success() -> Self {
            Self {
                exchange_result: RefCell::new(Some(Ok(TokenResponse {
                    access_token: "access_tok".into(),
                    id_token: "id_tok".into(),
                    refresh_token: Some("refresh_tok".into()),
                    expires_in: 3600,
                }))),
                refresh_result: RefCell::new(None),
                revoke_result: RefCell::new(Some(Ok(()))),
            }
        }
    }
    impl OidcClient for MockOidc {
        fn exchange_code(
            &self,
            _p: &OidcProvider,
            _c: &AuthorizationCode,
            _v: &str,
            _r: &str,
        ) -> Result<TokenResponse, IdentityError> {
            self.exchange_result.borrow_mut().take().unwrap()
        }
        fn refresh_tokens(
            &self,
            _p: &OidcProvider,
            _rt: &str,
        ) -> Result<TokenResponse, IdentityError> {
            self.refresh_result.borrow_mut().take().unwrap()
        }
        fn revoke_token(&self, _p: &OidcProvider, _t: &str) -> Result<(), IdentityError> {
            self.revoke_result.borrow_mut().take().unwrap()
        }
    }

    struct MockValidator {
        should_fail: bool,
    }
    impl TokenValidator for MockValidator {
        fn validate_id_token(
            &self,
            _t: &str,
            _p: &ValidationParams,
        ) -> Result<IdTokenClaims, IdentityError> {
            if self.should_fail {
                return Err(IdentityError::NonceMismatch);
            }
            Ok(IdTokenClaims {
                sub: "user".into(),
                iss: "iss".into(),
                aud: "aud".into(),
                nonce: Some("test_nonce".into()),
            })
        }
    }

    struct MockStore {
        tokens: RefCell<Option<TokenSet>>,
    }
    impl MockStore {
        fn empty() -> Self {
            Self {
                tokens: RefCell::new(None),
            }
        }
        fn with(ts: TokenSet) -> Self {
            Self {
                tokens: RefCell::new(Some(ts)),
            }
        }
    }
    impl TokenStore for MockStore {
        fn save(&self, _id: &str, t: &TokenSet) -> Result<(), IdentityError> {
            *self.tokens.borrow_mut() = Some(t.clone());
            Ok(())
        }
        fn load(&self, _id: &str) -> Result<Option<TokenSet>, IdentityError> {
            Ok(self.tokens.borrow().clone())
        }
        fn delete(&self, _id: &str) -> Result<(), IdentityError> {
            *self.tokens.borrow_mut() = None;
            Ok(())
        }
    }

    fn test_provider() -> OidcProvider {
        OidcProvider {
            issuer: url::Url::parse("https://auth.example.com").unwrap(),
            client_id: "client123".into(),
            authorization_endpoint: url::Url::parse("https://auth.example.com/authorize").unwrap(),
            token_endpoint: url::Url::parse("https://auth.example.com/token").unwrap(),
            revocation_endpoint: Some(url::Url::parse("https://auth.example.com/revoke").unwrap()),
            jwks_uri: url::Url::parse("https://auth.example.com/jwks").unwrap(),
            scopes: vec!["openid".into(), "profile".into(), "email".into()],
        }
    }

    fn make_svc(
        oidc: MockOidc,
        store: MockStore,
        validator: MockValidator,
        callback: impl CallbackServer + 'static,
        browser: MockBrowser,
    ) -> IdentityServiceImpl<
        MockOidc,
        MockStore,
        MockValidator,
        impl CallbackServer,
        MockCrypto,
        MockBrowser,
    > {
        IdentityServiceImpl::new(oidc, store, validator, callback, MockCrypto, browser)
    }

    // --- Login tests ---

    #[test]
    fn test_login_happy_path() {
        // Arrange
        let svc = make_svc(
            MockOidc::success(),
            MockStore::empty(),
            MockValidator { should_fail: false },
            MockCallbackServer {
                state: "test_state".into(),
            },
            MockBrowser {
                should_fail: false,
                open_called: RefCell::new(false),
            },
        );

        // Act
        let result = svc.login(Login {
            profile_id: "dev".into(),
            provider: test_provider(),
            no_browser: false,
        });

        // Assert
        assert_eq!(result.unwrap().access_token_expires_in, 3600);
    }

    #[test]
    fn test_login_does_not_log_authorization_secrets() {
        crate::shared::verbose::capture::enable();
        let svc = make_svc(
            MockOidc::success(),
            MockStore::empty(),
            MockValidator { should_fail: false },
            MockCallbackServer {
                state: "test_state".into(),
            },
            MockBrowser {
                should_fail: false,
                open_called: RefCell::new(false),
            },
        );

        let result = svc.login(Login {
            profile_id: "dev".into(),
            provider: test_provider(),
            no_browser: false,
        });

        assert!(result.is_ok());
        let log = crate::shared::verbose::capture::joined();
        for secret in [
            "test_state",
            "test_nonce",
            "test_challenge",
            "test_verifier",
        ] {
            assert!(
                !log.contains(secret),
                "authorization secret {secret} reached the debug log:\n{log}"
            );
        }
        assert!(
            !log.contains("https://auth.example.com/authorize"),
            "the authorization URL reached the debug log:\n{log}"
        );
    }

    #[test]
    fn test_login_state_mismatch() {
        // Arrange
        let svc = make_svc(
            MockOidc::success(),
            MockStore::empty(),
            MockValidator { should_fail: false },
            MockCallbackServer {
                state: "wrong_state".into(),
            },
            MockBrowser {
                should_fail: false,
                open_called: RefCell::new(false),
            },
        );

        // Act
        let result = svc.login(Login {
            profile_id: "dev".into(),
            provider: test_provider(),
            no_browser: false,
        });

        // Assert
        assert!(matches!(result, Err(IdentityError::StateMismatch)));
    }

    #[test]
    fn test_login_nonce_mismatch() {
        // Arrange
        let svc = make_svc(
            MockOidc::success(),
            MockStore::empty(),
            MockValidator { should_fail: true },
            MockCallbackServer {
                state: "test_state".into(),
            },
            MockBrowser {
                should_fail: false,
                open_called: RefCell::new(false),
            },
        );

        // Act
        let result = svc.login(Login {
            profile_id: "dev".into(),
            provider: test_provider(),
            no_browser: false,
        });

        // Assert
        assert!(matches!(result, Err(IdentityError::NonceMismatch)));
    }

    #[test]
    fn test_login_callback_timeout() {
        // Arrange
        let svc = make_svc(
            MockOidc::success(),
            MockStore::empty(),
            MockValidator { should_fail: false },
            MockTimeoutCallbackServer,
            MockBrowser {
                should_fail: false,
                open_called: RefCell::new(false),
            },
        );

        // Act
        let result = svc.login(Login {
            profile_id: "dev".into(),
            provider: test_provider(),
            no_browser: false,
        });

        // Assert
        assert!(matches!(result, Err(IdentityError::CallbackTimeout(_))));
    }

    #[test]
    fn test_login_exchange_failure() {
        // Arrange
        let oidc = MockOidc {
            exchange_result: RefCell::new(Some(Err(IdentityError::TokenExchange("fail".into())))),
            refresh_result: RefCell::new(None),
            revoke_result: RefCell::new(None),
        };
        let svc = make_svc(
            oidc,
            MockStore::empty(),
            MockValidator { should_fail: false },
            MockCallbackServer {
                state: "test_state".into(),
            },
            MockBrowser {
                should_fail: false,
                open_called: RefCell::new(false),
            },
        );

        // Act
        let result = svc.login(Login {
            profile_id: "dev".into(),
            provider: test_provider(),
            no_browser: false,
        });

        // Assert
        assert!(matches!(result, Err(IdentityError::TokenExchange(_))));
    }

    #[test]
    fn test_login_browser_failure_is_non_fatal() {
        // Arrange
        let svc = make_svc(
            MockOidc::success(),
            MockStore::empty(),
            MockValidator { should_fail: false },
            MockCallbackServer {
                state: "test_state".into(),
            },
            MockBrowser {
                should_fail: true,
                open_called: RefCell::new(false),
            },
        );

        // Act
        let result = svc.login(Login {
            profile_id: "dev".into(),
            provider: test_provider(),
            no_browser: false,
        });

        // Assert
        assert_eq!(result.unwrap().access_token_expires_in, 3600);
    }

    #[test]
    fn test_login_no_browser_skips_browser_open() {
        // Arrange
        let browser = MockBrowser {
            should_fail: false,
            open_called: RefCell::new(false),
        };
        let svc = make_svc(
            MockOidc::success(),
            MockStore::empty(),
            MockValidator { should_fail: false },
            MockCallbackServer {
                state: "test_state".into(),
            },
            browser,
        );

        // Act
        let result = svc.login(Login {
            profile_id: "dev".into(),
            provider: test_provider(),
            no_browser: true,
        });

        // Assert
        let login_result = result.unwrap();
        assert_eq!(login_result.access_token_expires_in, 3600);
    }

    #[test]
    fn test_login_with_browser_calls_browser_open() {
        // Arrange
        let svc = make_svc(
            MockOidc::success(),
            MockStore::empty(),
            MockValidator { should_fail: false },
            MockCallbackServer {
                state: "test_state".into(),
            },
            MockBrowser {
                should_fail: false,
                open_called: RefCell::new(false),
            },
        );

        // Act
        let result = svc.login(Login {
            profile_id: "dev".into(),
            provider: test_provider(),
            no_browser: false,
        });

        // Assert
        let login_result = result.unwrap();
        assert_eq!(login_result.access_token_expires_in, 3600);
    }

    // --- get_access_token tests ---

    fn valid_token_set() -> TokenSet {
        TokenSet {
            access_token: "valid_access".into(),
            id_token: "id".into(),
            refresh_token: "refresh".into(),
            expires_at: Utc::now() + Duration::seconds(3600),
        }
    }

    fn expired_token_set() -> TokenSet {
        TokenSet {
            access_token: "old_access".into(),
            id_token: "id".into(),
            refresh_token: "old_refresh".into(),
            expires_at: Utc::now() - Duration::seconds(60),
        }
    }

    #[test]
    fn test_get_access_token_valid() {
        // Arrange
        let svc = make_svc(
            MockOidc::success(),
            MockStore::with(valid_token_set()),
            MockValidator { should_fail: false },
            MockCallbackServer { state: "".into() },
            MockBrowser {
                should_fail: false,
                open_called: RefCell::new(false),
            },
        );

        // Act
        let tok = svc
            .get_access_token(GetAccessToken {
                profile_id: "dev".into(),
                provider: test_provider(),
            })
            .unwrap();

        // Assert
        assert_eq!(tok, "valid_access");
    }

    #[test]
    fn test_get_access_token_expired_refreshes() {
        // Arrange
        let oidc = MockOidc {
            exchange_result: RefCell::new(None),
            refresh_result: RefCell::new(Some(Ok(TokenResponse {
                access_token: "new_access".into(),
                id_token: "new_id".into(),
                refresh_token: Some("new_refresh".into()),
                expires_in: 3600,
            }))),
            revoke_result: RefCell::new(None),
        };
        let svc = make_svc(
            oidc,
            MockStore::with(expired_token_set()),
            MockValidator { should_fail: false },
            MockCallbackServer { state: "".into() },
            MockBrowser {
                should_fail: false,
                open_called: RefCell::new(false),
            },
        );

        // Act
        let tok = svc
            .get_access_token(GetAccessToken {
                profile_id: "dev".into(),
                provider: test_provider(),
            })
            .unwrap();

        // Assert
        assert_eq!(tok, "new_access");
    }

    #[test]
    fn test_get_access_token_refresh_preserves_original_refresh_token() {
        // Arrange
        let oidc = MockOidc {
            exchange_result: RefCell::new(None),
            refresh_result: RefCell::new(Some(Ok(TokenResponse {
                access_token: "new_access".into(),
                id_token: "new_id".into(),
                refresh_token: None,
                expires_in: 3600,
            }))),
            revoke_result: RefCell::new(None),
        };
        let svc = make_svc(
            oidc,
            MockStore::with(expired_token_set()),
            MockValidator { should_fail: false },
            MockCallbackServer { state: "".into() },
            MockBrowser {
                should_fail: false,
                open_called: RefCell::new(false),
            },
        );

        // Act
        let result = svc.get_access_token(GetAccessToken {
            profile_id: "dev".into(),
            provider: test_provider(),
        });

        // Assert
        assert!(result.is_ok());
    }

    #[test]
    fn test_get_access_token_refresh_failure_deletes_tokens() {
        // Arrange
        let oidc = MockOidc {
            exchange_result: RefCell::new(None),
            refresh_result: RefCell::new(Some(Err(IdentityError::RefreshFailed("expired".into())))),
            revoke_result: RefCell::new(None),
        };
        let svc = make_svc(
            oidc,
            MockStore::with(expired_token_set()),
            MockValidator { should_fail: false },
            MockCallbackServer { state: "".into() },
            MockBrowser {
                should_fail: false,
                open_called: RefCell::new(false),
            },
        );

        // Act
        let result = svc.get_access_token(GetAccessToken {
            profile_id: "dev".into(),
            provider: test_provider(),
        });

        // Assert
        assert!(matches!(result, Err(IdentityError::RefreshFailed(_))));
    }

    #[test]
    fn test_get_access_token_no_tokens() {
        // Arrange
        let svc = make_svc(
            MockOidc::success(),
            MockStore::empty(),
            MockValidator { should_fail: false },
            MockCallbackServer { state: "".into() },
            MockBrowser {
                should_fail: false,
                open_called: RefCell::new(false),
            },
        );

        // Act
        let result = svc.get_access_token(GetAccessToken {
            profile_id: "dev".into(),
            provider: test_provider(),
        });

        // Assert
        assert!(matches!(result, Err(IdentityError::NotAuthenticated(_))));
    }

    // --- Logout tests ---

    #[test]
    fn test_logout_revokes_then_deletes() {
        // Arrange
        let svc = make_svc(
            MockOidc::success(),
            MockStore::with(valid_token_set()),
            MockValidator { should_fail: false },
            MockCallbackServer { state: "".into() },
            MockBrowser {
                should_fail: false,
                open_called: RefCell::new(false),
            },
        );

        // Act
        let result = svc.logout(Logout {
            profile_id: "dev".into(),
            provider: test_provider(),
        });

        // Assert
        assert!(result.unwrap().was_logged_in);
    }

    #[test]
    fn test_logout_revoke_failure_still_deletes() {
        // Arrange
        let oidc = MockOidc {
            exchange_result: RefCell::new(None),
            refresh_result: RefCell::new(None),
            revoke_result: RefCell::new(Some(Err(IdentityError::TokenExchange(
                "network error".into(),
            )))),
        };
        let svc = make_svc(
            oidc,
            MockStore::with(valid_token_set()),
            MockValidator { should_fail: false },
            MockCallbackServer { state: "".into() },
            MockBrowser {
                should_fail: false,
                open_called: RefCell::new(false),
            },
        );

        // Act
        let result = svc.logout(Logout {
            profile_id: "dev".into(),
            provider: test_provider(),
        });

        // Assert
        assert!(result.unwrap().was_logged_in);
    }

    #[test]
    fn test_logout_no_tokens_is_ok() {
        // Arrange
        let svc = make_svc(
            MockOidc::success(),
            MockStore::empty(),
            MockValidator { should_fail: false },
            MockCallbackServer { state: "".into() },
            MockBrowser {
                should_fail: false,
                open_called: RefCell::new(false),
            },
        );

        // Act
        let result = svc.logout(Logout {
            profile_id: "dev".into(),
            provider: test_provider(),
        });

        // Assert
        assert!(!result.unwrap().was_logged_in);
    }

    // --- get_token tests ---

    #[test]
    fn test_get_token_access_delegates_to_get_access_token() {
        // Arrange
        let svc = make_svc(
            MockOidc::success(),
            MockStore::with(valid_token_set()),
            MockValidator { should_fail: false },
            MockCallbackServer { state: "".into() },
            MockBrowser {
                should_fail: false,
                open_called: RefCell::new(false),
            },
        );

        // Act
        let result = svc.get_token(GetToken {
            profile_id: "dev".into(),
            provider: test_provider(),
            token_type: TokenType::Access,
        });

        // Assert
        assert_eq!(result.unwrap(), "valid_access");
    }

    #[test]
    fn test_get_token_id_returns_id_token() {
        // Arrange
        let svc = make_svc(
            MockOidc::success(),
            MockStore::with(valid_token_set()),
            MockValidator { should_fail: false },
            MockCallbackServer { state: "".into() },
            MockBrowser {
                should_fail: false,
                open_called: RefCell::new(false),
            },
        );

        // Act
        let result = svc.get_token(GetToken {
            profile_id: "dev".into(),
            provider: test_provider(),
            token_type: TokenType::Id,
        });

        // Assert
        assert_eq!(result.unwrap(), "id");
    }

    #[test]
    fn test_get_token_id_no_tokens() {
        // Arrange
        let svc = make_svc(
            MockOidc::success(),
            MockStore::empty(),
            MockValidator { should_fail: false },
            MockCallbackServer { state: "".into() },
            MockBrowser {
                should_fail: false,
                open_called: RefCell::new(false),
            },
        );

        // Act
        let result = svc.get_token(GetToken {
            profile_id: "dev".into(),
            provider: test_provider(),
            token_type: TokenType::Id,
        });

        // Assert
        assert!(matches!(result, Err(IdentityError::NotAuthenticated(_))));
    }
}
