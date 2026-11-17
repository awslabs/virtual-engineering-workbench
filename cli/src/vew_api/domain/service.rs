use std::collections::HashMap;

use super::error::VewApiError;
use super::model::{HttpMethod, Operation, OperationParameter, ParameterLocation, ServiceCatalog};

/// Extracts the semantic CLI name from an OpenAPI operationId using the
/// path template to identify where path segments begin in the operationId.
///
/// Algorithm:
/// 1. Build a set of path segment tokens from the path template
///    (e.g. `/internal/projects/{id}/integrations` → `{"internal", "projects", "integrations"}`)
/// 2. Split operationId on `_`, drop the trailing HTTP method token
/// 3. Walk tokens right-to-left, dropping any that match a path segment or path parameter name
/// 4. Join remaining tokens with `-`
pub fn resolve_operation_name(operation_id: &str, path_template: &str) -> String {
    let http_methods = ["get", "post", "put", "delete", "patch", "head", "options"];

    // Strip everything from the first `__` onwards (path parameter encoding)
    let prefix = match operation_id.find("__") {
        Some(pos) => &operation_id[..pos],
        None => operation_id,
    };

    let mut tokens: Vec<&str> = prefix.split('_').filter(|s| !s.is_empty()).collect();

    // Drop trailing HTTP method
    if tokens
        .last()
        .is_some_and(|t| http_methods.contains(&t.to_lowercase().as_str()))
    {
        tokens.pop();
    }

    // Get the leading non-parameter path segments in order.
    // e.g. "/internal/projects/{id}/..." → ["internal", "projects"]
    //      "/projects/{id}/..." → ["projects"]
    let leading_path_segments: Vec<String> = path_template
        .split('/')
        .filter(|s| !s.is_empty())
        .take_while(|s| !s.starts_with('{'))
        .map(|s| s.replace('-', "_"))
        .collect();

    // Find where these leading path segments appear as a suffix of our tokens
    if !leading_path_segments.is_empty() && tokens.len() > leading_path_segments.len() {
        let suffix_start = tokens.len() - leading_path_segments.len();
        let suffix_matches = tokens[suffix_start..]
            .iter()
            .zip(leading_path_segments.iter())
            .all(|(t, p)| *t == p.as_str());
        if suffix_matches {
            tokens.truncate(suffix_start);
        }
    }

    tokens.join("-")
}

/// Converts an API parameter name (camelCase or snake_case) to a --kebab-case CLI flag.
pub fn resolve_parameter_name(api_name: &str) -> String {
    let mut result = String::with_capacity(api_name.len() + 4);
    result.push_str("--");
    for (i, ch) in api_name.chars().enumerate() {
        if ch.is_uppercase() && i > 0 {
            result.push('-');
            result.push(ch.to_ascii_lowercase());
        } else if ch == '_' {
            result.push('-');
        } else {
            result.push(ch.to_ascii_lowercase());
        }
    }
    result
}

/// Parses an OpenAPI 3.1 JSON spec into a ServiceCatalog.
pub fn parse_openapi_spec(
    spec: &serde_json::Value,
    bc_name: &str,
) -> Result<ServiceCatalog, VewApiError> {
    let paths = spec
        .get("paths")
        .and_then(|p| p.as_object())
        .ok_or_else(|| VewApiError::SpecParseError("missing 'paths' object".into()))?;

    let mut operations: Vec<Operation> = paths
        .iter()
        .filter(|(path, _)| !is_skipped_path(path))
        .filter_map(|(path, item)| Some((path, item.as_object()?)))
        .flat_map(|(path, path_obj)| {
            METHODS.iter().filter_map(move |(method_str, http_method)| {
                let method_value = path_obj.get(*method_str)?;
                build_operation(path, method_value, http_method.clone(), spec)
            })
        })
        .collect();

    for op in &mut operations {
        apply_parameter_defaults(op);
    }
    disambiguate_names(&mut operations);

    let info = spec.get("info");
    let summary = info
        .and_then(|i| i.get("summary"))
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());
    let description = info
        .and_then(|i| i.get("description"))
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());

    Ok(ServiceCatalog {
        bounded_context: bc_name.to_string(),
        summary,
        description,
        operations,
    })
}

const METHODS: &[(&str, HttpMethod)] = &[
    ("get", HttpMethod::Get),
    ("post", HttpMethod::Post),
    ("put", HttpMethod::Put),
    ("delete", HttpMethod::Delete),
    ("patch", HttpMethod::Patch),
];

fn is_skipped_path(path: &str) -> bool {
    path.contains("/_swagger") || path.contains("/openapi") || path.starts_with("/internal")
}

fn build_operation(
    path: &str,
    method_value: &serde_json::Value,
    http_method: HttpMethod,
    spec: &serde_json::Value,
) -> Option<Operation> {
    let operation_id = method_value.get("operationId")?.as_str()?;
    if operation_id.to_lowercase().contains("cors") {
        return None;
    }
    let as_string = |ptr: &str| {
        method_value
            .pointer(ptr)
            .and_then(|v| v.as_str())
            .map(|s| s.to_string())
    };
    let example = |ptr: &str| {
        method_value
            .pointer(ptr)
            .map(|s| generate_sample_json(s, spec))
    };
    Some(Operation {
        cli_name: resolve_operation_name(operation_id, path),
        operation_id: operation_id.to_string(),
        http_method,
        path_template: path.to_string(),
        summary: as_string("/summary"),
        description: as_string("/description"),
        parameters: extract_parameters(method_value),
        has_request_body: method_value.get("requestBody").is_some(),
        request_body_example: example("/requestBody/content/application~1json/schema"),
        response_example: example("/responses/200/content/application~1json/schema"),
    })
}

/// Generates a sample JSON value from an OpenAPI schema, resolving $ref pointers.
fn generate_sample_json(schema: &serde_json::Value, root: &serde_json::Value) -> serde_json::Value {
    // Resolve $ref
    if let Some(ref_path) = schema.get("$ref").and_then(|r| r.as_str()) {
        if let Some(resolved) = resolve_ref(ref_path, root) {
            return generate_sample_json(resolved, root);
        }
        return serde_json::Value::Null;
    }

    // Handle anyOf (pick first non-null)
    if let Some(any_of) = schema.get("anyOf").and_then(|a| a.as_array()) {
        for variant in any_of {
            if variant.get("type").and_then(|t| t.as_str()) == Some("null") {
                continue;
            }
            return generate_sample_json(variant, root);
        }
        return serde_json::Value::Null;
    }

    match schema.get("type").and_then(|t| t.as_str()) {
        Some("object") => {
            let mut obj = serde_json::Map::new();
            if let Some(props) = schema.get("properties").and_then(|p| p.as_object()) {
                for (key, prop_schema) in props {
                    obj.insert(key.clone(), generate_sample_json(prop_schema, root));
                }
            }
            serde_json::Value::Object(obj)
        }
        Some("array") => {
            let item = schema
                .get("items")
                .map(|i| generate_sample_json(i, root))
                .unwrap_or(serde_json::Value::Null);
            serde_json::json!([item])
        }
        Some("string") => serde_json::json!("string"),
        Some("integer") => serde_json::json!(0),
        Some("number") => serde_json::json!(0.0),
        Some("boolean") => serde_json::json!(false),
        _ => {
            // No type but has properties → treat as object
            if schema.get("properties").is_some() {
                let mut obj = serde_json::Map::new();
                if let Some(props) = schema.get("properties").and_then(|p| p.as_object()) {
                    for (key, prop_schema) in props {
                        obj.insert(key.clone(), generate_sample_json(prop_schema, root));
                    }
                }
                serde_json::Value::Object(obj)
            } else {
                serde_json::Value::Null
            }
        }
    }
}

