"""the provisioned product API says why a workbench failed."""

import assertpy
import openapi_schema_validator

from app.provisioning.domain.model import product_status, provisioned_product, provisioning_parameter
from app.provisioning.entrypoints.api.model import api_model_mappers


def _workbench(status, status_reason=None, failed_operation=None, instance_type="g6.xlarge"):
    return provisioned_product.ProvisionedProduct(
        projectId="proj-123",
        provisionedProductId="pp-123",
        provisionedProductName="my name",
        provisionedProductType=provisioned_product.ProvisionedProductType.Workbench,
        userId="T0011AA",
        userDomains=["domain"],
        status=status,
        statusReason=status_reason,
        failedOperation=failed_operation,
        productId="prod-123",
        productName="GPU workbench",
        technologyId="tech-123",
        versionId="vers-123",
        versionName="1.0.3",
        awsAccountId="001234567890",
        accountId="acc-123",
        stage=provisioned_product.ProvisionedProductStage.PROD,
        region="eu-north-1",
        amiId="ami-123",
        scProductId="sc-prod-123",
        scProvisioningArtifactId="sc-pa-123",
        provisioningParameters=[
            provisioning_parameter.ProvisioningParameter(key="InstanceType", value=instance_type),
        ],
        createDate="2026-10-08T12:02:13+00:00",
        lastUpdateDate="2026-10-08T12:13:33+00:00",
        createdBy="T0011AA",
        lastUpdatedBy="T0011AA",
    )


def test_a_failed_launch_carries_its_failure():
    response = api_model_mappers.map_provisioned_product(
        _workbench(
            product_status.ProductStatus.ProvisioningError,
            status_reason="InsufficientCapacityInAllAvailabilityZones",
            failed_operation="LAUNCH",
        )
    )

    assertpy.assert_that(response.failure.model_dump()).is_equal_to(
        {"code": "CAPACITY", "operation": "LAUNCH", "instanceType": "g6.xlarge", "gpu": True}
    )


def test_an_owner_gets_the_failure_without_the_raw_reason():
    # The raw reason can carry the spoke account ID and role or KMS key ARNs.
    response = api_model_mappers.map_provisioned_product(
        _workbench(
            product_status.ProductStatus.ProvisioningError,
            status_reason="API: iam:PassRole User: arn:aws:sts::001234567890:assumed-role/x is not authorized",
            failed_operation="LAUNCH",
        )
    )

    assertpy.assert_that(response.failure.code).is_equal_to("PERMISSIONS")
    assertpy.assert_that(response.statusReason).is_none()


def test_an_admin_gets_the_raw_reason():
    response = api_model_mappers.map_provisioned_product(
        _workbench(
            product_status.ProductStatus.ProvisioningError,
            status_reason="InsufficientCapacityInAllAvailabilityZones",
            failed_operation="LAUNCH",
        ),
        include_status_reason=True,
    )

    assertpy.assert_that(response.failure.code).is_equal_to("CAPACITY")
    assertpy.assert_that(response.statusReason).is_equal_to("InsufficientCapacityInAllAvailabilityZones")
    assertpy.assert_that(response.model_dump()).does_not_contain_key("keyPairId")


def test_the_sensitive_path_keeps_the_raw_reason():
    response = api_model_mappers.map_provisioned_product(
        _workbench(
            product_status.ProductStatus.ProvisioningError,
            status_reason="InsufficientCapacityInAllAvailabilityZones",
            failed_operation="LAUNCH",
        ),
        include_sensitive=True,
    )

    assertpy.assert_that(response.failure.code).is_equal_to("CAPACITY")
    assertpy.assert_that(response.statusReason).is_equal_to("InsufficientCapacityInAllAvailabilityZones")


def test_a_running_workbench_has_no_failure():
    response = api_model_mappers.map_provisioned_product(_workbench(product_status.ProductStatus.Running))

    assertpy.assert_that(response.failure).is_none()


def test_the_failure_matches_the_api_schema(api_schema):
    response = api_model_mappers.map_provisioned_product(
        _workbench(
            product_status.ProductStatus.Stopped,
            status_reason="Insufficient instance capacity error",
            failed_operation="START",
            instance_type="m7i.xlarge",
        )
    )

    schema = {**api_schema["components"]["schemas"]["WorkbenchFailure"], "components": api_schema["components"]}
    openapi_schema_validator.validate(response.failure.model_dump(mode="json"), schema)
    assertpy.assert_that(response.failure.operation).is_equal_to("START")
    assertpy.assert_that(response.failure.gpu).is_false()
