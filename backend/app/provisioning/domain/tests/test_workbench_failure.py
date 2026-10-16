import assertpy
import pytest

from app.provisioning.domain.model import product_status
from app.provisioning.domain.model.workbench_failure import (
    FailedOperation,
    FailureCode,
    classify_reason,
    describe_failure,
    is_gpu_instance_type,
)


@pytest.mark.parametrize(
    "reason,code",
    [
        # Reasons as the hub records them for a launch and a start.
        ("InsufficientCapacityInAllAvailabilityZones", FailureCode.Capacity),
        ("Insufficient instance capacity error", FailureCode.Capacity),
        (
            "Insufficient instance capacity error: We currently do not have sufficient g6.xlarge capacity in the "
            "Availability Zone you requested (eu-north-1a).",
            FailureCode.Capacity,
        ),
        ("Server.InsufficientInstanceCapacity: Insufficient capacity.", FailureCode.Capacity),
        ("INSUFFICIENT_CLUSTER_CAPACITY", FailureCode.Capacity),
        (
            "You have requested more vCPU capacity than your current vCPU limit of 0 allows for the instance bucket "
            "that the specified instance type belongs to (Error Code: VcpuLimitExceeded)",
            FailureCode.Quota,
        ),
        ("InstanceLimitExceeded: Your quota allows for 0 more running instance(s).", FailureCode.Quota),
        (
            "Unsupported: Your requested instance type (g6.xlarge) is not supported in your requested Availability "
            "Zone (eu-north-1c).",
            FailureCode.UnsupportedInAz,
        ),
        (
            "User: arn:aws:sts::1:assumed-role/x is not authorized to perform: ec2:RunInstances with an explicit deny",
            FailureCode.Permissions,
        ),
        ("UnauthorizedOperation: You are not authorized to perform this operation.", FailureCode.Permissions),
        ("Missing IP address in the output.", FailureCode.Template),
        ("Parameter validation failed: Invalid type for parameter", FailureCode.Template),
        ("Something nobody has seen before", FailureCode.Unknown),
        (None, FailureCode.Unknown),
    ],
)
def test_classify_reason(reason, code):
    assertpy.assert_that(classify_reason(reason)).is_equal_to(code)


@pytest.mark.parametrize(
    "instance_type,gpu",
    [
        ("g6.xlarge", True),
        ("g6e.2xlarge", True),
        ("g4dn.xlarge", True),
        ("p5.48xlarge", True),
        ("m7i.xlarge", False),
        ("c8g.metal-24xl", False),
        (None, False),
    ],
)
def test_is_gpu_instance_type(instance_type, gpu):
    assertpy.assert_that(is_gpu_instance_type(instance_type)).is_equal_to(gpu)


def test_a_failed_launch_is_described_with_its_code_and_instance_type():
    failure = describe_failure(
        status=product_status.ProductStatus.ProvisioningError,
        status_reason="InsufficientCapacityInAllAvailabilityZones",
        failed_operation="LAUNCH",
        instance_type="g6.xlarge",
    )

    assertpy.assert_that(failure.model_dump()).is_equal_to(
        {"code": FailureCode.Capacity, "operation": FailedOperation.Launch, "instanceType": "g6.xlarge", "gpu": True}
    )


def test_an_older_failed_launch_without_an_operation_is_a_launch_when_capacity():
    failure = describe_failure(
        status=product_status.ProductStatus.ProvisioningError,
        status_reason="InsufficientCapacityInAllAvailabilityZones",
    )

    assertpy.assert_that(failure.operation).is_equal_to(FailedOperation.Launch)


def test_a_provisioning_error_without_a_reason_is_unknown():
    failure = describe_failure(status=product_status.ProductStatus.ProvisioningError, status_reason=None)

    assertpy.assert_that(failure.code).is_equal_to(FailureCode.Unknown)
    assertpy.assert_that(failure.operation).is_none()


def test_a_failed_start_is_described():
    failure = describe_failure(
        status=product_status.ProductStatus.Stopped,
        status_reason="VcpuLimitExceeded: You have requested more vCPU capacity than your current vCPU limit",
        failed_operation="START",
        instance_type="m7i.xlarge",
    )

    assertpy.assert_that(failure.code).is_equal_to(FailureCode.Quota)
    assertpy.assert_that(failure.operation).is_equal_to(FailedOperation.Start)
    assertpy.assert_that(failure.gpu).is_false()


def test_an_older_stopped_record_with_a_capacity_reason_is_a_failed_start():
    # A STOPPED record written before failedOperation existed.
    failure = describe_failure(
        status=product_status.ProductStatus.Stopped, status_reason="Insufficient instance capacity error"
    )

    assertpy.assert_that(failure.code).is_equal_to(FailureCode.Capacity)
    assertpy.assert_that(failure.operation).is_equal_to(FailedOperation.Start)


@pytest.mark.parametrize(
    "status,reason,operation",
    [
        # An idle stop's reason on a stopped workbench isn't a failure.
        (product_status.ProductStatus.Stopped, "Idle for 120 minutes with nobody connected", None),
        (product_status.ProductStatus.Stopped, None, None),
        (product_status.ProductStatus.Running, "Insufficient instance capacity error", "START"),
        (product_status.ProductStatus.Starting, None, None),
    ],
)
def test_no_failure(status, reason, operation):
    assertpy.assert_that(describe_failure(status=status, status_reason=reason, failed_operation=operation)).is_none()
