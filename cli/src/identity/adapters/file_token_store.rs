use std::path::PathBuf;

use crate::identity::domain::error::IdentityError;
use crate::identity::domain::model::TokenSet;
use crate::identity::ports::outbound::TokenStore;
use crate::shared::fs::{atomic_write_private, ensure_private_dir, warn_if_world_readable};

pub struct FileTokenStore {
    base_dir: PathBuf,
}

impl FileTokenStore {
    pub fn new(base_dir: PathBuf) -> Self {
        Self { base_dir }
    }

    pub fn default_dir() -> Result<PathBuf, IdentityError> {
        let home = dirs::home_dir().ok_or_else(|| {
            IdentityError::StoreError(anyhow::anyhow!("cannot determine home directory"))
        })?;
        Ok(home.join(".vew").join("tokens"))
    }

    fn token_path(&self, profile_id: &str) -> PathBuf {
        self.base_dir.join(format!("{profile_id}.json"))
    }
}

impl TokenStore for FileTokenStore {
    fn save(&self, profile_id: &str, tokens: &TokenSet) -> Result<(), IdentityError> {
        ensure_private_dir(&self.base_dir).map_err(|e| IdentityError::StoreError(e.into()))?;
        let json = serde_json::to_string_pretty(tokens)
            .map_err(|e| IdentityError::StoreError(e.into()))?;
        atomic_write_private(&self.token_path(profile_id), json.as_bytes())
            .map_err(|e| IdentityError::StoreError(e.into()))
    }

    fn load(&self, profile_id: &str) -> Result<Option<TokenSet>, IdentityError> {
        let path = self.token_path(profile_id);
        if !path.exists() {
            return Ok(None);
        }
        warn_if_world_readable(&path);
        let content =
            std::fs::read_to_string(&path).map_err(|e| IdentityError::StoreError(e.into()))?;
        let tokens: TokenSet =
            serde_json::from_str(&content).map_err(|e| IdentityError::StoreError(e.into()))?;
        Ok(Some(tokens))
    }

    fn delete(&self, profile_id: &str) -> Result<(), IdentityError> {
        let path = self.token_path(profile_id);
        if path.exists() {
            std::fs::remove_file(&path).map_err(|e| IdentityError::StoreError(e.into()))?;
        }
        Ok(())
    }
}
