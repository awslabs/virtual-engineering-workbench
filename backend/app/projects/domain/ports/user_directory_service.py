import abc
from typing import Optional


class UserDirectoryService(abc.ABC):
    """Abstract port for looking up attributes of the identity provider's users.

    Decouples the domain from the concrete identity provider (Cognito today;
    another IdP later) so handlers can enrich domain entities — e.g. populate
    ``userEmail`` on a project assignment — without taking a dependency on
    a specific SDK.
    """

    @abc.abstractmethod
    def get_user_email(self, user_tid: str) -> Optional[str]:
        """Return the email of the user identified by ``user_tid``.

        ``user_tid`` is the tenant-internal identifier VEW stores on the IdP
        user record (``custom:user_tid`` in Cognito). The comparison is
        case-sensitive on the value as stored by the IdP.

        Returns ``None`` if the user is not found or if the lookup fails for
        any reason. Callers MUST treat ``None`` as "email unknown" rather
        than as a hard error: a missing email is recoverable (the UI will
        render a blank column) while an unavailable IdP should not block
        user onboarding.
        """
