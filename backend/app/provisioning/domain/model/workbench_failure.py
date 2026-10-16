"""Why a workbench failed to launch or start, for its owner.

VEW records the raw AWS reason in statusReason. This turns it into a small, stable set of codes the
portal explains in plain words; admins also see the raw reason. Classification is by the reason's text
(CloudFormation stack events and EC2 errors carry the EC2 error code or its message).
"""

import re
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field

from app.provisioning.domain.model import product_status


class FailureCode(StrEnum):
    Capacity = "CAPACITY"
    Quota = "QUOTA"
    UnsupportedInAz = "UNSUPPORTED_IN_AZ"
    Permissions = "PERMISSIONS"
    Template = "TEMPLATE"
    Unknown = "UNKNOWN"


class FailedOperation(StrEnum):
    Launch = "LAUNCH"
    Start = "START"
    Update = "UPDATE"
    Remove = "REMOVE"


class WorkbenchFailure(BaseModel):
    code: FailureCode = Field(..., title="Code")
    operation: Optional[FailedOperation] = Field(None, title="Operation")
    instanceType: Optional[str] = Field(None, title="InstanceType")
    gpu: bool = Field(False, title="Gpu")


# Checked in this order: a quota message can also mention capacity ("more vCPU capacity than your
# current vCPU limit"), so quota goes first.
_PATTERNS: list[tuple[FailureCode, re.Pattern]] = [
    (
        FailureCode.Quota,
        re.compile(
            r"VcpuLimitExceeded|InstanceLimitExceeded|vCPU limit|MaxSpotInstanceCountExceeded|"
            r"service quota|LimitExceeded",
            re.IGNORECASE,
        ),
    ),
    (
        FailureCode.Capacity,
        re.compile(
            r"InsufficientInstanceCapacity|InsufficientCapacity|InsufficientClusterCapacity|"
            r"insufficient (instance )?capacity|INSUFFICIENT_\w*CAPACITY|do not have sufficient .* capacity",
            re.IGNORECASE,
        ),
    ),
    (
        FailureCode.UnsupportedInAz,
        re.compile(
            r"\bUnsupported\b|not supported in (your|the) requested Availability Zone|"
            r"instance type .* is not supported",
            re.IGNORECASE,
        ),
    ),
    (
        FailureCode.Permissions,
        re.compile(
            r"AccessDenied|UnauthorizedOperation|not authorized to perform|explicit deny|" r"is not authorized",
            re.IGNORECASE,
        ),
    ),
    (
        FailureCode.Template,
        re.compile(
            r"ValidationError|Parameter validation failed|Template (format )?error|Missing .* in the output|"
            r"Exceeded attempts to wait|InvalidParameter",
            re.IGNORECASE,
        ),
    ),
]

_FAILED_STATUSES = {product_status.ProductStatus.ProvisioningError}
START_FAILURE_STATUSES = {product_status.ProductStatus.Stopped, product_status.ProductStatus.InstanceError}


def classify_reason(reason: Optional[str]) -> FailureCode:
    """The failure class of a raw AWS reason."""
    for code, pattern in _PATTERNS:
        if reason and pattern.search(reason):
            return code
    return FailureCode.Unknown


def is_gpu_instance_type(instance_type: Optional[str]) -> bool:
    """G and P families carry GPUs (g4dn, g5, g6, g6e, p4d, p5, ...)."""
    match = re.match(r"^([a-z]+)\d", (instance_type or "").lower())
    return bool(match) and match.group(1) in {"g", "p"}


def describe_failure(
    status: Optional[str],
    status_reason: Optional[str],
    failed_operation: Optional[str] = None,
    instance_type: Optional[str] = None,
) -> Optional[WorkbenchFailure]:
    """The failure to show for a workbench, or None when it hasn't failed.

    PROVISIONING_ERROR always has failed (launch, update or removal). A stopped workbench has failed
    only when its last start did (failed_operation START), or when an older record's reason is a
    capacity or quota error from a start; other reasons on a stopped workbench (an idle stop) aren't
    failures.
    """
    operation = FailedOperation(failed_operation) if failed_operation in FailedOperation.__members__.values() else None
    code = classify_reason(status_reason)

    if status in _FAILED_STATUSES:
        if operation is None and code in (FailureCode.Capacity, FailureCode.Quota, FailureCode.UnsupportedInAz):
            operation = FailedOperation.Launch
    elif status in START_FAILURE_STATUSES:
        if operation != FailedOperation.Start:
            if not status_reason or code not in (FailureCode.Capacity, FailureCode.Quota):
                return None
            operation = FailedOperation.Start
    else:
        return None

    return WorkbenchFailure(
        code=code,
        operation=operation,
        instanceType=instance_type,
        gpu=is_gpu_instance_type(instance_type),
    )
