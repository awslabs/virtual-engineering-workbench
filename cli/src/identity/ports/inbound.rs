use super::super::domain::commands::{GetAccessToken, GetToken, Login, Logout};
use super::super::domain::error::IdentityError;
use super::super::domain::model::{LoginResult, LogoutResult};

pub trait IdentityService {
    fn login(&self, cmd: Login) -> Result<LoginResult, IdentityError>;
    fn logout(&self, cmd: Logout) -> Result<LogoutResult, IdentityError>;
    fn get_access_token(&self, cmd: GetAccessToken) -> Result<String, IdentityError>;
    fn get_token(&self, cmd: GetToken) -> Result<String, IdentityError>;
}
