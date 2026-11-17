use std::path::PathBuf;

use crate::debug_log;
use crate::shared::constants::{CACHE_DIR, ENABLED_CONTEXTS_FILE, VEW_DIR};
use crate::shared::fs::{atomic_write_private, ensure_private_dir};
use crate::vew_api::domain::error::VewApiError;
use crate::vew_api::domain::model::EnabledContexts;
use crate::vew_api::ports::outbound::EnabledContextsStore;

pub struct FileEnabledContextsStore {
    base_dir: PathBuf,
}

impl FileEnabledContextsStore {
    pub fn new(base_dir: PathBuf) -> Self {
        Self { base_dir }
    }

    pub fn default_dir() -> Result<PathBuf, VewApiError> {
        let home = dirs::home_dir()
            .ok_or_else(|| VewApiError::CacheError("cannot determine home directory".into()))?;
        Ok(home.join(VEW_DIR).join(CACHE_DIR))
    }

    fn path_for(&self, profile_name: &str) -> PathBuf {
        self.base_dir.join(profile_name).join(ENABLED_CONTEXTS_FILE)
    }
}

impl EnabledContextsStore for FileEnabledContextsStore {
    fn get(&self, profile_name: &str) -> Result<Option<EnabledContexts>, VewApiError> {
        let path = self.path_for(profile_name);
        if !path.exists() {
            return Ok(None);
        }
        let content =
            std::fs::read_to_string(&path).map_err(|e| VewApiError::CacheError(e.to_string()))?;
        match serde_json::from_str::<EnabledContexts>(&content) {
            Ok(enabled) => Ok(Some(enabled)),
            Err(e) => {
                debug_log!("enabled contexts deserialization failed: {}", e);
                Ok(None)
            }
        }
    }

    fn put(&self, enabled: &EnabledContexts) -> Result<(), VewApiError> {
        let path = self.path_for(&enabled.profile_name);
        let dir = path.parent().unwrap();
        ensure_private_dir(dir).map_err(|e| VewApiError::CacheError(e.to_string()))?;
        let json = serde_json::to_string_pretty(enabled)
            .map_err(|e| VewApiError::CacheError(e.to_string()))?;
        atomic_write_private(&path, json.as_bytes())
            .map_err(|e| VewApiError::CacheError(e.to_string()))
    }
}
