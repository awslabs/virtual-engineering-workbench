use super::model::{OidcProvider, TokenType};

pub struct Login {
    pub profile_id: String,
    pub provider: OidcProvider,
    pub no_browser: bool,
}

pub struct Logout {
    pub profile_id: String,
    pub provider: OidcProvider,
}

pub struct GetAccessToken {
    pub profile_id: String,
    pub provider: OidcProvider,
}

pub struct GetToken {
    pub profile_id: String,
    pub provider: OidcProvider,
    pub token_type: TokenType,
}
