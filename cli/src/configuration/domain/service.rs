use crate::configuration::domain::commands::ResolveProfile;
use crate::configuration::domain::error::ConfigError;
use crate::configuration::domain::model::Profile;
use crate::configuration::ports::inbound::ConfigurationService;
use crate::configuration::ports::outbound::ConfigReader;

pub struct ConfigurationServiceImpl<R: ConfigReader> {
    reader: R,
}

impl<R: ConfigReader> ConfigurationServiceImpl<R> {
    pub fn new(reader: R) -> Self {
        Self { reader }
    }
}

impl<R: ConfigReader> ConfigurationService for ConfigurationServiceImpl<R> {
    fn resolve_profile(&self, cmd: ResolveProfile) -> Result<Profile, ConfigError> {
        let config = self.reader.read_config()?;
        config.resolve(cmd.profile_name.as_deref()).cloned()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::configuration::domain::model::{Config, ProfileName};
    use std::collections::HashMap;
    use url::Url;

    struct MockReader {
        config: Result<Config, ConfigError>,
    }

    impl ConfigReader for MockReader {
        fn read_config(&self) -> Result<Config, ConfigError> {
            match &self.config {
                Ok(c) => Ok(c.clone()),
                Err(_) => Err(ConfigError::ReadError(anyhow::anyhow!("mock error"))),
            }
        }
    }

    fn test_config() -> Config {
        let name = ProfileName::new("dev").unwrap();
        let profile = Profile {
            name: name.clone(),
            api_endpoint: Url::parse("https://api.example.com").unwrap(),
            issuer_url: Url::parse("https://auth.example.com").unwrap(),
            oidc_client_id: "client123".to_string(),
            scopes: None,
        };
        let mut profiles = HashMap::new();
        profiles.insert(name.clone(), profile);
        Config {
            default_profile: Some(name),
            profiles,
        }
    }

    #[test]
    fn test_resolve_profile_delegates_to_reader_and_config() {
        // Arrange
        let svc = ConfigurationServiceImpl::new(MockReader {
            config: Ok(test_config()),
        });

        // Act
        let profile = svc
            .resolve_profile(ResolveProfile {
                profile_name: Some("dev".to_string()),
            })
            .unwrap();

        // Assert
        assert_eq!(profile.name.as_str(), "dev");
    }

    #[test]
    fn test_resolve_profile_propagates_reader_error() {
        // Arrange
        let svc = ConfigurationServiceImpl::new(MockReader {
            config: Err(ConfigError::ReadError(anyhow::anyhow!("fail"))),
        });

        // Act
        let result = svc.resolve_profile(ResolveProfile { profile_name: None });

        // Assert
        assert!(matches!(result, Err(ConfigError::ReadError(_))));
    }
}
