use std::io::Write;
use tempfile::NamedTempFile;
use vew::configuration::adapters::file_config_reader::FileConfigReader;
use vew::configuration::domain::error::ConfigError;
use vew::configuration::ports::outbound::ConfigReader;

#[test]
fn test_read_valid_config() {
    // Arrange
    let mut f = NamedTempFile::new().unwrap();
    write!(
        f,
        r#"
default_profile = "dev"

[profiles.dev]
api_endpoint = "https://api.dev.example.com"
issuer_url = "https://auth.dev.example.com"
oidc_client_id = "client-dev"

[profiles.prod]
api_endpoint = "https://api.example.com"
issuer_url = "https://auth.example.com"
oidc_client_id = "client-prod"
"#
    )
    .unwrap();
    let reader = FileConfigReader::new(f.path().to_path_buf());

    // Act
    let config = reader.read_config().unwrap();

    // Assert
    assert_eq!(config.default_profile.as_ref().unwrap().as_str(), "dev");
    assert_eq!(config.profiles.len(), 2);
    let dev = config.resolve(Some("dev")).unwrap();
    assert_eq!(dev.api_endpoint.as_str(), "https://api.dev.example.com/");
    assert_eq!(dev.issuer_url.as_str(), "https://auth.dev.example.com/");
    assert_eq!(dev.oidc_client_id, "client-dev");
    let prod = config.resolve(Some("prod")).unwrap();
    assert_eq!(prod.oidc_client_id, "client-prod");
}

#[test]
fn test_read_missing_file() {
    // Arrange
    let reader = FileConfigReader::new("/tmp/nonexistent_vew_config_test".into());

    // Act
    let config = reader.read_config().unwrap();

    // Assert
    assert!(config.profiles.is_empty());
    assert!(config.default_profile.is_none());
}

#[test]
fn test_read_malformed_toml() {
    // Arrange
    let mut f = NamedTempFile::new().unwrap();
    write!(f, "this is not [valid toml {{{{").unwrap();
    let reader = FileConfigReader::new(f.path().to_path_buf());

    // Act
    let result = reader.read_config();

    // Assert
    assert!(matches!(result, Err(ConfigError::ReadError(_))));
}

#[test]
fn test_read_profile_missing_api_endpoint() {
    // Arrange
    let mut f = NamedTempFile::new().unwrap();
    write!(
        f,
        r#"
[profiles.broken]
issuer_url = "https://auth.example.com"
oidc_client_id = "client123"
"#
    )
    .unwrap();
    let reader = FileConfigReader::new(f.path().to_path_buf());

    // Act
    let result = reader.read_config();

    // Assert
    match result {
        Err(ConfigError::MissingProperty { profile, property }) => {
            assert_eq!(profile, "broken");
            assert_eq!(property, "api_endpoint");
        }
        other => panic!("expected MissingProperty, got {:?}", other),
    }
}

#[test]
fn test_read_config_with_default_profile() {
    // Arrange
    let mut f = NamedTempFile::new().unwrap();
    write!(
        f,
        r#"
default_profile = "staging"

[profiles.staging]
api_endpoint = "https://api.staging.example.com"
issuer_url = "https://auth.staging.example.com"
oidc_client_id = "client-staging"
"#
    )
    .unwrap();
    let reader = FileConfigReader::new(f.path().to_path_buf());

    // Act
    let config = reader.read_config().unwrap();
    let profile = config.resolve(None).unwrap();

    // Assert
    assert_eq!(profile.name.as_str(), "staging");
}

#[test]
fn test_read_config_with_scopes() {
    // Arrange
    let mut f = NamedTempFile::new().unwrap();
    write!(
        f,
        r#"
[profiles.dev]
api_endpoint = "https://api.example.com"
issuer_url = "https://auth.example.com"
oidc_client_id = "client123"
scopes = ["openid", "profile", "custom:read"]
"#
    )
    .unwrap();
    let reader = FileConfigReader::new(f.path().to_path_buf());

    // Act
    let config = reader.read_config().unwrap();
    let profile = config.resolve(Some("dev")).unwrap();

    // Assert
    assert_eq!(
        profile.scopes.as_ref().unwrap(),
        &vec![
            "openid".to_string(),
            "profile".to_string(),
            "custom:read".to_string()
        ]
    );
}
