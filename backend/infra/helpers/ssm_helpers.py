from typing import Optional

from aws_cdk import aws_ssm


def try_get_value_from_lookup(scope, parameter_name: str, default_value: Optional[str] = None) -> Optional[str]:
    try:
        return aws_ssm.StringParameter.value_from_lookup(scope, parameter_name=parameter_name)
    except:
        return default_value