fn resolve_ref<'a>(ref_path: &str, root: &'a serde_json::Value) -> Option<&'a serde_json::Value> {
    // "#/components/schemas/Foo" → ["components", "schemas", "Foo"]
    let parts: Vec<&str> = ref_path.trim_start_matches("#/").split('/').collect();
    let mut current = root;
    for part in parts {
        current = current.get(part)?;
    }
    Some(current)
}

fn extract_parameters(method_value: &serde_json::Value) -> Vec<OperationParameter> {
    let arr = match method_value.get("parameters").and_then(|p| p.as_array()) {
        Some(a) => a,
        None => return Vec::new(),
    };
    arr.iter()
        .filter_map(|p| {
            let name = p.get("name")?.as_str()?;
            let loc = match p.get("in")?.as_str()? {
                "path" => ParameterLocation::Path,
                "query" => ParameterLocation::Query,
                _ => return None,
            };
            let required = p.get("required").and_then(|r| r.as_bool()).unwrap_or(false);
            let schema_type = p
                .get("schema")
                .and_then(|s| s.get("type"))
                .and_then(|t| t.as_str())
                .unwrap_or("string")
                .to_string();
            Some(OperationParameter {
                cli_name: resolve_parameter_name(name),
                api_name: name.to_string(),
                location: loc,
                required,
                schema_type,
                default_value: None,
            })
        })
        .collect()
}

/// Applies product-level default values to parameters.
/// Kept out of OpenAPI parsing so the translation stays pure.
fn apply_parameter_defaults(op: &mut Operation) {
    for p in &mut op.parameters {
        if matches!(p.cli_name.as_str(), "--page-size" | "--page_size") {
            p.default_value = Some("10".to_string());
        }
    }
}

fn disambiguate_names(operations: &mut [Operation]) {
    let mut counts: HashMap<String, usize> = HashMap::new();
    for op in operations.iter() {
        *counts.entry(op.cli_name.clone()).or_insert(0) += 1;
    }
    for op in operations.iter_mut() {
        if counts.get(&op.cli_name).copied().unwrap_or(0) > 1 {
            op.cli_name = format!("{}-{}", op.cli_name, op.http_method.as_str().to_lowercase());
        }
    }
}

/// Parses raw CLI args `["--key", "value", ...]` into a HashMap.
/// Validates that all required parameters are present.
pub fn parse_raw_args(
    raw: &[String],
    operation: &Operation,
) -> Result<HashMap<String, String>, VewApiError> {
    let mut map = HashMap::new();
    let mut i = 0;
    while i < raw.len() {
        if raw[i].starts_with("--") {
            let key = raw[i].trim_start_matches("--").to_string();
            let value = raw.get(i + 1).cloned().unwrap_or_default();
            map.insert(key, value);
            i += 2;
        } else {
            i += 1;
        }
    }
    for param in &operation.parameters {
        let key = param.cli_name.trim_start_matches("--");
        if param.required && !map.contains_key(key) {
            return Err(VewApiError::MissingRequiredParam {
                param: param.cli_name.clone(),
                operation: operation.cli_name.clone(),
            });
        }
        if !map.contains_key(key)
            && let Some(default) = &param.default_value
        {
            map.insert(key.to_string(), default.clone());
        }
    }
    Ok(map)
}

/// Builds the full request URL by substituting path parameters and appending query parameters.
pub fn build_request_url(
    api_endpoint: &url::Url,
    bc_name: &str,
    operation: &Operation,
    args: &HashMap<String, String>,
) -> String {
    let base = api_endpoint.as_str().trim_end_matches('/');
    let mut path = operation.path_template.clone();
    for param in &operation.parameters {
        if param.location == ParameterLocation::Path {
            let key = param.cli_name.trim_start_matches("--");
            if let Some(value) = args.get(key) {
                path = path.replace(&format!("{{{}}}", param.api_name), value);
            }
        }
    }
    let query_params: Vec<String> = operation
        .parameters
        .iter()
        .filter(|p| p.location == ParameterLocation::Query)
        .filter_map(|p| {
            let key = p.cli_name.trim_start_matches("--");
            args.get(key).map(|v| format!("{}={}", p.api_name, v))
        })
        .collect();
    if query_params.is_empty() {
        format!("{}/{}{}", base, bc_name, path)
    } else {
        format!("{}/{}{}?{}", base, bc_name, path, query_params.join("&"))
    }
}

use super::help::{build_operation_detail, build_operations_list};

use super::commands::{ExecuteCommand, InitAllCaches, ListEnabledContexts};
use super::model::{
    BcRefreshOutcome, BoundedContext, BoundedContextInfo, BulkRefreshResult, CacheKey,
    EnabledContexts, ExecuteResult, InvocationResult,
};
use crate::debug_log;
use crate::shared::constants::SWAGGER_SUFFIX;
use crate::vew_api::ports::inbound::VewApiService;
use crate::vew_api::ports::outbound::{
    ApiInvoker, CatalogCache, EnabledContextsStore, SpecFetcher,
};

pub struct VewApiServiceImpl<
    F: SpecFetcher,
    C: CatalogCache,
    I: ApiInvoker,
    E: EnabledContextsStore,
> {
    fetcher: F,
    cache: C,
    invoker: I,
    enabled_store: E,
}

