use std::collections::HashMap;
use std::path::PathBuf;

use serde::Deserialize;
use url::Url;

use crate::configuration::domain::error::ConfigError;
use crate::configuration::domain::model::{Config, Profile, ProfileName};
use crate::configuration::ports::outbound::ConfigReader;

#[derive(Deserialize)]
struct TomlConfig {
    default_profile: Option<String>,
    #[serde(default)]
    profiles: HashMap<String, TomlProfile>,
}

#[derive(Deserialize)]
struct TomlProfile {
    api_endpoint: Option<String>,
    issuer_url: Option<String>,
    oidc_client_id: Option<String>,
    scopes: Option<Vec<String>>,
}

pub struct FileConfigReader {
    path: PathBuf,
}

impl FileConfigReader {
    pub fn new(path: PathBuf) -> Self {
        Self { path }
    }

    pub fn default_path() -> Result<PathBuf, ConfigError> {
        let home = dirs::home_dir().ok_or_else(|| {
            ConfigError::ReadError(anyhow::anyhow!("cannot determine home directory"))
        })?;
        Ok(home.join(".vew").join("config"))
    }
}

impl ConfigReader for FileConfigReader {
    fn read_config(&self) -> Result<Config, ConfigError> {
        if !self.path.exists() {
            return Ok(Config::default());
        }
        let content =
            std::fs::read_to_string(&self.path).map_err(|e| ConfigError::ReadError(e.into()))?;
        let toml_cfg: TomlConfig =
            toml::from_str(&content).map_err(|e| ConfigError::ReadError(e.into()))?;

        let mut profiles = HashMap::new();
        for (name, tp) in toml_cfg.profiles {
            let profile = to_profile(&name, tp)?;
            profiles.insert(profile.name.clone(), profile);
        }

        let default_profile = toml_cfg
            .default_profile
            .map(|d| ProfileName::new(&d))
            .transpose()?;

        Ok(Config {
            default_profile,
            profiles,
        })
    }
}

fn to_profile(name: &str, tp: TomlProfile) -> Result<Profile, ConfigError> {
    let api_endpoint = required_url(name, "api_endpoint", tp.api_endpoint)?;
    let issuer_url = required_url(name, "issuer_url", tp.issuer_url)?;
    let oidc_client_id = tp
        .oidc_client_id
        .ok_or_else(|| ConfigError::MissingProperty {
            profile: name.to_string(),
            property: "oidc_client_id".to_string(),
        })?;

    Ok(Profile {
        name: ProfileName::new(name)?,
        api_endpoint,
        issuer_url,
        oidc_client_id,
        scopes: tp.scopes,
    })
}

fn required_url(profile: &str, property: &str, value: Option<String>) -> Result<Url, ConfigError> {
    let raw = value.ok_or_else(|| ConfigError::MissingProperty {
        profile: profile.to_string(),
        property: property.to_string(),
    })?;
    Url::parse(&raw).map_err(|e| {
        ConfigError::ReadError(anyhow::anyhow!(
            "profile '{}' property '{}': {}",
            profile,
            property,
            e
        ))
    })
}
