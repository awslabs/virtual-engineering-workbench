from mypy_boto3_verifiedpermissions import client

from app.authorization.adapters.exceptions import adapter_exception
from app.authorization.domain.ports import authorization_service


class VerifiedPermissionsService(authorization_service.AuthorizationService):
    def __init__(
        self,
        verified_permissions_client: client.VerifiedPermissionsClient,
    ):
        self.__verified_permissions_client = verified_permissions_client

    def is_action_allowed(
        self,
        policy_store_id: str,
        principal: dict[str, str],
        action: dict[str, str],
        entities: dict,
        resource: dict[str, str] | None = None,
    ) -> bool:

        kwargs = {
            "policyStoreId": policy_store_id,
            "principal": principal,
            "action": action,
            "resource": resource,
            "entities": entities,
        }

        try:
            response = self.__verified_permissions_client.is_authorized(
                **{key: val for key, val in kwargs.items() if val is not None}
            )
            return response["decision"] == "ALLOW"
        except self.__verified_permissions_client.exceptions.ResourceNotFoundException:
            raise adapter_exception.AdapterException(f"Policy store {policy_store_id} not found")
        except Exception as e:
            raise adapter_exception.AdapterException(f"Error checking authorization: {str(e)}")
