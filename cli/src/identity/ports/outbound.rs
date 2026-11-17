use url::Url;

use super::super::domain::error::IdentityError;
use super::super::domain::model::{
    AuthorizationCode, CallbackResult, IdTokenClaims, Nonce, OidcProvider, PkceChallenge,
    StateParam, TokenResponse, TokenSet, ValidationParams,
};

pub trait TokenStore {
    fn save(&self, profile_id: &str, tokens: &TokenSet) -> Result<(), IdentityError>;
    fn load(&self, profile_id: &str) -> Result<Option<TokenSet>, IdentityError>;
    fn delete(&self, profile_id: &str) -> Result<(), IdentityError>;
}

pub trait OidcClient {
    fn exchange_code(
        &self,
        provider: &OidcProvider,
        code: &AuthorizationCode,
        verifier: &str,
        redirect_uri: &str,
    ) -> Result<TokenResponse, IdentityError>;

    fn refresh_tokens(
        &self,
        provider: &OidcProvider,
        refresh_token: &str,
    ) -> Result<TokenResponse, IdentityError>;

    fn revoke_token(&self, provider: &OidcProvider, token: &str) -> Result<(), IdentityError>;
}

pub trait CallbackReceiver {
    fn wait_for_callback(&self) -> Result<CallbackResult, IdentityError>;
}

pub trait CallbackServer {
    fn start(&self) -> Result<(u16, Box<dyn CallbackReceiver + Send>), IdentityError>;
}

pub trait BrowserLauncher {
    fn open(&self, url: &str) -> Result<(), IdentityError>;
}

pub trait CryptoProvider {
    fn generate_pkce_challenge(&self) -> PkceChallenge;
    fn generate_state(&self) -> StateParam;
    fn generate_nonce(&self) -> Nonce;
}

pub trait TokenValidator {
    fn validate_id_token(
        &self,
        id_token: &str,
        params: &ValidationParams,
    ) -> Result<IdTokenClaims, IdentityError>;
}

pub trait OidcDiscovery {
    fn resolve(&self, issuer: &Url, client_id: &str) -> Result<OidcProvider, IdentityError>;
}
