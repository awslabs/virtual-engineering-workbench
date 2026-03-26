import json
import re


def sanitize_aws_resource_ids(text: str) -> str:

    patterns = [
        r"\b\d{12}\b",  # AWS Account IDs (12 digits)
        r"vpc-[0-9a-f]{8}(?:[0-9a-f]{9})?",  # VPC IDs
        r"subnet-[0-9a-f]{8}(?:[0-9a-f]{9})?",  # Subnet IDs
        r"arn:(?:aws|aws-cn|aws-us-gov):[\w-]+:[\w-]*:(?:\d{12})?:[\w-]+[:/][\w-]+(?:[:/][\w-]+)*",  # ARN
        r"ami-[0-9a-f]{8}(?:[0-9a-f]{9})?",  # AMI IDs
        r"i-[0-9a-f]{8}(?:[0-9a-f]{9})?",  # EC2 Instance IDs
        r"vol-[0-9a-f]{8}(?:[0-9a-f]{9})?",  # EBS Volume IDs
        r"sg-[0-9a-f]{8}(?:[0-9a-f]{9})?",  # Security Group IDs
        r"igw-[0-9a-f]{8}(?:[0-9a-f]{9})?",  # Internet Gateway IDs
        r"acl-[0-9a-f]{8}(?:[0-9a-f]{9})?",  # Network ACL IDs
        r"rtb-[0-9a-f]{8}(?:[0-9a-f]{9})?",  # Route Table IDs
    ]

    combined_pattern = "|".join(f"({pattern})" for pattern in patterns)

    return re.sub(combined_pattern, "[REDACTED]", text)


def try_parse_json(text: str) -> dict | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None
