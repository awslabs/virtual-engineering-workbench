import typing

import pydantic


class PathMethod(pydantic.BaseModel):
    method: str
    tags: list[str]
    auth: list
    headers: list[str]


class PathContext(pydantic.BaseModel):
    path: str
    methods: list[PathMethod]
    cors_methods: list[str] | None
    cors_headers: list[str] | None
    cors_method_error: list[str] | None
    cors_header_error: list[str] | None
    tag_name_errors: list[str] | None
    auth_errors: list[str] | None


class OpenAPIAnalyzer:
    def __init__(
        self,
        api_schema: dict,
        allowed_roles: set = set(
            ["PRODUCT_CONTRIBUTOR", "PLATFORM_USER", "BETA_USER", "POWER_USER", "PROGRAM_OWNER", "ADMIN", "ALL"]
        ),
    ) -> None:
        self._api_schema = api_schema
        self._path_contexts: list[PathContext] = []
        self._allowed_roles = allowed_roles
        self._no_auth_paths = []
        self._default_auth_scheme = None

    def analyze(self) -> typing.Self:
        if self._path_contexts:
            return self

        security_schemes = set(self._api_schema.get("components", {}).get("securitySchemes", {}).keys())
        self._default_auth_scheme = self._api_schema.get("security", [])
        default_auth_scheme_names = {a for aa in self._default_auth_scheme for a in aa.keys()}
        missing_schemes = default_auth_scheme_names - security_schemes
        if missing_schemes:
            raise ValueError(f"Default auth scheme refers to undefined security schemes: {missing_schemes}")

        for path, path_config in self._api_schema.get("paths").items():
            methods: list[PathMethod] = []
            all_headers = set()
            for method, method_config in path_config.items():
                headers = [
                    h.get("name").lower() for h in method_config.get("parameters", []) if h.get("in") == "header"
                ]
                methods.append(
                    PathMethod(
                        method=method,
                        tags=method_config.get("tags", []),
                        headers=headers,
                        auth=method_config.get("security", []),
                    )
                )

                all_headers = all_headers | set(headers)

            cors_methods = self._get_cors_param("method.response.header.Access-Control-Allow-Methods", path_config)
            cors_headers = self._get_cors_param("method.response.header.Access-Control-Allow-Headers", path_config)
            if cors_headers:
                cors_headers = [h.lower() for h in cors_headers]

            self._path_contexts.append(
                PathContext(
                    path=path,
                    methods=methods,
                    cors_methods=cors_methods,
                    cors_headers=cors_headers,
                    cors_method_error=[
                        m.method for m in methods if cors_methods is not None and m.method.upper() not in cors_methods
                    ],
                    cors_header_error=[h for h in all_headers if cors_headers is not None and h not in cors_headers],
                    tag_name_errors=[
                        f"{m.method} {set(m.tags) - self._allowed_roles}"
                        for m in methods
                        if set(m.tags) - self._allowed_roles
                    ],
                    auth_errors=[
                        m.method
                        for m in methods
                        if (
                            not self._default_auth_scheme
                            and (not m.auth or not {a for aa in m.auth for a in aa.keys()}.issubset(security_schemes))
                        )
                        and m.method != "options"
                        and path not in self._no_auth_paths
                    ],
                )
            )

        return self

    def allow_no_auth_paths(self, no_auth_paths: list[str]) -> typing.Self:
        self._no_auth_paths = no_auth_paths
        return self

    def _get_sanitized_cors_param(self, param: str) -> list[str]:
        return param.replace("'", "").split(",")

    def _get_cors_param(self, param_name: str, path_config: dict) -> list[str] | None:
        cosr_integration_config = (
            path_config.get("options", {})
            .get("x-amazon-apigateway-integration", {})
            .get("responses", {})
            .get("default", {})
            .get("responseParameters", {})
        )

        if not cosr_integration_config or param_name not in cosr_integration_config:
            return None

        return self._get_sanitized_cors_param(cosr_integration_config.get(param_name))

    @property
    def path_contexts(self):
        return self._path_contexts

    @staticmethod
    def from_dict(api_schema: dict, no_auth_paths: list[str] = []):
        return OpenAPIAnalyzer(api_schema=api_schema).allow_no_auth_paths(no_auth_paths=no_auth_paths).analyze()
