import logging
import os
import re
import shlex
import subprocess
from itertools import chain
from typing import Any

from app.projects.adapters.exceptions import adapter_exception
from app.projects.domain.ports import iac_service
from app.shared.api import sts_api

SESSION_USER = "AccountOnboardingProcess"


class CDKIACService(iac_service.IACService):
    def __init__(
        self,
        toolkit_stack_name: str,
        toolkit_stack_qualifier: str,
        bootstrap_role: str,
        logger: logging.Logger,
        boto_session: Any = None,
        trusted_account: str = None,
        enable_lookup: bool = False,
    ) -> None:
        self.__toolkit_stack_name = toolkit_stack_name
        self.__toolkit_stack_qualifier = toolkit_stack_qualifier
        self.__bootstrap_role = bootstrap_role
        self.__boto_session = boto_session
        self.__trusted_account = trusted_account
        self.__enable_lookup = enable_lookup
        self.__logger = logger

    @staticmethod
    def _validate_cdk_variables(variables: dict[str, str]) -> None:
        """Validate CDK context variables for security."""
        for key, value in variables.items():
            if not re.match(r"^[a-zA-Z0-9_-]+$", key) or "--" in key:
                raise ValueError(f"Invalid variable key format: {key}")
            if len(value) > 2000:
                raise ValueError(f"Variable value too long for key: {key}")

    def deploy_iac(self, aws_account_id: str, region: str, variables: dict[str, str] = {}) -> None:  # noqa: C901
        self._validate_cdk_variables(variables)

        # Save original credentials to restore after CDK operations
        original_creds = {
            "AWS_ACCESS_KEY_ID": os.environ.get("AWS_ACCESS_KEY_ID"),
            "AWS_SECRET_ACCESS_KEY": os.environ.get("AWS_SECRET_ACCESS_KEY"),
            "AWS_SESSION_TOKEN": os.environ.get("AWS_SESSION_TOKEN"),
        }

        try:
            with sts_api.STSAPI(
                aws_account_id, region, self.__bootstrap_role, SESSION_USER, self.__boto_session
            ) as sts:
                (
                    access_key_id,
                    secret_access_key,
                    session_token,
                ) = sts.get_temp_creds()
                # Set environment variables for CDK
                os.environ["AWS_ACCESS_KEY_ID"] = access_key_id
                os.environ["AWS_SECRET_ACCESS_KEY"] = secret_access_key
                os.environ["AWS_SESSION_TOKEN"] = session_token

            # Setup the variables args
            variables_args = [f"{key}={value}" for key, value in variables.items()]

            for i in range(len(variables_args)):
                variables_args.insert(i * 2, "--context")

            # Run CDK bootstrap to bootstrap the account and region
            bootstrap_args = list(
                chain(
                    ["cdk", "bootstrap", f"aws://{aws_account_id}/{region}"],
                    variables_args,
                    ["--qualifier", self.__toolkit_stack_qualifier, "--toolkit-stack-name", self.__toolkit_stack_name],
                )
            )
            if self.__trusted_account:
                bootstrap_args.extend(["--trust", self.__trusted_account])
                if self.__enable_lookup:
                    bootstrap_args.extend(["--trust-for-lookup", self.__trusted_account])

            bootstrap_cmd = [shlex.quote(arg) for arg in bootstrap_args]

            self.__logger.debug(f"Running bootstrap command: {' '.join(bootstrap_cmd)}")

            try:
                subprocess.run(bootstrap_cmd, shell=False, text=True, capture_output=True, check=True, timeout=600)
                self.__logger.info("Bootstrap completed successfully")
            except subprocess.CalledProcessError as e:
                self.__logger.error(
                    {
                        "error": "BootstrapError",
                        "returncode": e.returncode,
                        "stderr": e.stderr.splitlines() if e.stderr else "",
                        "stdout": e.stdout.splitlines() if e.stdout else "",
                    }
                )
                raise adapter_exception.AdapterException(f"Bootstrap failed with code {e.returncode}: {e.stderr}")
            except subprocess.TimeoutExpired as e:
                self.__logger.error({"error": "BootstrapTimeout", "timeout": e.timeout})
                raise adapter_exception.AdapterException(f"Bootstrap timed out after {e.timeout} seconds")

            # Run CDK deploy to deploy the infrastructure
            deploy_args = list(
                chain(["cdk", "deploy"], variables_args, ["--require-approval", "never", "*", "--concurrency", "10"])
            )
            deploy_cmd = [shlex.quote(arg) for arg in deploy_args]

            try:
                subprocess.run(
                    deploy_cmd, shell=False, text=True, capture_output=True, check=True, timeout=1800  # 30 minutes
                )
                self.__logger.info("Deploy completed successfully")
            except subprocess.CalledProcessError as e:
                self.__logger.error(
                    {
                        "error": "DeployError",
                        "returncode": e.returncode,
                        "stderr": e.stderr.splitlines() if e.stderr else "",
                        "stdout": e.stdout.splitlines() if e.stdout else "",
                    }
                )
                raise adapter_exception.AdapterException(f"Deploy failed with code {e.returncode}: {e.stderr}")
            except subprocess.TimeoutExpired as e:
                self.__logger.error({"error": "DeployTimeout", "timeout": e.timeout})
                raise adapter_exception.AdapterException(f"Deploy timed out after {e.timeout} seconds")
        finally:
            # Restore original Lambda credentials
            for key, value in original_creds.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
