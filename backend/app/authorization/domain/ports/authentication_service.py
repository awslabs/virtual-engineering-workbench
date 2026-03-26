from abc import ABC, abstractmethod

import jwt


class AuthenticationService(ABC):
    @abstractmethod
    def get_signing_key_from_jwt(self, auth_token_jwt: str) -> tuple[bool, jwt.api_jwk.PyJWK | None]: ...

    @abstractmethod
    def get_user_info(self, auth_token: str) -> dict: ...
