pub trait AuthProvider {
    fn auth_header(&self, token: &str) -> (&str, String);
}

pub struct BearerAuthProvider;

impl AuthProvider for BearerAuthProvider {
    fn auth_header(&self, token: &str) -> (&str, String) {
        ("Authorization", format!("Bearer {}", token))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_bearer_auth_provider_produces_correct_header() {
        // Arrange
        let provider = BearerAuthProvider;

        // Act
        let (key, value) = provider.auth_header("my-token-123");

        // Assert
        assert_eq!(key, "Authorization");
        assert_eq!(value, "Bearer my-token-123");
    }
}