impl<F: SpecFetcher, C: CatalogCache, I: ApiInvoker, E: EnabledContextsStore>
    VewApiServiceImpl<F, C, I, E>
{
    pub fn new(fetcher: F, cache: C, invoker: I, enabled_store: E) -> Self {
        Self {
            fetcher,
            cache,
            invoker,
            enabled_store,
        }
    }

    fn resolve_catalog(
        &self,
        key: &CacheKey,
        cmd: &ExecuteCommand,
    ) -> Result<ServiceCatalog, VewApiError> {
        if !cmd.refresh_cache
            && let Some(catalog) = self.cache.get(key)?
        {
            debug_log!("cache hit for {}/{}", key.profile_name, key.bounded_context);
            return Ok(catalog);
        }

        let spec_url = format!(
            "{}/{}{}",
            cmd.api_endpoint.as_str().trim_end_matches('/'),
            cmd.bounded_context.as_str(),
            SWAGGER_SUFFIX,
        );

        debug_log!("fetching spec from {}", spec_url);
        let spec_json = self.fetcher.fetch(&spec_url, &cmd.access_token)?;
        let catalog = parse_openapi_spec(&spec_json, cmd.bounded_context.as_str())?;
        self.cache.put(key, &catalog)?;
        Ok(catalog)
    }
}

impl<F: SpecFetcher, C: CatalogCache, I: ApiInvoker, E: EnabledContextsStore> VewApiService
    for VewApiServiceImpl<F, C, I, E>
{
    fn execute(&self, cmd: ExecuteCommand) -> Result<ExecuteResult, VewApiError> {
        let bc_name = cmd.bounded_context.as_str();
        let cache_key = CacheKey {
            profile_name: cmd.profile_name.clone(),
            bounded_context: bc_name.to_string(),
        };
        let catalog = self.resolve_catalog(&cache_key, &cmd)?;

        let Some(op_name) = cmd.operation.as_deref() else {
            return Ok(ExecuteResult::Help(build_operations_list(&catalog)));
        };
        let operation = lookup_operation(&catalog, op_name, bc_name)?;

        if wants_help(&cmd, operation) {
            return Ok(ExecuteResult::Help(build_operation_detail(
                bc_name, operation,
            )));
        }

        let args = parse_raw_args(&cmd.raw_args, operation)?;
        self.invoke_operation(bc_name, operation, &cmd, &args)
    }

    fn init_all_caches(&self, cmd: InitAllCaches) -> Result<BulkRefreshResult, VewApiError> {
        use rayon::prelude::*;

        let outcomes: Vec<BcRefreshOutcome> = BoundedContext::all()
            .par_iter()
            .map(|bc| {
                let key = CacheKey {
                    profile_name: cmd.profile_name.clone(),
                    bounded_context: bc.as_str().to_string(),
                };
                let spec_url = format!(
                    "{}/{}{}",
                    cmd.api_endpoint.as_str().trim_end_matches('/'),
                    bc.as_str(),
                    SWAGGER_SUFFIX,
                );
                let result = self
                    .fetcher
                    .fetch(&spec_url, &cmd.access_token)
                    .and_then(|json| parse_openapi_spec(&json, bc.as_str()))
                    .and_then(|catalog| {
                        let count = catalog.operations.len();
                        self.cache.put(&key, &catalog)?;
                        Ok(count)
                    })
                    .map_err(|e| e.to_string());
                BcRefreshOutcome {
                    bounded_context: bc.clone(),
                    result,
                }
            })
            .collect();

        let result = BulkRefreshResult { outcomes };
        let enabled = EnabledContexts {
            profile_name: cmd.profile_name.clone(),
            contexts: result
                .enabled_contexts()
                .iter()
                .map(|bc| BoundedContextInfo {
                    name: bc.as_str().to_string(),
                    summary: None,
                })
                .collect(),
        };
        self.enabled_store.put(&enabled)?;
        Ok(result)
    }

    fn list_enabled_contexts(
        &self,
        cmd: ListEnabledContexts,
    ) -> Result<EnabledContexts, VewApiError> {
        let mut ec =
            self.enabled_store
                .get(&cmd.profile_name)?
                .ok_or(VewApiError::NoEnabledContexts {
                    profile: cmd.profile_name.clone(),
                })?;
        for ctx in &mut ec.contexts {
            if ctx.summary.is_none() {
                let key = CacheKey {
                    profile_name: cmd.profile_name.clone(),
                    bounded_context: ctx.name.clone(),
                };
                ctx.summary = self.cache.get(&key).ok().flatten().and_then(|c| c.summary);
            }
        }
        Ok(ec)
    }
}

fn lookup_operation<'a>(
    catalog: &'a ServiceCatalog,
    op_name: &str,
    bc_name: &str,
) -> Result<&'a Operation, VewApiError> {
    catalog
        .find_operation(op_name)
        .ok_or_else(|| VewApiError::UnknownOperation {
            name: op_name.to_string(),
            bc: bc_name.to_string(),
        })
}

/// Returns true when the user passed `--help` / `-h`, or omitted all args on
/// an operation that has required parameters.
fn wants_help(cmd: &ExecuteCommand, op: &Operation) -> bool {
    let explicit = cmd.raw_args.iter().any(|a| a == "--help" || a == "-h");
    let needs_prompt = cmd.raw_args.is_empty() && op.parameters.iter().any(|p| p.required);
    explicit || needs_prompt
}

