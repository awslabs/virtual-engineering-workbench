from typing import Any, Optional, Tuple

import boto3
from mypy_boto3_cloudformation import client

from app.publishing.adapters.exceptions import adapter_exception
from app.publishing.domain.model import version
from app.publishing.domain.ports import iac_service
from app.shared.api import sts_api

SESSION_USER = "ProductPublishingProcess"


class CloudFormationService(iac_service.IACService):
    def __init__(self, admin_role: str, tools_aws_account_id: str, region: str, boto_session: Any = None):
        self._admin_role = admin_role
        self._tools_aws_account_id = tools_aws_account_id
        self._region = region
        self._boto_session = boto_session

    def validate_template(
        self, template_body: str = None, template_url: str = None
    ) -> Tuple[bool, Optional[list[version.VersionParameter]], Optional[str]]:
        """
            Validates a specified template.
            CloudFormation first checks if the template is valid JSON. If it isn't, CloudFormation checks if the template is valid YAML.
            If both these checks fail, CloudFormation returns a template validation error.
            You must pass template_url or template_body. If both are passed, only template_body is used.

        Args:
            template_body (str): Structure containing the template body with a minimum length of 1 byte and a maximum length of 51,200 bytes.
            template_url (str): Location of file containing the template body. The URL must point to a template (max size: 460,800 bytes)
                that is located in an Amazon S3 bucket or a Systems Manager document.

        Returns:
            bool: Returns True if template is valid, False otherwise
            Optional[list[version.VersionParameter]]: Returns the list of input parameters of the template
        """

        # Get STS temp credentials
        with sts_api.STSAPI(
            self._tools_aws_account_id, self._region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            # Create CloudFormation API instance cross-account
            cf_client: client.CloudFormationClient = (
                self._boto_session.client(
                    "cloudformation",
                    region_name=self._region,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    aws_session_token=session_token,
                )
                if self._boto_session
                else boto3.client(
                    "cloudformation",
                    region_name=self._region,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    aws_session_token=session_token,
                )
            )

            # Call the CloudFormation API
            try:
                if template_body:
                    response = cf_client.validate_template(TemplateBody=template_body)
                elif template_url:
                    response = cf_client.validate_template(TemplateURL=template_url)
                else:
                    raise adapter_exception.AdapterException("Template body or URL is required")
            except cf_client.exceptions.ClientError as e:
                error_code = e.response.get("Error", {}).get("Code")
                error_message = e.response.get("Error", {}).get("Message", "Unknown error")

                if error_code == "ValidationError":
                    return False, None, error_message
                raise

        parameters = []
        for param in response.get("Parameters", []):
            parameters.append(
                version.VersionParameter(
                    parameterKey=param["ParameterKey"],
                    defaultValue=param.get("DefaultValue", None),
                    description=param.get("Description", None),
                )
            )

        return True, parameters, None
