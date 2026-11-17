use super::super::domain::error::VewApiError;
use super::super::domain::model::{CacheKey, EnabledContexts, ServiceCatalog};

pub trait SpecFetcher: Send + Sync {
    fn fetch(&self, url: &str, token: &str) -> Result<serde_json::Value, VewApiError>;
}

pub trait CatalogCache: Send + Sync {
    fn get(&self, key: &CacheKey) -> Result<Option<ServiceCatalog>, VewApiError>;
    fn put(&self, key: &CacheKey, catalog: &ServiceCatalog) -> Result<(), VewApiError>;
}

pub trait ApiInvoker: Send + Sync {
    fn invoke(
        &self,
        method: &str,
        url: &str,
        token: &str,
        body: Option<&serde_json::Value>,
    ) -> Result<(u16, serde_json::Value), VewApiError>;
}

pub trait EnabledContextsStore: Send + Sync {
    fn get(&self, profile_name: &str) -> Result<Option<EnabledContexts>, VewApiError>;
    fn put(&self, enabled: &EnabledContexts) -> Result<(), VewApiError>;
}
