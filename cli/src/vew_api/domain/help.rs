use super::model::{Operation, ServiceCatalog};

fn indent_json(value: &serde_json::Value, spaces: usize) -> String {
    let json = serde_json::to_string_pretty(value).unwrap_or_default();
    let pad: String = " ".repeat(spaces);
    json.lines()
        .map(|line| format!("{}{}\n", pad, line))
        .collect()
}

/// Builds a compact list of available operation names.
pub fn build_operations_list(catalog: &ServiceCatalog) -> String {
    let mut out = String::new();
    if let Some(s) = &catalog.summary {
        out.push_str(&format!("{}\n", s));
    }
    if let Some(d) = &catalog.description {
        out.push_str(&format!("\n{}\n", d));
    }
    out.push_str(&format!(
        "\nAvailable operations for '{}':\n\n",
        catalog.bounded_context
    ));
    let mut ops: Vec<&Operation> = catalog.operations.iter().collect();
    ops.sort_by_key(|o| &o.cli_name);
    for op in ops {
        match &op.summary {
            Some(s) => out.push_str(&format!("  {:<30} {}\n", op.cli_name, s)),
            None => out.push_str(&format!("  {}\n", op.cli_name)),
        }
    }
    out.push_str(&format!(
        "\nRun `vew {} <operation>` to view parameters and usage.\n",
        catalog.bounded_context
    ));
    out
}

/// Builds a detailed help page for a single operation.
pub fn build_operation_detail(bc_name: &str, op: &Operation) -> String {
    let mut usage = format!("vew {} {}", bc_name, op.cli_name);
    for param in &op.parameters {
        if param.required {
            usage.push_str(&format!(" {} <{}>", param.cli_name, param.schema_type));
        }
    }
    for param in &op.parameters {
        if !param.required {
            usage.push_str(&format!(" [{} <{}>]", param.cli_name, param.schema_type));
        }
    }
    if op.has_request_body {
        usage.push_str(" --body <JSON>");
    }

    let mut out = format!("Usage: {}\n", usage);
    if let Some(s) = &op.summary {
        out.push_str(&format!("\n{}\n", s));
    }
    if let Some(d) = &op.description {
        out.push_str(&format!("\n{}\n", d));
    }
    if !op.parameters.is_empty() || op.has_request_body {
        out.push_str("\nParameters:\n");
        for param in &op.parameters {
            let req = if param.required {
                "(required)"
            } else {
                "(optional)"
            };
            let default = match &param.default_value {
                Some(v) => format!(" [default: {}]", v),
                None => String::new(),
            };
            out.push_str(&format!(
                "  {:<40} {} {}{}\n",
                param.cli_name, param.schema_type, req, default
            ));
        }
        if op.has_request_body {
            out.push_str(&format!("  {:<40} JSON string\n", "--body"));
        }
    }
    if let Some(req_example) = &op.request_body_example {
        out.push_str("\nRequest body:\n");
        out.push_str(&indent_json(req_example, 2));
    }
    if let Some(resp_example) = &op.response_example {
        out.push_str("\nResponse:\n");
        out.push_str(&indent_json(resp_example, 2));
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::vew_api::domain::model::{
        HttpMethod, Operation, OperationParameter, ParameterLocation, ServiceCatalog,
    };

    #[test]
    fn test_build_operations_list_is_compact_and_sorted() {
        // Arrange
        let catalog = ServiceCatalog {
            bounded_context: "pipelines".to_string(),
            summary: None,
            description: None,
            operations: vec![
                Operation {
                    cli_name: "get-integrations".to_string(),
                    operation_id: "get_integrations".to_string(),
                    http_method: HttpMethod::Get,
                    path_template: "/integrations".to_string(),
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
                },
                Operation {
                    cli_name: "create-integration".to_string(),
                    operation_id: "create_integration".to_string(),
                    http_method: HttpMethod::Post,
                    path_template: "/integrations".to_string(),
                    summary: None,
                    description: None,
                    parameters: vec![],
                    has_request_body: true,
                    request_body_example: None,
                    response_example: None,
                },
            ],
        };

        // Act
        let list = build_operations_list(&catalog);

        // Assert
        assert!(list.contains("pipelines"));
        assert!(list.contains("get-integrations"));
        assert!(list.contains("create-integration"));
        assert!(!list.contains("--project-id"));
        assert!(!list.contains("--body"));
        assert!(list.contains("to view parameters and usage"));
        let create_pos = list.find("create-integration").unwrap();
        let get_pos = list.find("get-integrations").unwrap();
        assert!(create_pos < get_pos);
    }

    #[test]
    fn test_build_operation_detail_shows_full_invocation_syntax() {
        // Arrange
        let op = Operation {
            cli_name: "get-integrations".to_string(),
            operation_id: "get_integrations".to_string(),
            http_method: HttpMethod::Get,
            path_template: "/projects/{project_id}/integrations".to_string(),
            summary: None,
            description: None,
            parameters: vec![
                OperationParameter {
                    cli_name: "--project-id".into(),
                    api_name: "project_id".into(),
                    location: ParameterLocation::Path,
                    required: true,
                    schema_type: "string".into(),
                    default_value: None,
                },
                OperationParameter {
                    cli_name: "--status".into(),
                    api_name: "status".into(),
                    location: ParameterLocation::Query,
                    required: false,
                    schema_type: "string".into(),
                    default_value: None,
                },
            ],
            has_request_body: false,
            request_body_example: None,
            response_example: None,
        };

        // Act
        let detail = build_operation_detail("pipelines", &op);

        // Assert
        assert!(detail.starts_with(
            "Usage: vew pipelines get-integrations --project-id <string> [--status <string>]"
        ));
    }

    #[test]
    fn test_build_operation_detail_shows_default_value() {
        // Arrange
        let op = Operation {
            cli_name: "list-items".to_string(),
            operation_id: "list_items".to_string(),
            http_method: HttpMethod::Get,
            path_template: "/items".to_string(),
            summary: None,
            description: None,
            parameters: vec![OperationParameter {
                cli_name: "--page-size".into(),
                api_name: "pageSize".into(),
                location: ParameterLocation::Query,
                required: false,
                schema_type: "integer".into(),
                default_value: Some("10".into()),
            }],
            has_request_body: false,
            request_body_example: None,
            response_example: None,
        };

        // Act
        let detail = build_operation_detail("test", &op);

        // Assert
        assert!(detail.starts_with("Usage: vew test list-items"));
        assert!(detail.contains("[default: 10]"));
    }

    #[test]
    fn test_build_operation_detail_shows_request_and_response_examples() {
        // Arrange
        let op = Operation {
            cli_name: "create-item".to_string(),
            operation_id: "create_item".to_string(),
            http_method: HttpMethod::Post,
            path_template: "/items".to_string(),
            summary: None,
            description: None,
            parameters: vec![],
            has_request_body: true,
            request_body_example: Some(serde_json::json!({"name": "string"})),
            response_example: Some(serde_json::json!({"id": "string"})),
        };

        // Act
        let detail = build_operation_detail("test", &op);

        // Assert
        assert!(detail.starts_with("Usage: vew test create-item --body <JSON>"));
        assert!(detail.contains("Request body:"));
        assert!(detail.contains("\"name\": \"string\""));
        assert!(detail.contains("Response:"));
        assert!(detail.contains("\"id\": \"string\""));
    }
}
