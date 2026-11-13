use tempfile::TempDir;
use vew::vew_api::adapters::file_catalog_cache::FileCatalogCache;
use vew::vew_api::domain::model::{
    CacheKey, HttpMethod, Operation, OperationParameter, ParameterLocation, ServiceCatalog,
};
use vew::vew_api::ports::outbound::CatalogCache;

fn test_catalog() -> ServiceCatalog {
    ServiceCatalog {
        bounded_context: "pipelines".into(),
        summary: None,
        description: None,
        operations: vec![Operation {
            cli_name: "get-integrations".into(),
            operation_id: "get_integrations".into(),
            http_method: HttpMethod::Get,
            path_template: "/projects/{project_id}/integrations".into(),
            summary: None,
            description: None,
            parameters: vec![OperationParameter {
                cli_name: "--project-id".into(),
                api_name: "project_id".into(),
                location: ParameterLocation::Path,
                required: true,
                schema_type: "string".into(),
                default_value: None,
            }],
            has_request_body: false,
            request_body_example: None,
            response_example: None,
        }],
    }
}

fn test_key() -> CacheKey {
    CacheKey {
        profile_name: "dev".into(),
        bounded_context: "pipelines".into(),
    }
}

#[test]
fn test_put_then_get_round_trip() {
    // Arrange
    let dir = TempDir::new().unwrap();
    let cache = FileCatalogCache::new(dir.path().join("cache"));
    let key = test_key();
    let catalog = test_catalog();

    // Act
    cache.put(&key, &catalog).unwrap();
    let loaded = cache.get(&key).unwrap().unwrap();

    // Assert
    assert_eq!(loaded.bounded_context, "pipelines");
    assert_eq!(loaded.operations.len(), 1);
    assert_eq!(loaded.operations[0].cli_name, "get-integrations");
    assert_eq!(loaded.operations[0].parameters[0].cli_name, "--project-id");
}

#[test]
fn test_get_nonexistent_returns_none() {
    // Arrange
    let dir = TempDir::new().unwrap();
    let cache = FileCatalogCache::new(dir.path().join("cache"));

    // Act
    let result = cache.get(&test_key()).unwrap();

    // Assert
    assert!(result.is_none());
}

#[test]
fn test_get_corrupted_file_returns_none() {
    // Arrange
    let dir = TempDir::new().unwrap();
    let cache_dir = dir.path().join("cache").join("dev");
    std::fs::create_dir_all(&cache_dir).unwrap();
    std::fs::write(cache_dir.join("pipelines.json"), "not valid json{{{").unwrap();
    let cache = FileCatalogCache::new(dir.path().join("cache"));

    // Act
    let result = cache.get(&test_key()).unwrap();

    // Assert
    assert!(result.is_none());
}

#[test]
fn test_put_creates_directory() {
    // Arrange
    let dir = TempDir::new().unwrap();
    let cache_path = dir.path().join("nested").join("cache");
    let cache = FileCatalogCache::new(cache_path.clone());

    // Act
    cache.put(&test_key(), &test_catalog()).unwrap();

    // Assert
    assert!(cache_path.join("dev").join("pipelines.json").exists());
}

#[test]
fn test_put_produces_pretty_json() {
    // Arrange
    let dir = TempDir::new().unwrap();
    let cache = FileCatalogCache::new(dir.path().join("cache"));

    // Act
    cache.put(&test_key(), &test_catalog()).unwrap();

    // Assert
    let content =
        std::fs::read_to_string(dir.path().join("cache").join("dev").join("pipelines.json"))
            .unwrap();
    assert!(content.contains('\n'));
    assert!(content.contains("get-integrations"));
}

#[cfg(unix)]
#[test]
fn test_unix_file_permissions() {
    use std::os::unix::fs::PermissionsExt;

    // Arrange
    let dir = TempDir::new().unwrap();
    let cache = FileCatalogCache::new(dir.path().join("cache"));

    // Act
    cache.put(&test_key(), &test_catalog()).unwrap();

    // Assert
    let meta =
        std::fs::metadata(dir.path().join("cache").join("dev").join("pipelines.json")).unwrap();
    assert_eq!(meta.permissions().mode() & 0o777, 0o600);
}

#[cfg(unix)]
#[test]
fn test_unix_dir_permissions() {
    use std::os::unix::fs::PermissionsExt;

    // Arrange
    let dir = TempDir::new().unwrap();
    let cache = FileCatalogCache::new(dir.path().join("cache"));

    // Act
    cache.put(&test_key(), &test_catalog()).unwrap();

    // Assert
    let meta = std::fs::metadata(dir.path().join("cache").join("dev")).unwrap();
    assert_eq!(meta.permissions().mode() & 0o777, 0o700);
}