impl<F: SpecFetcher, C: CatalogCache, I: ApiInvoker, E: EnabledContextsStore>
    VewApiServiceImpl<F, C, I, E>
{
    fn invoke_operation(
        &self,
        bc_name: &str,
        operation: &Operation,
        cmd: &ExecuteCommand,
        args: &HashMap<String, String>,
    ) -> Result<ExecuteResult, VewApiError> {
        let url = build_request_url(&cmd.api_endpoint, bc_name, operation, args);
        let body_val = args.get("body").and_then(|b| serde_json::from_str(b).ok());
        let (status, response_body) = self.invoker.invoke(
            operation.http_method.as_str(),
            &url,
            &cmd.access_token,
            body_val.as_ref(),
        )?;
        Ok(ExecuteResult::Response(InvocationResult {
            status_code: status,
            body: response_body,
        }))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::vew_api::domain::commands::ExecuteCommand;
    use crate::vew_api::domain::model::BoundedContext;
    use crate::vew_api::ports::outbound::{ApiInvoker, CatalogCache, SpecFetcher};
    use std::sync::Mutex;

    // --- Mock implementations ---

    struct MockFetcher {
        response: Mutex<Option<serde_json::Value>>,
        called: Mutex<bool>,
    }

    impl MockFetcher {
        fn new(response: serde_json::Value) -> Self {
            Self {
                response: Mutex::new(Some(response)),
                called: Mutex::new(false),
            }
        }
        fn was_called(&self) -> bool {
            *self.called.lock().unwrap()
        }
    }

    impl SpecFetcher for MockFetcher {
        fn fetch(&self, _url: &str, _token: &str) -> Result<serde_json::Value, VewApiError> {
            *self.called.lock().unwrap() = true;
            Ok(self.response.lock().unwrap().clone().unwrap())
        }
    }

    struct MockCache {
        catalog: Mutex<Option<ServiceCatalog>>,
        put_called: Mutex<bool>,
    }

    impl MockCache {
        fn with_catalog(catalog: ServiceCatalog) -> Self {
            Self {
                catalog: Mutex::new(Some(catalog)),
                put_called: Mutex::new(false),
            }
        }
        fn empty() -> Self {
            Self {
                catalog: Mutex::new(None),
                put_called: Mutex::new(false),
            }
        }
        fn was_put_called(&self) -> bool {
            *self.put_called.lock().unwrap()
        }
    }

    impl CatalogCache for MockCache {
        fn get(&self, _key: &CacheKey) -> Result<Option<ServiceCatalog>, VewApiError> {
            Ok(self.catalog.lock().unwrap().clone())
        }
        fn put(&self, _key: &CacheKey, _catalog: &ServiceCatalog) -> Result<(), VewApiError> {
            *self.put_called.lock().unwrap() = true;
            Ok(())
        }
    }

    struct MockInvoker {
        status: u16,
        body: serde_json::Value,
        called: Mutex<bool>,
    }

    impl MockInvoker {
        fn new(status: u16, body: serde_json::Value) -> Self {
            Self {
                status,
                body,
                called: Mutex::new(false),
            }
        }
        fn was_called(&self) -> bool {
            *self.called.lock().unwrap()
        }
    }

    impl ApiInvoker for MockInvoker {
        fn invoke(
            &self,
            _method: &str,
            _url: &str,
            _token: &str,
            _body: Option<&serde_json::Value>,
        ) -> Result<(u16, serde_json::Value), VewApiError> {
            *self.called.lock().unwrap() = true;
            Ok((self.status, self.body.clone()))
        }
    }

    struct MockEnabledStore {
        stored: Mutex<Option<EnabledContexts>>,
    }

    impl MockEnabledStore {
        fn new() -> Self {
            Self {
                stored: Mutex::new(None),
            }
        }
        fn with(enabled: EnabledContexts) -> Self {
            Self {
                stored: Mutex::new(Some(enabled)),
            }
        }
        fn stored(&self) -> Option<EnabledContexts> {
            self.stored.lock().unwrap().clone()
        }
    }

    impl EnabledContextsStore for MockEnabledStore {
        fn get(&self, _profile_name: &str) -> Result<Option<EnabledContexts>, VewApiError> {
            Ok(self.stored.lock().unwrap().clone())
        }
        fn put(&self, enabled: &EnabledContexts) -> Result<(), VewApiError> {
            *self.stored.lock().unwrap() = Some(enabled.clone());
            Ok(())
        }
    }

    fn sample_catalog() -> ServiceCatalog {
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

    fn sample_spec() -> serde_json::Value {
        make_spec(serde_json::json!({
            "/projects/{project_id}/integrations": {
                "get": {
                    "operationId": "get_integrations_projects__project_id__integrations_get",
                    "parameters": [
                        {"name": "project_id", "in": "path", "required": true, "schema": {"type": "string"}}
                    ]
                }
            }
        }))
    }

    fn sample_cmd(operation: Option<&str>, refresh: bool) -> ExecuteCommand {
        ExecuteCommand {
            bounded_context: BoundedContext::Pipelines,
            operation: operation.map(String::from),
            raw_args: vec!["--project-id".into(), "abc".into()],
            api_endpoint: url::Url::parse("https://api.example.com").unwrap(),
            access_token: "token".into(),
            refresh_cache: refresh,
            profile_name: "dev".into(),
        }
    }

    // --- VewApiServiceImpl::execute tests ---

    #[test]
    fn test_execute_no_operation_returns_help() {
        // Arrange
        let svc = VewApiServiceImpl::new(
            MockFetcher::new(sample_spec()),
            MockCache::with_catalog(sample_catalog()),
            MockInvoker::new(200, serde_json::json!({})),
            MockEnabledStore::new(),
        );
        let cmd = sample_cmd(None, false);

        // Act
        let result = svc.execute(cmd).unwrap();

        // Assert
        match result {
            ExecuteResult::Help(text) => {
                assert!(text.contains("get-integrations"));
                assert!(!text.contains("--project-id")); // compact list, no params
            }
            _ => panic!("expected Help"),
        }
    }

    #[test]
    fn test_execute_cache_hit_invokes_api() {
        // Arrange
        let fetcher = MockFetcher::new(sample_spec());
        let invoker = MockInvoker::new(200, serde_json::json!({"integrations": []}));
        let svc = VewApiServiceImpl::new(
            fetcher,
            MockCache::with_catalog(sample_catalog()),
            invoker,
            MockEnabledStore::new(),
        );
        let cmd = sample_cmd(Some("get-integrations"), false);

        // Act
        let result = svc.execute(cmd).unwrap();

        // Assert
        match result {
            ExecuteResult::Response(inv) => {
                assert_eq!(inv.status_code, 200);
                assert_eq!(inv.body["integrations"], serde_json::json!([]));
            }
            _ => panic!("expected Response"),
        }
        assert!(!svc.fetcher.was_called());
        assert!(svc.invoker.was_called());
    }

    #[test]
    fn test_execute_cache_miss_fetches_and_caches() {
        // Arrange
        let fetcher = MockFetcher::new(sample_spec());
        let cache = MockCache::empty();
        let invoker = MockInvoker::new(200, serde_json::json!({}));
        let svc = VewApiServiceImpl::new(fetcher, cache, invoker, MockEnabledStore::new());
        let cmd = sample_cmd(Some("get-integrations"), false);

        // Act
        let result = svc.execute(cmd);

        // Assert
        assert!(result.is_ok(), "execute failed: {:?}", result.err());
        assert!(svc.fetcher.was_called());
        assert!(svc.cache.was_put_called());
    }

    #[test]
    fn test_execute_refresh_cache_skips_cache_lookup() {
        // Arrange
        let fetcher = MockFetcher::new(sample_spec());
        let cache = MockCache::with_catalog(sample_catalog());
        let invoker = MockInvoker::new(200, serde_json::json!({}));
        let svc = VewApiServiceImpl::new(fetcher, cache, invoker, MockEnabledStore::new());
        let cmd = sample_cmd(Some("get-integrations"), true);

        // Act
        let result = svc.execute(cmd);

        // Assert
        assert!(result.is_ok());
        assert!(svc.fetcher.was_called());
        assert!(svc.cache.was_put_called());
    }

    #[test]
    fn test_execute_unknown_operation_returns_error() {
        // Arrange
        let svc = VewApiServiceImpl::new(
            MockFetcher::new(sample_spec()),
            MockCache::with_catalog(sample_catalog()),
            MockInvoker::new(200, serde_json::json!({})),
            MockEnabledStore::new(),
        );
        let cmd = sample_cmd(Some("nonexistent-op"), false);

        // Act
        let result = svc.execute(cmd);

        // Assert
        match result {
            Err(VewApiError::UnknownOperation { name, bc }) => {
                assert_eq!(name, "nonexistent-op");
                assert_eq!(bc, "pipelines");
            }
            other => panic!("expected UnknownOperation, got {:?}", other),
        }
    }

    #[test]
    fn test_execute_missing_required_param_shows_help() {
        // Arrange
        let svc = VewApiServiceImpl::new(
            MockFetcher::new(sample_spec()),
            MockCache::with_catalog(sample_catalog()),
            MockInvoker::new(200, serde_json::json!({})),
            MockEnabledStore::new(),
        );
        let mut cmd = sample_cmd(Some("get-integrations"), false);
        cmd.raw_args = vec![]; // no args provided

        // Act
        let result = svc.execute(cmd).unwrap();

        // Assert
        assert!(matches!(result, ExecuteResult::Help(_)));
    }

    #[test]
    fn test_execute_corrupted_cache_refetches() {
        // Arrange — empty cache simulates deserialization failure (returns None)
        let fetcher = MockFetcher::new(sample_spec());
        let cache = MockCache::empty();
        let invoker = MockInvoker::new(200, serde_json::json!({}));
        let svc = VewApiServiceImpl::new(fetcher, cache, invoker, MockEnabledStore::new());
        let cmd = sample_cmd(Some("get-integrations"), false);

        // Act
        let result = svc.execute(cmd);

        // Assert
        assert!(result.is_ok());
        assert!(svc.fetcher.was_called());
        assert!(svc.cache.was_put_called());
    }

    // --- resolve_operation_name tests ---

    fn make_spec(paths: serde_json::Value) -> serde_json::Value {
        serde_json::json!({ "openapi": "3.1.0", "paths": paths })
    }

    #[test]
    fn test_resolve_get_github_build_jobs() {
        // Act
        let result = resolve_operation_name(
            "get_github_build_jobs_projects__project_id__buildjobs_github_get",
            "/projects/{project_id}/buildjobs/github",
        );

        // Assert
        assert_eq!(result, "get-github-build-jobs");
    }

    #[test]
    fn test_resolve_create_integration() {
        // Act
        let result = resolve_operation_name(
            "create_integration_projects__project_id__integrations_post",
            "/projects/{project_id}/integrations",
        );

        // Assert
        assert_eq!(result, "create-integration");
    }

    #[test]
    fn test_resolve_update_integration() {
        // Act
        let result = resolve_operation_name(
            "update_integration_projects__project_id__integrations__integration_id__put",
            "/projects/{project_id}/integrations/{integration_id}",
        );

        // Assert
        assert_eq!(result, "update-integration");
    }

    #[test]
    fn test_resolve_retire_integration() {
        // Act
        let result = resolve_operation_name(
            "retire_integration_projects__project_id__integrations__integration_id__delete",
            "/projects/{project_id}/integrations/{integration_id}",
        );

        // Assert
        assert_eq!(result, "retire-integration");
    }

    #[test]
    fn test_resolve_get_integration_components_list_internal() {
        // Act
        let result = resolve_operation_name(
            "get_integration_components_list_internal_internal_projects__project_id__integrations__integration_id__component_lists_get",
            "/internal/projects/{project_id}/integrations/{integration_id}/component-lists",
        );

        // Assert
        assert_eq!(result, "get-integration-components-list-internal");
    }

    #[test]
    fn test_resolve_update_jenkins_configuration() {
        // Act
        let result = resolve_operation_name(
            "update_jenkins_configuration_projects__project_id__integrations__integration_id__jenkins_configuration_put",
            "/projects/{project_id}/integrations/{integration_id}/jenkins/configuration",
        );

        // Assert
        assert_eq!(result, "update-jenkins-configuration");
    }

    #[test]
    fn test_resolve_configure_github_application_key() {
        // Act
        let result = resolve_operation_name(
            "configure_github_application_key_projects__project_id__integrations__integration_id__github_application_key_put",
            "/projects/{project_id}/integrations/{integration_id}/github-application-key",
        );

        // Assert
        assert_eq!(result, "configure-github-application-key");
    }

    #[test]
    fn test_resolve_generate_github_application_secret() {
        // Act
        let result = resolve_operation_name(
            "generate_github_application_secret_projects__project_id__integrations__integration_id__github_application_secret_post",
            "/projects/{project_id}/integrations/{integration_id}/github-application-secret",
        );

        // Assert
        assert_eq!(result, "generate-github-application-secret");
    }

    // --- resolve_parameter_name tests ---

    #[test]
    fn test_resolve_param_project_id() {
        assert_eq!(resolve_parameter_name("projectId"), "--project-id");
    }

    #[test]
    fn test_resolve_param_integration_id() {
        assert_eq!(resolve_parameter_name("integrationId"), "--integration-id");
    }

    #[test]
    fn test_resolve_param_integration_type() {
        assert_eq!(
            resolve_parameter_name("integrationType"),
            "--integration-type"
        );
    }

    #[test]
    fn test_resolve_param_os_version() {
        assert_eq!(resolve_parameter_name("osVersion"), "--os-version");
    }

    #[test]
    fn test_resolve_param_status() {
        assert_eq!(resolve_parameter_name("status"), "--status");
    }

    #[test]
    fn test_resolve_param_snake_case_project_id() {
        assert_eq!(resolve_parameter_name("project_id"), "--project-id");
    }

    // --- parse_openapi_spec tests ---

    #[test]
    fn test_parse_spec_extracts_operations() {
        // Arrange
        let spec = make_spec(serde_json::json!({
            "/projects/{project_id}/integrations": {
                "get": {
                    "operationId": "get_integrations_projects__project_id__integrations_get",
                    "parameters": [
                        {"name": "project_id", "in": "path", "required": true, "schema": {"type": "string"}}
                    ]
                },
                "post": {
                    "operationId": "create_integration_projects__project_id__integrations_post",
                    "parameters": [
                        {"name": "project_id", "in": "path", "required": true, "schema": {"type": "string"}}
                    ],
                    "requestBody": {"content": {"application/json": {"schema": {}}}}
                }
            }
        }));

        // Act
        let catalog = parse_openapi_spec(&spec, "pipelines").unwrap();

        // Assert
        assert_eq!(catalog.operations.len(), 2);
        assert!(catalog.find_operation("get-integrations").is_some());
        assert!(catalog.find_operation("create-integration").is_some());
    }

    #[test]
    fn test_parse_spec_skips_swagger_and_cors() {
        // Arrange
        let spec = make_spec(serde_json::json!({
            "/_swagger": {
                "get": {"operationId": "get_swagger_spec"}
            },
            "/projects/{project_id}/integrations": {
                "get": {
                    "operationId": "get_integrations_projects__project_id__integrations_get",
                    "parameters": []
                },
                "options": {
                    "operationId": "get_integrations_cors_projects__project_id__integrations_options"
                }
            }
        }));

        // Act
        let catalog = parse_openapi_spec(&spec, "test").unwrap();

        // Assert
        assert_eq!(catalog.operations.len(), 1);
        assert_eq!(catalog.operations[0].cli_name, "get-integrations");
    }

    #[test]
    fn test_parse_spec_disambiguates_duplicate_names() {
        // Arrange — two different paths that resolve to the same CLI name
        let spec = make_spec(serde_json::json!({
            "/items": {
                "get": {
                    "operationId": "list_items_items_get",
                    "parameters": []
                }
            },
            "/items/{id}": {
                "get": {
                    "operationId": "list_items_items__id__get",
                    "parameters": []
                }
            }
        }));

        // Act
        let catalog = parse_openapi_spec(&spec, "test").unwrap();

        // Assert
        let names: Vec<&str> = catalog
            .operations
            .iter()
            .map(|o| o.cli_name.as_str())
            .collect();
        assert!(names.contains(&"list-items-get"));
        assert_eq!(catalog.operations.len(), 2);
    }

    #[test]
    fn test_parse_spec_extracts_path_and_query_params() {
        // Arrange
        let spec = make_spec(serde_json::json!({
            "/projects/{project_id}/runner-integrations": {
                "get": {
                    "operationId": "get_runner_integrations_projects__project_id__runner_integrations_get",
                    "parameters": [
                        {"name": "project_id", "in": "path", "required": true, "schema": {"type": "string"}},
                        {"name": "integrationType", "in": "query", "required": true, "schema": {"type": "string"}},
                        {"name": "status", "in": "query", "required": false, "schema": {"type": "string"}}
                    ]
                }
            }
        }));

        // Act
        let catalog = parse_openapi_spec(&spec, "pipelines").unwrap();
        let op = &catalog.operations[0];

        // Assert
        assert_eq!(op.parameters.len(), 3);
        let path_param = op
            .parameters
            .iter()
            .find(|p| p.api_name == "project_id")
            .unwrap();
        assert_eq!(path_param.location, ParameterLocation::Path);
        assert!(path_param.required);
        let query_param = op
            .parameters
            .iter()
            .find(|p| p.api_name == "status")
            .unwrap();
        assert_eq!(query_param.location, ParameterLocation::Query);
        assert!(!query_param.required);
    }

    #[test]
    fn test_parse_spec_detects_request_body() {
        // Arrange
        let spec = make_spec(serde_json::json!({
            "/items": {
                "get": {
                    "operationId": "list_items_items_get",
                    "parameters": []
                },
                "post": {
                    "operationId": "create_item_items_post",
                    "parameters": [],
                    "requestBody": {"content": {"application/json": {"schema": {}}}}
                }
            }
        }));

        // Act
        let catalog = parse_openapi_spec(&spec, "test").unwrap();

        // Assert
        let get_op = catalog.find_operation("list-items").unwrap();
        assert!(!get_op.has_request_body);
        let post_op = catalog.find_operation("create-item").unwrap();
        assert!(post_op.has_request_body);
    }

    #[test]
    fn test_parse_spec_skips_operations_without_operation_id() {
        // Arrange
        let spec = make_spec(serde_json::json!({
            "/items": {
                "get": {
                    "summary": "no operationId here"
                },
                "post": {
                    "operationId": "create_item_items_post",
                    "parameters": []
                }
            }
        }));

        // Act
        let catalog = parse_openapi_spec(&spec, "test").unwrap();

        // Assert
        assert_eq!(catalog.operations.len(), 1);
        assert_eq!(catalog.operations[0].cli_name, "create-item");
    }

    // --- parse_raw_args tests ---

    fn make_operation(params: Vec<OperationParameter>) -> Operation {
        Operation {
            cli_name: "test-op".to_string(),
            operation_id: "test_op".to_string(),
            http_method: HttpMethod::Get,
            path_template: "/test/{project_id}".to_string(),
            summary: None,
            description: None,
            parameters: params,
            has_request_body: false,
            request_body_example: None,
            response_example: None,
        }
    }

    #[test]
    fn test_parse_raw_args_happy_path() {
        // Arrange
        let op = make_operation(vec![
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
        ]);
        let raw: Vec<String> = vec!["--project-id", "abc", "--status", "CREATED"]
            .into_iter()
            .map(String::from)
            .collect();

        // Act
        let result = parse_raw_args(&raw, &op).unwrap();

        // Assert
        assert_eq!(result.get("project-id").unwrap(), "abc");
        assert_eq!(result.get("status").unwrap(), "CREATED");
    }

    #[test]
    fn test_parse_raw_args_missing_required_param() {
        // Arrange
        let op = make_operation(vec![OperationParameter {
            cli_name: "--project-id".into(),
            api_name: "project_id".into(),
            location: ParameterLocation::Path,
            required: true,
            schema_type: "string".into(),
            default_value: None,
        }]);
        let raw: Vec<String> = vec![];

        // Act
        let result = parse_raw_args(&raw, &op);

        // Assert
        assert!(matches!(
            result,
            Err(VewApiError::MissingRequiredParam { .. })
        ));
    }

    #[test]
    fn test_parse_raw_args_optional_param_omitted() {
        // Arrange
        let op = make_operation(vec![OperationParameter {
            cli_name: "--status".into(),
            api_name: "status".into(),
            location: ParameterLocation::Query,
            required: false,
            schema_type: "string".into(),
            default_value: None,
        }]);
        let raw: Vec<String> = vec![];

        // Act
        let result = parse_raw_args(&raw, &op);

        // Assert
        assert!(result.is_ok());
        assert!(result.unwrap().is_empty());
    }

    // --- build_request_url tests ---

    #[test]
    fn test_build_request_url_substitutes_path_params() {
        // Arrange
        let op = make_operation(vec![OperationParameter {
            cli_name: "--project-id".into(),
            api_name: "project_id".into(),
            location: ParameterLocation::Path,
            required: true,
            schema_type: "string".into(),
            default_value: None,
        }]);
        let endpoint = url::Url::parse("https://api.example.com").unwrap();
        let mut args = HashMap::new();
        args.insert("project-id".to_string(), "abc-123".to_string());

        // Act
        let url = build_request_url(&endpoint, "pipelines", &op, &args);

        // Assert
        assert_eq!(url, "https://api.example.com/pipelines/test/abc-123");
    }

    #[test]
    fn test_build_request_url_appends_query_params() {
        // Arrange
        let op = Operation {
            cli_name: "test-op".to_string(),
            operation_id: "test_op".to_string(),
            http_method: HttpMethod::Get,
            path_template: "/items".to_string(),
            summary: None,
            description: None,
            parameters: vec![
                OperationParameter {
                    cli_name: "--status".into(),
                    api_name: "status".into(),
                    location: ParameterLocation::Query,
                    required: false,
                    schema_type: "string".into(),
                    default_value: None,
                },
                OperationParameter {
                    cli_name: "--type".into(),
                    api_name: "type".into(),
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
        let endpoint = url::Url::parse("https://api.example.com").unwrap();
        let mut args = HashMap::new();
        args.insert("status".to_string(), "ACTIVE".to_string());
        args.insert("type".to_string(), "Jenkins".to_string());

        // Act
        let url = build_request_url(&endpoint, "test", &op, &args);

        // Assert
        assert!(url.starts_with("https://api.example.com/test/items?"));
        assert!(url.contains("status=ACTIVE"));
        assert!(url.contains("type=Jenkins"));
    }

    #[test]
    fn test_build_request_url_no_query_params() {
        // Arrange
        let op = Operation {
            cli_name: "test-op".to_string(),
            operation_id: "test_op".to_string(),
            http_method: HttpMethod::Get,
            path_template: "/items".to_string(),
            summary: None,
            description: None,
            parameters: vec![],
            has_request_body: false,
            request_body_example: None,
            response_example: None,
        };
        let endpoint = url::Url::parse("https://api.example.com").unwrap();
        let args = HashMap::new();

        // Act
        let url = build_request_url(&endpoint, "test", &op, &args);

        // Assert
        assert_eq!(url, "https://api.example.com/test/items");
        assert!(!url.contains('?'));
    }

    // --- new feature tests ---

    #[test]
    fn test_parse_spec_skips_internal_paths() {
        // Arrange
        let spec = make_spec(serde_json::json!({
            "/internal/projects/{project_id}/integrations": {
                "get": {
                    "operationId": "get_internal_integrations_internal_projects__project_id__integrations_get",
                    "parameters": []
                }
            },
            "/projects/{project_id}/integrations": {
                "get": {
                    "operationId": "get_integrations_projects__project_id__integrations_get",
                    "parameters": []
                }
            }
        }));

        // Act
        let catalog = parse_openapi_spec(&spec, "test").unwrap();

        // Assert
        assert_eq!(catalog.operations.len(), 1);
        assert_eq!(catalog.operations[0].cli_name, "get-integrations");
    }

    #[test]
    fn test_parse_spec_sets_page_size_default() {
        // Arrange
        let spec = make_spec(serde_json::json!({
            "/items": {
                "get": {
                    "operationId": "list_items_items_get",
                    "parameters": [
                        {"name": "pageSize", "in": "query", "required": false, "schema": {"type": "integer"}},
                        {"name": "status", "in": "query", "required": false, "schema": {"type": "string"}}
                    ]
                }
            }
        }));

        // Act
        let catalog = parse_openapi_spec(&spec, "test").unwrap();
        let op = &catalog.operations[0];

        // Assert
        let page_param = op
            .parameters
            .iter()
            .find(|p| p.api_name == "pageSize")
            .unwrap();
        assert_eq!(page_param.default_value, Some("10".to_string()));
        let status_param = op
            .parameters
            .iter()
            .find(|p| p.api_name == "status")
            .unwrap();
        assert_eq!(status_param.default_value, None);
    }

    #[test]
    fn test_parse_raw_args_applies_default_value() {
        // Arrange
        let op = Operation {
            cli_name: "list-items".into(),
            operation_id: "list_items".into(),
            http_method: HttpMethod::Get,
            path_template: "/items".into(),
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
        let raw: Vec<String> = vec![]; // user provides no args

        // Act
        let result = parse_raw_args(&raw, &op).unwrap();

        // Assert
        assert_eq!(result.get("page-size").unwrap(), "10");
    }

    #[test]
    fn test_parse_raw_args_user_overrides_default() {
        // Arrange
        let op = Operation {
            cli_name: "list-items".into(),
            operation_id: "list_items".into(),
            http_method: HttpMethod::Get,
            path_template: "/items".into(),
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
        let raw: Vec<String> = vec!["--page-size".into(), "50".into()];

        // Act
        let result = parse_raw_args(&raw, &op).unwrap();

        // Assert
        assert_eq!(result.get("page-size").unwrap(), "50");
    }

    #[test]
    fn test_parse_spec_extracts_request_and_response_examples() {
        // Arrange
        let spec = serde_json::json!({
            "openapi": "3.1.0",
            "paths": {
                "/items": {
                    "post": {
                        "operationId": "create_item_items_post",
                        "parameters": [],
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": { "$ref": "#/components/schemas/CreateItemRequest" }
                                }
                            }
                        },
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": { "$ref": "#/components/schemas/CreateItemResponse" }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "components": {
                "schemas": {
                    "CreateItemRequest": {
                        "type": "object",
                        "properties": {
                            "name": { "type": "string" },
                            "count": { "type": "integer" }
                        }
                    },
                    "CreateItemResponse": {
                        "type": "object",
                        "properties": {
                            "id": { "type": "string" },
                            "success": { "type": "boolean" }
                        }
                    }
                }
            }
        });

        // Act
        let catalog = parse_openapi_spec(&spec, "test").unwrap();
        let op = &catalog.operations[0];

        // Assert
        let req = op.request_body_example.as_ref().unwrap();
        assert_eq!(req["name"], "string");
        assert_eq!(req["count"], 0);
        let resp = op.response_example.as_ref().unwrap();
        assert_eq!(resp["id"], "string");
        assert_eq!(resp["success"], false);
    }

    #[test]
    fn test_execute_with_help_flag_returns_operation_detail() {
        // Arrange
        let svc = VewApiServiceImpl::new(
            MockFetcher::new(sample_spec()),
            MockCache::with_catalog(sample_catalog()),
            MockInvoker::new(200, serde_json::json!({})),
            MockEnabledStore::new(),
        );
        let mut cmd = sample_cmd(Some("get-integrations"), false);
        cmd.raw_args = vec!["--help".into()];

        // Act
        let result = svc.execute(cmd).unwrap();

        // Assert
        match result {
            ExecuteResult::Help(text) => {
                assert!(text.contains("--project-id"));
                assert!(text.contains("(required)"));
            }
            _ => panic!("expected Help"),
        }
    }

    #[test]
    fn test_execute_with_required_params_and_no_args_returns_detail() {
        // Arrange
        let svc = VewApiServiceImpl::new(
            MockFetcher::new(sample_spec()),
            MockCache::with_catalog(sample_catalog()),
            MockInvoker::new(200, serde_json::json!({})),
            MockEnabledStore::new(),
        );
        let mut cmd = sample_cmd(Some("get-integrations"), false);
        cmd.raw_args = vec![]; // no args, but operation has required params

        // Act
        let result = svc.execute(cmd).unwrap();

        // Assert
        match result {
            ExecuteResult::Help(text) => {
                assert!(text.contains("--project-id"));
            }
            _ => panic!("expected Help with operation detail"),
        }
    }

    // --- init_all_caches / list_enabled_contexts tests ---

    /// A fetcher that returns a minimal valid spec for any URL,
    /// unless the URL contains a BC name in the `fail_bcs` set.
    struct InitMockFetcher {
        fail_bcs: Vec<String>,
    }

    impl InitMockFetcher {
        fn all_succeed() -> Self {
            Self { fail_bcs: vec![] }
        }
        fn failing(fail_bcs: Vec<&str>) -> Self {
            Self {
                fail_bcs: fail_bcs.into_iter().map(String::from).collect(),
            }
        }
    }

    impl SpecFetcher for InitMockFetcher {
        fn fetch(&self, url: &str, _token: &str) -> Result<serde_json::Value, VewApiError> {
            for bc in &self.fail_bcs {
                if url.contains(bc.as_str()) {
                    return Err(VewApiError::SpecFetchError {
                        url: url.to_string(),
                        reason: "HTTP 404".to_string(),
                    });
                }
            }
            Ok(make_spec(serde_json::json!({
                "/items": {
                    "get": {
                        "operationId": "list_items_items_get",
                        "parameters": []
                    }
                }
            })))
        }
    }

    /// A cache that tracks how many puts were called.
    struct InitMockCache {
        put_count: Mutex<usize>,
    }

    impl InitMockCache {
        fn new() -> Self {
            Self {
                put_count: Mutex::new(0),
            }
        }
        fn _put_count(&self) -> usize {
            *self.put_count.lock().unwrap()
        }
    }

    impl CatalogCache for InitMockCache {
        fn get(&self, _key: &CacheKey) -> Result<Option<ServiceCatalog>, VewApiError> {
            Ok(None)
        }
        fn put(&self, _key: &CacheKey, _catalog: &ServiceCatalog) -> Result<(), VewApiError> {
            *self.put_count.lock().unwrap() += 1;
            Ok(())
        }
    }

    fn init_cmd() -> InitAllCaches {
        InitAllCaches {
            api_endpoint: url::Url::parse("https://api.example.com").unwrap(),
            access_token: "token".into(),
            profile_name: "dev".into(),
        }
    }

    #[test]
    fn test_init_all_caches_attempts_all_bcs() {
        // Arrange
        let svc = VewApiServiceImpl::new(
            InitMockFetcher::all_succeed(),
            InitMockCache::new(),
            MockInvoker::new(200, serde_json::json!({})),
            MockEnabledStore::new(),
        );

        // Act
        let result = svc.init_all_caches(init_cmd()).unwrap();

        // Assert
        assert_eq!(result.outcomes.len(), BoundedContext::all().len());
        assert!(result.outcomes.iter().all(|o| o.result.is_ok()));
    }

    #[test]
    fn test_init_all_caches_partial_failure() {
        // Arrange
        let svc = VewApiServiceImpl::new(
            InitMockFetcher::failing(vec!["test-generation", "pricing"]),
            InitMockCache::new(),
            MockInvoker::new(200, serde_json::json!({})),
            MockEnabledStore::new(),
        );

        // Act
        let result = svc.init_all_caches(init_cmd()).unwrap();

        // Assert
        let failed: Vec<_> = result
            .outcomes
            .iter()
            .filter(|o| o.result.is_err())
            .collect();
        assert_eq!(failed.len(), 2);

        let succeeded: Vec<_> = result
            .outcomes
            .iter()
            .filter(|o| o.result.is_ok())
            .collect();
        assert_eq!(succeeded.len(), BoundedContext::all().len() - 2);
    }

    #[test]
    fn test_init_all_caches_persists_enabled_contexts() {
        // Arrange
        let _enabled_store = MockEnabledStore::new();
        let svc = VewApiServiceImpl::new(
            InitMockFetcher::failing(vec!["test-generation"]),
            InitMockCache::new(),
            MockInvoker::new(200, serde_json::json!({})),
            MockEnabledStore::new(),
        );

        // Act
        let result = svc.init_all_caches(init_cmd()).unwrap();

        // Assert
        let stored = svc.enabled_store.stored().unwrap();
        assert_eq!(stored.profile_name, "dev");
        assert!(!stored.contexts.iter().any(|c| c.name == "test-generation"));
        assert_eq!(stored.contexts.len(), result.enabled_contexts().len());
    }

    #[test]
    fn test_init_all_caches_cache_error_captured() {
        // Arrange — a cache that fails on put
        struct FailingCache;
        impl CatalogCache for FailingCache {
            fn get(&self, _key: &CacheKey) -> Result<Option<ServiceCatalog>, VewApiError> {
                Ok(None)
            }
            fn put(&self, _key: &CacheKey, _catalog: &ServiceCatalog) -> Result<(), VewApiError> {
                Err(VewApiError::CacheError("disk full".into()))
            }
        }

        let svc = VewApiServiceImpl::new(
            InitMockFetcher::all_succeed(),
            FailingCache,
            MockInvoker::new(200, serde_json::json!({})),
            MockEnabledStore::new(),
        );

        // Act
        let result = svc.init_all_caches(init_cmd()).unwrap();

        // Assert — all outcomes are Err because cache.put fails
        assert!(result.outcomes.iter().all(|o| o.result.is_err()));
    }

    #[test]
    fn test_list_enabled_contexts_returns_stored() {
        // Arrange
        let enabled = EnabledContexts {
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
            ],
        };
        let svc = VewApiServiceImpl::new(
            MockFetcher::new(serde_json::json!({})),
            MockCache::empty(),
            MockInvoker::new(200, serde_json::json!({})),
            MockEnabledStore::with(enabled.clone()),
        );

        // Act
        let result = svc
            .list_enabled_contexts(ListEnabledContexts {
                profile_name: "dev".into(),
            })
            .unwrap();

        // Assert
        assert_eq!(result, enabled);
    }

    #[test]
    fn test_list_enabled_contexts_returns_error_when_none() {
        // Arrange
        let svc = VewApiServiceImpl::new(
            MockFetcher::new(serde_json::json!({})),
            MockCache::empty(),
            MockInvoker::new(200, serde_json::json!({})),
            MockEnabledStore::new(),
        );

        // Act
        let result = svc.list_enabled_contexts(ListEnabledContexts {
            profile_name: "dev".into(),
        });

        // Assert
        assert!(matches!(result, Err(VewApiError::NoEnabledContexts { .. })));
    }
}
