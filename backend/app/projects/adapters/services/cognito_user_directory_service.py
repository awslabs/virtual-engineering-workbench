import logging
from typing import TYPE_CHECKING, Optional

from app.projects.domain.ports import user_directory_service

if TYPE_CHECKING:
    from mypy_boto3_cognito_idp import CognitoIdentityProviderClient

_USER_TID_ATTRIBUTE = "custom:user_tid"
_EMAIL_ATTRIBUTE = "email"


class CognitoUserDirectoryService(user_directory_service.UserDirectoryService):
    """Cognito-backed implementation of ``UserDirectoryService``.

    Looks up the ``email`` attribute for the Cognito user whose
    ``custom:user_tid`` matches the supplied tenant-internal user id.

    Cognito does not support server-side filtering on custom attributes via
    ``ListUsers --filter``, so this adapter paginates through the pool and
    matches client-side. That is acceptable for VEW's user-pool scale
    (hundreds to low thousands); if a deployment outgrows it, cache this
    lookup or maintain a reverse index on the ``user_tid``.

    Any failure degrades gracefully to ``None``: a missing email must never
    block user onboarding.
    """

    _PAGE_SIZE = 60  # Cognito ListUsers hard cap

    def __init__(
        self,
        cognito_client: "CognitoIdentityProviderClient",
        user_pool_id: str,
        logger: logging.Logger,
    ):
        self._client = cognito_client
        self._user_pool_id = user_pool_id
        self._logger = logger

    def get_user_email(self, user_tid: str) -> Optional[str]:
        if not user_tid:
            return None

        try:
            paginator = self._client.get_paginator("list_users")
            pages = paginator.paginate(
                UserPoolId=self._user_pool_id,
                AttributesToGet=[_USER_TID_ATTRIBUTE, _EMAIL_ATTRIBUTE],
                PaginationConfig={"PageSize": self._PAGE_SIZE},
            )

            for page in pages:
                for cognito_user in page.get("Users", []):
                    attributes = {attr["Name"]: attr.get("Value") for attr in cognito_user.get("Attributes", [])}

                    if attributes.get(_USER_TID_ATTRIBUTE) == user_tid:
                        return attributes.get(_EMAIL_ATTRIBUTE)

            self._logger.info(
                "No Cognito user found for user_tid=%s in pool=%s",
                user_tid,
                self._user_pool_id,
            )
            return None

        except Exception:
            # Lookup is best-effort — we don't want identity-provider issues
            # to block user onboarding. Log and return None so the caller
            # persists the assignment with userEmail=None, mirroring the
            # pre-existing behavior for assignments where the email simply
            # isn't known yet.
            self._logger.exception(
                "Failed to look up Cognito email for user_tid=%s in pool=%s",
                user_tid,
                self._user_pool_id,
            )
            return None
