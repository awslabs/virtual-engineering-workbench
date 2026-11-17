use super::super::domain::commands::ResolveProfile;
use super::super::domain::error::ConfigError;
use super::super::domain::model::Profile;

pub trait ConfigurationService {
    fn resolve_profile(&self, cmd: ResolveProfile) -> Result<Profile, ConfigError>;
}
