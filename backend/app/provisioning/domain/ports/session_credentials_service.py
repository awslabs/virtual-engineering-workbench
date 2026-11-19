from abc import ABC, abstractmethod

from app.provisioning.domain.model import session_credentials


class SessionCredentialsService(ABC):
    @abstractmethod
    def get_session_credentials(
        self, aws_account_id: str, region: str, user_id: str, instance_id: str
    ) -> session_credentials.SessionCredentials | None:
        """Credentials that can only start a Session Manager session on the instance.

        None while the instance's SSM Agent is not connected.
        """
