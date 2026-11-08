use serde::{Deserialize, Serialize};

use crate::str_enum;

str_enum! {
    #[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
    pub enum HttpMethod {
        Get => "GET",
        Post => "POST",
        Put => "PUT",
        Delete => "DELETE",
        Patch => "PATCH",
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum ParameterLocation {
    Path,
    Query,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OperationParameter {
    pub cli_name: String,
    pub api_name: String,
    pub location: ParameterLocation,
    pub required: bool,
    pub schema_type: String,
    pub default_value: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Operation {
    pub cli_name: String,
    pub operation_id: String,
    pub http_method: HttpMethod,
    pub path_template: String,
    pub summary: Option<String>,
    pub description: Option<String>,
    pub parameters: Vec<OperationParameter>,
    pub has_request_body: bool,
    pub request_body_example: Option<serde_json::Value>,
    pub response_example: Option<serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServiceCatalog {
    pub bounded_context: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub summary: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
    pub operations: Vec<Operation>,
}

impl ServiceCatalog {
    pub fn find_operation(&self, cli_name: &str) -> Option<&Operation> {
        self.operations.iter().find(|op| op.cli_name == cli_name)
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct CacheKey {
    pub profile_name: String,
    pub bounded_context: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct InvocationResult {
    pub status_code: u16,
    pub body: serde_json::Value,
}

impl std::fmt::Display for InvocationResult {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "{}",
            serde_json::to_string_pretty(&self.body).unwrap_or_default()
        )
    }
}

#[derive(Debug)]
pub enum ExecuteResult {
    Help(String),
    Response(InvocationResult),
}
use super::error::VewApiError;

str_enum! {
    #[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
    pub enum BoundedContext {
        AccessManagement     => "access-management",
        BusinessMetrics      => "business-metrics",
        Executing            => "executing",
        Notifications        => "notifications",
        Packaging            => "packaging",
        Pipelines            => "pipelines",
        Pricing              => "pricing",
        Projects             => "projects",
        Provisioning         => "provisioning",
        ProvisioningCompound => "provisioning-compound",
        Publishing           => "publishing",
        PublishingCompound   => "publishing-compound",
        TestGeneration       => "test-generation",
    }
}

impl BoundedContext {
    pub fn parse(s: &str) -> Result<Self, VewApiError> {
        Self::try_from_str(s).ok_or_else(|| VewApiError::UnknownBoundedContext {
            name: s.to_string(),
            available: Self::all()
                .iter()
                .map(|bc| bc.as_str().to_string())
                .collect(),
        })
    }
}

/// Outcome of attempting to refresh a single BC's cache during bulk init.
#[derive(Debug, Clone, Serialize)]
pub struct BcRefreshOutcome {
    pub bounded_context: BoundedContext,
    pub result: Result<usize, String>,
}

/// Result of a bulk cache init across all bounded contexts.
#[derive(Debug, Clone, Serialize)]
pub struct BulkRefreshResult {
    pub outcomes: Vec<BcRefreshOutcome>,
}

impl BulkRefreshResult {
    pub fn enabled_contexts(&self) -> Vec<&BoundedContext> {
        self.outcomes
            .iter()
            .filter_map(|o| o.result.is_ok().then_some(&o.bounded_context))
            .collect()
    }
}

/// Summary info for a single bounded context.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct BoundedContextInfo {
    pub name: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub summary: Option<String>,
}

/// The set of BCs whose specs were successfully fetched for a profile.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct EnabledContexts {
    pub profile_name: String,
    pub contexts: Vec<BoundedContextInfo>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_from_str_valid_pipelines() {
        // Act
        let result = BoundedContext::parse("pipelines");

        // Assert
        assert_eq!(result.unwrap(), BoundedContext::Pipelines);
    }

    #[test]
    fn test_from_str_valid_access_management() {
        // Act
        let result = BoundedContext::parse("access-management");

        // Assert
        assert_eq!(result.unwrap(), BoundedContext::AccessManagement);
    }

    #[test]
    fn test_from_str_invalid() {
        // Act
        let result = BoundedContext::parse("nonexistent");

        // Assert
        match result {
            Err(VewApiError::UnknownBoundedContext { name, available }) => {
                assert_eq!(name, "nonexistent");
                assert!(available.contains(&"pipelines".to_string()));
                assert_eq!(available.len(), 13);
            }
            _ => panic!("expected UnknownBoundedContext"),
        }
    }

    #[test]
    fn test_as_str_round_trip_all_variants() {
        // Act & Assert
        for bc in BoundedContext::all() {
            let s = bc.as_str();
            let round_tripped = BoundedContext::parse(s).unwrap();
            assert_eq!(*bc, round_tripped);
        }
    }

    #[test]
    fn test_bulk_refresh_result_enabled_contexts_filters_ok() {
        // Arrange
        let result = BulkRefreshResult {
            outcomes: vec![
                BcRefreshOutcome {
                    bounded_context: BoundedContext::Pipelines,
                    result: Ok(23),
                },
                BcRefreshOutcome {
                    bounded_context: BoundedContext::Projects,
                    result: Err("HTTP 404".to_string()),
                },
                BcRefreshOutcome {
                    bounded_context: BoundedContext::Packaging,
                    result: Ok(8),
                },
            ],
        };

        // Act
        let enabled = result.enabled_contexts();

        // Assert
        assert_eq!(enabled.len(), 2);
        assert_eq!(*enabled[0], BoundedContext::Pipelines);
        assert_eq!(*enabled[1], BoundedContext::Packaging);
    }

    #[test]
    fn test_enabled_contexts_serde_round_trip() {
        // Arrange
        let enabled = EnabledContexts {
            profile_name: "dev".to_string(),
            contexts: vec![
                BoundedContextInfo {
                    name: "pipelines".to_string(),
                    summary: None,
                },
                BoundedContextInfo {
                    name: "projects".to_string(),
                    summary: None,
                },
            ],
        };

        // Act
        let json = serde_json::to_string(&enabled).unwrap();
        let deserialized: EnabledContexts = serde_json::from_str(&json).unwrap();

        // Assert
        assert_eq!(deserialized, enabled);
    }
}
