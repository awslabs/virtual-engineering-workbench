import warnings
from typing import List, Optional

import boto3

from app.shared.api import parameter_service


class SSMApi(parameter_service.ParameterService):
    """Secondary adapter for the AWS SSM API."""

    def __init__(
        self,
        region: str,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        session_token: Optional[str] = None,
        session=None,
    ) -> None:
        warnings.warn("Use app/shared/adapters/boto/aws_parameter_service.py instead.", DeprecationWarning)

        self._client = (
            session.client(
                "ssm",
                region_name=region,
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                aws_session_token=session_token,
            )
            if session
            else boto3.client(
                "ssm",
                region_name=region,
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                aws_session_token=session_token,
            )
        )

    def get_parameter_value(self, parameter_name: str) -> str:
        """Returns a parameter as a string value."""

        param = self._client.get_parameter(Name=parameter_name)

        return str(param["Parameter"]["Value"])

    def get_list_parameter_value(self, parameter_name: str) -> List[str]:
        """Returns a parameter as a list of strings."""

        param = self._client.get_parameter(Name=parameter_name)

        return str(param["Parameter"]["Value"]).split(",")

    def create_string_parameter(self, parameter_name: str, parameter_value: str, is_overwrite: bool = False) -> None:
        """Creates a string parameter."""

        self._client.put_parameter(Name=parameter_name, Value=parameter_value, Type="String", Overwrite=is_overwrite)
