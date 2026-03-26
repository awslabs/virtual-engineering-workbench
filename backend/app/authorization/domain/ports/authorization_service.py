from abc import ABC, abstractmethod


class AuthorizationService(ABC):
    @abstractmethod
    def is_action_allowed(
        self,
        policy_store_id: str,
        principal: dict[str, str],
        action: dict[str, str],
        entities: dict,
        resource: dict[str, str] | None = None,
    ) -> bool: ...
