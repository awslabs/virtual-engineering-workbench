use std::collections::HashMap;
use url::Url;

use super::error::ConfigError;

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct ProfileName(String);

impl ProfileName {
    pub fn new(name: &str) -> Result<Self, ConfigError> {
        let trimmed = name.trim();
        if trimmed.is_empty() {
            return Err(ConfigError::EmptyProfileName);
        }
        if trimmed.contains('/')
            || trimmed.contains('\\')
            || trimmed.contains('\0')
            || trimmed == "."
            || trimmed == ".."
        {
            return Err(ConfigError::InvalidProfileName {
                name: trimmed.to_string(),
            });
        }
        Ok(Self(trimmed.to_string()))
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

#[derive(Debug, Clone)]
pub struct Profile {
    pub name: ProfileName,
    pub api_endpoint: Url,
    pub issuer_url: Url,
    pub oidc_client_id: String,
    pub scopes: Option<Vec<String>>,
}

#[derive(Debug, Clone, Default)]
pub struct Config {
    pub default_profile: Option<ProfileName>,
    pub profiles: HashMap<ProfileName, Profile>,
}

impl Config {
    pub fn resolve(&self, name: Option<&str>) -> Result<&Profile, ConfigError> {
        let key = match name {
            Some(n) => ProfileName::new(n)?,
            None => self
                .default_profile
                .clone()
                .ok_or(ConfigError::NoProfileSpecified)?,
        };
        self.profiles
            .get(&key)
            .ok_or_else(|| ConfigError::ProfileNotFound {
                name: key.as_str().to_string(),
                available: self
                    .profiles
                    .keys()
                    .map(|k| k.as_str().to_string())
                    .collect(),
            })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_profile(name: &str) -> Profile {
        Profile {
            name: ProfileName(name.to_string()),
            api_endpoint: Url::parse("https://api.example.com").unwrap(),
            issuer_url: Url::parse("https://auth.example.com").unwrap(),
            oidc_client_id: "client123".to_string(),
            scopes: None,
        }
    }

    fn make_config(profiles: &[&str], default: Option<&str>) -> Config {
        let mut map = HashMap::new();
        for &name in profiles {
            map.insert(ProfileName(name.to_string()), make_profile(name));
        }
        Config {
            default_profile: default.map(|d| ProfileName(d.to_string())),
            profiles: map,
        }
    }

    #[test]
    fn test_profile_name_rejects_empty() {
        // Act
        let result = ProfileName::new("");

        // Assert
        assert!(matches!(result, Err(ConfigError::EmptyProfileName)));
    }

    #[test]
    fn test_profile_name_rejects_whitespace() {
        // Act
        let result = ProfileName::new("   ");

        // Assert
        assert!(matches!(result, Err(ConfigError::EmptyProfileName)));
    }

    #[test]
    fn test_profile_name_accepts_valid() {
        // Act
        let name = ProfileName::new("dev").unwrap();

        // Assert
        assert_eq!(name.as_str(), "dev");
    }

    #[test]
    fn test_profile_name_trims_whitespace() {
        // Act
        let name = ProfileName::new(" dev ").unwrap();

        // Assert
        assert_eq!(name.as_str(), "dev");
    }

    #[test]
    fn test_profile_name_rejects_forward_slash() {
        // Act
        let result = ProfileName::new("../evil");

        // Assert
        assert!(matches!(
            result,
            Err(ConfigError::InvalidProfileName { .. })
        ));
    }

    #[test]
    fn test_profile_name_rejects_backslash() {
        // Act
        let result = ProfileName::new("foo\\bar");

        // Assert
        assert!(matches!(
            result,
            Err(ConfigError::InvalidProfileName { .. })
        ));
    }

    #[test]
    fn test_profile_name_rejects_null_byte() {
        // Act
        let result = ProfileName::new("foo\0bar");

        // Assert
        assert!(matches!(
            result,
            Err(ConfigError::InvalidProfileName { .. })
        ));
    }

    #[test]
    fn test_profile_name_rejects_dot_dot() {
        // Act
        let result = ProfileName::new("..");

        // Assert
        assert!(matches!(
            result,
            Err(ConfigError::InvalidProfileName { .. })
        ));
    }

    #[test]
    fn test_profile_name_rejects_single_dot() {
        // Act
        let result = ProfileName::new(".");

        // Assert
        assert!(matches!(
            result,
            Err(ConfigError::InvalidProfileName { .. })
        ));
    }

    #[test]
    fn test_config_resolve_explicit_name() {
        // Arrange
        let config = make_config(&["dev", "prod"], Some("dev"));

        // Act
        let profile = config.resolve(Some("prod")).unwrap();

        // Assert
        assert_eq!(profile.name.as_str(), "prod");
    }

    #[test]
    fn test_config_resolve_default() {
        // Arrange
        let config = make_config(&["dev", "prod"], Some("dev"));

        // Act
        let profile = config.resolve(None).unwrap();

        // Assert
        assert_eq!(profile.name.as_str(), "dev");
    }

    #[test]
    fn test_config_resolve_no_profile_no_default() {
        // Arrange
        let config = make_config(&["dev"], None);

        // Act
        let result = config.resolve(None);

        // Assert
        assert!(matches!(result, Err(ConfigError::NoProfileSpecified)));
    }

    #[test]
    fn test_config_resolve_unknown_profile() {
        // Arrange
        let config = make_config(&["dev"], Some("dev"));

        // Act
        let err = config.resolve(Some("staging")).unwrap_err();

        // Assert
        match err {
            ConfigError::ProfileNotFound { name, available } => {
                assert_eq!(name, "staging");
                assert!(available.contains(&"dev".to_string()));
            }
            _ => panic!("expected ProfileNotFound, got {:?}", err),
        }
    }
}
