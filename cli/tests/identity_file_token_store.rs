use chrono::{Duration, Utc};
use tempfile::TempDir;
use vew::identity::adapters::file_token_store::FileTokenStore;
use vew::identity::domain::model::TokenSet;
use vew::identity::ports::outbound::TokenStore;

fn test_tokens() -> TokenSet {
    TokenSet {
        access_token: "access_123".into(),
        id_token: "id_456".into(),
        refresh_token: "refresh_789".into(),
        expires_at: Utc::now() + Duration::seconds(3600),
    }
}

#[test]
fn test_save_and_load_round_trip() {
    // Arrange
    let dir = TempDir::new().unwrap();
    let store = FileTokenStore::new(dir.path().join("tokens"));

    // Act
    store.save("dev", &test_tokens()).unwrap();
    let loaded = store.load("dev").unwrap().unwrap();

    // Assert
    assert_eq!(loaded.access_token, "access_123");
    assert_eq!(loaded.id_token, "id_456");
    assert_eq!(loaded.refresh_token, "refresh_789");
}

#[test]
fn test_load_nonexistent_returns_none() {
    // Arrange
    let dir = TempDir::new().unwrap();
    let store = FileTokenStore::new(dir.path().join("tokens"));

    // Act
    let result = store.load("nonexistent").unwrap();

    // Assert
    assert!(result.is_none());
}

#[test]
fn test_delete_removes_file() {
    // Arrange
    let dir = TempDir::new().unwrap();
    let store = FileTokenStore::new(dir.path().join("tokens"));
    store.save("dev", &test_tokens()).unwrap();

    // Act
    store.delete("dev").unwrap();

    // Assert
    assert!(store.load("dev").unwrap().is_none());
}

#[test]
fn test_delete_nonexistent_is_ok() {
    // Arrange
    let dir = TempDir::new().unwrap();
    let store = FileTokenStore::new(dir.path().join("tokens"));

    // Act
    let result = store.delete("nonexistent");

    // Assert
    assert!(result.is_ok());
}

#[test]
fn test_save_creates_directory() {
    // Arrange
    let dir = TempDir::new().unwrap();
    let tokens_dir = dir.path().join("nested").join("tokens");
    let store = FileTokenStore::new(tokens_dir.clone());

    // Act
    store.save("dev", &test_tokens()).unwrap();

    // Assert
    assert!(tokens_dir.exists());
}

#[test]
fn test_save_is_atomic() {
    // Arrange
    let dir = TempDir::new().unwrap();
    let tokens_dir = dir.path().join("tokens");
    let store = FileTokenStore::new(tokens_dir.clone());

    // Act
    store.save("dev", &test_tokens()).unwrap();

    // Assert
    assert!(!tokens_dir.join("dev.json.tmp").exists());
    assert!(tokens_dir.join("dev.json").exists());
}

#[cfg(unix)]
#[test]
fn test_unix_file_permissions() {
    use std::os::unix::fs::PermissionsExt;

    // Arrange
    let dir = TempDir::new().unwrap();
    let store = FileTokenStore::new(dir.path().join("tokens"));

    // Act
    store.save("dev", &test_tokens()).unwrap();

    // Assert
    let meta = std::fs::metadata(dir.path().join("tokens").join("dev.json")).unwrap();
    assert_eq!(meta.permissions().mode() & 0o777, 0o600);
}

#[cfg(unix)]
#[test]
fn test_unix_dir_permissions() {
    use std::os::unix::fs::PermissionsExt;

    // Arrange
    let dir = TempDir::new().unwrap();
    let tokens_dir = dir.path().join("tokens");
    let store = FileTokenStore::new(tokens_dir.clone());

    // Act
    store.save("dev", &test_tokens()).unwrap();

    // Assert
    let meta = std::fs::metadata(&tokens_dir).unwrap();
    assert_eq!(meta.permissions().mode() & 0o777, 0o700);
}
