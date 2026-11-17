use std::path::PathBuf;

use crate::debug_log;
use crate::shared::constants::{CACHE_DIR, VEW_DIR};
use crate::shared::fs::{atomic_write_private, ensure_private_dir};
use crate::vew_api::domain::error::VewApiError;
use crate::vew_api::domain::model::{CacheKey, ServiceCatalog};
use crate::vew_api::ports::outbound::CatalogCache;

pub struct FileCatalogCache {
    base_dir: PathBuf,
}

impl FileCatalogCache {
    pub fn new(base_dir: PathBuf) -> Self {
        Self { base_dir }
    }

    pub fn default_dir() -> Result<PathBuf, VewApiError> {
        let home = dirs::home_dir()
            .ok_or_else(|| VewApiError::CacheError("cannot determine home directory".into()))?;
        Ok(home.join(VEW_DIR).join(CACHE_DIR))
    }

    fn path_for(&self, key: &CacheKey) -> PathBuf {
        self.base_dir
            .join(&key.profile_name)
            .join(format!("{}.json", key.bounded_context))
    }
}

impl CatalogCache for FileCatalogCache {
    fn get(&self, key: &CacheKey) -> Result<Option<ServiceCatalog>, VewApiError> {
        let path = self.path_for(key);
        if !path.exists() {
            return Ok(None);
        }
        let content =
            std::fs::read_to_string(&path).map_err(|e| VewApiError::CacheError(e.to_string()))?;
        match serde_json::from_str::<ServiceCatalog>(&content) {
            Ok(catalog) => Ok(Some(catalog)),
            Err(e) => {
                debug_log!("cache deserialization failed, treating as miss: {}", e);
                Ok(None)
            }
        }
    }

    fn put(&self, key: &CacheKey, catalog: &ServiceCatalog) -> Result<(), VewApiError> {
        let path = self.path_for(key);
        let dir = path.parent().unwrap();
        ensure_private_dir(dir).map_err(|e| VewApiError::CacheError(e.to_string()))?;
        let json = serde_json::to_string_pretty(catalog)
            .map_err(|e| VewApiError::CacheError(e.to_string()))?;
        atomic_write_private(&path, json.as_bytes())
            .map_err(|e| VewApiError::CacheError(e.to_string()))
    }
}
