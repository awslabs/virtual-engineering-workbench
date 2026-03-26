from typing import Callable, Optional, Protocol

import boto3
from aws_lambda_powertools import logging
from mypy_boto3_sts import client as sts_client
from pydantic.main import BaseModel

from app.shared.adapters.exceptions.adapter_exception import AdapterException
from app.shared.logging import boto_logger

type ProviderType[ReturnType] = Callable[[BotoProviderOptions], ReturnType]

CREDENTIALS_CONTEXT_KEY = "boto_provider_credentials"


class SupportsContextManager(Protocol):
    context: dict

    def append_context(self, **additional_context): ...


class BotoProviderOptions:
    def __init__(
        self,
        aws_account_id: Optional[str] = None,
        aws_region: Optional[str] = None,
        aws_role_name: Optional[str] = None,
        aws_session_name: Optional[str] = None,
    ):
        self.aws_account_id = aws_account_id
        self.aws_region = aws_region
        self.aws_role_name = aws_role_name
        self.aws_session_name = aws_session_name


class _BotoParameters(BaseModel):
    """
    This class is used to pass parameters to boto3 calls
    """

    region_name: str | None
    aws_access_key_id: str | None
    aws_secret_access_key: str | None
    aws_session_token: str | None


class BotoProvider:
    def __init__(
        self,
        ctx: SupportsContextManager,
        logger: logging.Logger,
        default_options: BotoProviderOptions = BotoProviderOptions(),
    ):
        self._default_options = default_options
        self._ctx = ctx
        self._persistent_cache = {}
        self._logger = logger
        self._session = boto_logger.loggable_session(boto3.session.Session(), logger)
        self._sts_client: sts_client.STSClient | None = None

    def _sts_provider(self):
        if self._sts_client is None:
            self._sts_client = self._session.client("sts", region_name=self._default_options.aws_region)
        return self._sts_client

    def _key(self, resource_type: str, options: BotoProviderOptions):
        aws_account_id = options.aws_account_id or self._default_options.aws_account_id
        aws_region = options.aws_region or self._default_options.aws_region
        aws_role_name = options.aws_role_name or self._default_options.aws_role_name
        aws_session_name = options.aws_session_name or self._default_options.aws_session_name

        return f"{resource_type}#{aws_account_id}#{aws_region}#{aws_role_name}#{aws_session_name}"

    def _temp_credential_key(self, aws_account_id: str, aws_role_name: str, aws_session_name: str):
        return f"creds#{aws_account_id}#{aws_role_name}#{aws_session_name}"

    def _prepare_parameters(self, options: BotoProviderOptions) -> _BotoParameters:
        aws_account_id = options.aws_account_id or self._default_options.aws_account_id
        aws_region = options.aws_region or self._default_options.aws_region
        aws_role_name = options.aws_role_name or self._default_options.aws_role_name
        aws_session_name = options.aws_session_name or self._default_options.aws_session_name

        parameters = _BotoParameters()
        parameters.region_name = aws_region

        if aws_account_id:
            if not aws_role_name or not aws_session_name:
                raise AdapterException(
                    "BotoProvider: Assuming role requires full set of parameters: aws_role_name, aws_session_name"
                )

            if not self._ctx.context.get(CREDENTIALS_CONTEXT_KEY, None):
                self._ctx.append_context(**{CREDENTIALS_CONTEXT_KEY: {}})

            key = self._temp_credential_key(
                aws_account_id=aws_account_id,
                aws_role_name=aws_role_name,
                aws_session_name=aws_session_name,
            )

            if key not in self._ctx.context.get(CREDENTIALS_CONTEXT_KEY):

                assumed_role_object = self._sts_provider().assume_role(
                    RoleArn=f"arn:aws:iam::{aws_account_id}:role/{aws_role_name}",
                    RoleSessionName=aws_session_name,
                    Tags=[
                        {"Key": "UserId", "Value": str(aws_session_name)},
                    ],
                    TransitiveTagKeys=[
                        "UserId",
                    ],
                )

                credentials = assumed_role_object["Credentials"]

                parameters.aws_access_key_id = credentials["AccessKeyId"]
                parameters.aws_secret_access_key = credentials["SecretAccessKey"]
                parameters.aws_session_token = credentials["SessionToken"]
                self._ctx.context.get(CREDENTIALS_CONTEXT_KEY)[key] = parameters

            return self._ctx.context.get(CREDENTIALS_CONTEXT_KEY).get(key)

        return parameters

    def _is_persistent_client(self, options: BotoProviderOptions) -> bool:
        aws_account_id = options.aws_account_id or self._default_options.aws_account_id
        aws_role_name = options.aws_role_name or self._default_options.aws_role_name
        aws_session_name = options.aws_session_name or self._default_options.aws_session_name

        return not (aws_account_id or aws_role_name or aws_session_name)

    def temporary_credentials(self) -> ProviderType[_BotoParameters]:
        def _provider(options: Optional[BotoProviderOptions]) -> _BotoParameters:
            _options = options or BotoProviderOptions()
            return self._prepare_parameters(_options)

        return _provider

    def client[ReturnType](self, client_name: str) -> ProviderType[ReturnType]:
        def _provider(options: Optional[BotoProviderOptions]) -> ReturnType:
            _options = options or BotoProviderOptions()

            if self._is_persistent_client(_options):
                cache = self._persistent_cache
            else:
                if not self._ctx.context.get("boto_provider_clients", None):
                    self._ctx.append_context(boto_provider_clients={})
                cache = self._ctx.context["boto_provider_clients"]

            key = self._key(f"client/{client_name}", _options)
            if key in cache:
                return cache[key]

            parameters = self._prepare_parameters(_options)
            cache[key] = self._session.client(client_name, **parameters.dict())
            return cache[key]

        return _provider

    def resource[ReturnType](self, client_name: str) -> ProviderType[ReturnType]:
        def _provider(options: Optional[BotoProviderOptions]) -> ReturnType:
            _options = options or BotoProviderOptions()

            if self._is_persistent_client(_options):
                cache = self._persistent_cache
            else:
                if not self._ctx.context.get("boto_provider_clients", None):
                    self._ctx.append_context(boto_provider_clients={})
                cache = self._ctx.context["boto_provider_clients"]

            key = self._key(f"resource/{client_name}", _options)
            if key in cache:
                return cache[key]

            parameters = self._prepare_parameters(_options)
            cache[key] = self._session.resource(client_name, **parameters.dict())
            return cache[key]

        return _provider
