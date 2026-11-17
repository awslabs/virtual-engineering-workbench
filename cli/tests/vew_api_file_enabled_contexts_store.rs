use tempfile::TempDir;
use vew::vew_api::adapters::file_enabled_contexts_store::FileEnabledContextsStore;
use vew::vew_api::domain::model::{BoundedContextInfo, EnabledContexts};
use vew::vew_api::ports::outbound::EnabledContextsStore;

fn test_enabled() -> EnabledContexts {
    EnabledContexts {
        profile_name: "dev".into(),
        contexts: vec![
            BoundedContextInfo {
                name: "pipelines".into(),
                summary: None,
            },
            BoundedContextInfo {
                name: "projects".into(),
                summary: None,
            },
            BoundedContextInfo {
                name: "packaging".into(),
                summary: None,
            },
        ],
    }
}

#[test]
fn test_put_then_get_round_trip() {
    // Arrange
    let dir = TempDir::new().unwrap();
    let store = FileEnabledContextsStore::new(dir.path().join("cache"));

    // Act
    store.put(&test_enabled()).unwrap();
    let loaded = store.get("dev").unwrap().unwrap();

    // Assert
    assert_eq!(loaded.profile_name, "dev");
    assert_eq!(loaded.contexts, test_enabled().contexts);
}

#[test]
fn test_get_nonexistent_returns_none() {
    // Arrange
    let dir = TempDir::new().unwrap();
    let store = FileEnabledContextsStore::new(dir.path().join("cache"));

    // Act
    let result = store.get("dev").unwrap();

    // Assert
    assert!(result.is_none());
}

#[test]
fn test_get_corrupted_file_returns_none() {
    // Arrange
    let dir = TempDir::new().unwrap();
    let profile_dir = dir.path().join("cache").join("dev");
    std::fs::create_dir_all(&profile_dir).unwrap();
    std::fs::write(profile_dir.join("_enabled.json"), "not valid json{{{").unwrap();
    let store = FileEnabledContextsStore::new(dir.path().join("cache"));

    // Act
    let result = store.get("dev").unwrap();

    // Assert
    assert!(result.is_none());
}

#[test]
fn test_put_creates_directory() {
    // Arrange
    let dir = TempDir::new().unwrap();
    let cache_path = dir.path().join("nested").join("cache");
    let store = FileEnabledContextsStore::new(cache_path.clone());

    // Act
    store.put(&test_enabled()).unwrap();

    // Assert
    assert!(cache_path.join("dev").join("_enabled.json").exists());
}

#[test]
fn test_put_produces_pretty_json() {
    // Arrange
    let dir = TempDir::new().unwrap();
    let store = FileEnabledContextsStore::new(dir.path().join("cache"));

    // Act
    store.put(&test_enabled()).unwrap();

    // Assert
    let content =
        std::fs::read_to_string(dir.path().join("cache").join("dev").join("_enabled.json"))
            .unwrap();
    assert!(content.contains('\n'));
    assert!(content.contains("pipelines"));
}

#[cfg(unix)]
#[test]
fn test_unix_file_permissions() {
    use std::os::unix::fs::PermissionsExt;

    // Arrange
    let dir = TempDir::new().unwrap();
    let store = FileEnabledContextsStore::new(dir.path().join("cache"));

    // Act
    store.put(&test_enabled()).unwrap();

    // Assert
    let meta =
        std::fs::metadata(dir.path().join("cache").join("dev").join("_enabled.json")).unwrap();
    assert_eq!(meta.permissions().mode() & 0o777, 0o600);
}

#[cfg(unix)]
#[test]
fn test_unix_dir_permissions() {
    use std::os::unix::fs::PermissionsExt;

    // Arrange
    let dir = TempDir::new().unwrap();
    let store = FileEnabledContextsStore::new(dir.path().join("cache"));

    // Act
    store.put(&test_enabled()).unwrap();

    // Assert
    let meta = std::fs::metadata(dir.path().join("cache").join("dev")).unwrap();
    assert_eq!(meta.permissions().mode() & 0o777, 0o700);
}
