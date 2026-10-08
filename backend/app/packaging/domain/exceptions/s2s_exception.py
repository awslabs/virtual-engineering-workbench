class S2SException(Exception):
    def __init__(self, detail: str, *, code: str, retryable: bool) -> None:
        super().__init__(detail)
        self.detail = detail
        self.code = code
        self.retryable = retryable


class ProjectAccessDenied(S2SException):
    def __init__(self) -> None:
        super().__init__(
            "The service client is not assigned to this project.", code="PROJECT_ACCESS_DENIED", retryable=False
        )


class ProjectAccessUnavailable(S2SException):
    def __init__(self) -> None:
        super().__init__("Project access could not be verified.", code="PROJECT_ACCESS_UNAVAILABLE", retryable=True)


class InsufficientScope(S2SException):
    def __init__(self, required_scope: str) -> None:
        super().__init__(
            f"The access token does not include the required scope: {required_scope}.",
            code="INSUFFICIENT_SCOPE",
            retryable=False,
        )
