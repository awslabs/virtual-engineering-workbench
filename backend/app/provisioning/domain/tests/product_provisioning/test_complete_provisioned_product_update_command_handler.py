from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.provisioning.domain.command_handlers.product_provisioning import complete_update
from app.provisioning.domain.commands.product_provisioning import complete_provisioned_product_update
from app.provisioning.domain.events.product_provisioning import (
    provisioned_product_upgrade_failed,
    provisioned_product_upgraded,
)
from app.provisioning.domain.model import (
    instance_details,
    product_status,
    provisioned_product,
    provisioned_product_details,
    provisioned_product_output,
    provisioning_parameter,
)
from app.provisioning.domain.ports import versions_query_service
from app.provisioning.domain.read_models import version
from app.provisioning.domain.value_objects import provisioned_product_id_value_object


@pytest.fixture()
def mock_versions_query_service(get_test_version):
    v = get_test_version(
        parameters=[
            version.VersionParameter(
                parameterKey="SomeParam",
                defaultValue="some-default",
                parameterType="String",
            ),
            version.VersionParameter(
                parameterKey="SomeTechParam",
                defaultValue="/workbench/autosar/adaptive/ami-id/v1-3-x",
                parameterType="AWS::SSM::Parameter::Value<String>",
            ),
        ]
    )
    qs_mock = mock.create_autospec(spec=versions_query_service.VersionsQueryService)
    qs_mock.get_product_version_distributions.return_value = [v]
    qs_mock.get_by_provisioning_artifact_id.return_value = v
    return qs_mock


@freeze_time("2023-12-07")
def test_handle_when_successful_should_fetch_latest_parameters(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_instance_mgmt_srv,
    get_provisioned_product,
    mock_versions_query_service,
    mock_container_mgmt_srv,
):
    # ARRANGE
    command = complete_provisioned_product_update.CompleteProvisionedProductUpdateCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        sc_provisioned_product_id="sc-pp-123",
        status=product_status.ProductStatus.Updating,
        private_ip="192.168.1.1",
        public_ip="192.168.1.2",
        old_instance_id="i-01234567890abcdef",
    )
    mock_instance_mgmt_srv.get_instance_details.return_value = instance_details.InstanceDetails(
        State=instance_details.InstanceState(Name=product_status.EC2InstanceState.Stopped),
        PrivateIpAddress="192.168.2.1",
        PublicIpAddress="192.168.2.2",
    )

    # ACT
    complete_update.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_provisioned_products_qs,
        products_srv=mock_products_srv,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
        versions_qs=mock_versions_query_service,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_upgraded.ProvisionedProductUpgraded(
            provisionedProductId="pp-123",
            oldInstanceId="i-01234567890abcdef",
            instanceId="i-1234567890",
            awsAccountId="001234567890",
            region="us-east-1",
            projectId="proj-123",
            owner="T0011AA",
            privateIp="192.168.2.1",
            productType=provisioned_product.ProvisionedProductType.VirtualTarget,
            productName="Pied Piper",
        )
    )
    mock_unit_of_work.commit.assert_called_once()

    args, kwargs = mock_provisioned_product_repo.update_entity.call_args
    stored_entity: provisioned_product.ProvisionedProduct = kwargs.get("entity")

    assertpy.assert_that(stored_entity.outputs).contains_only(
        *[
            provisioned_product_output.ProvisionedProductOutput(
                outputKey="instance-id", outputValue="i-1234567890", description="description"
            ),
            provisioned_product_output.ProvisionedProductOutput(
                outputKey="privateIp", outputValue="192.168.1.1", description="description"
            ),
            provisioned_product_output.ProvisionedProductOutput(
                outputKey="SSHKeyPair",
                outputValue="/ec2/keypair/i-123",
                description="SSM Parameter containing the ssh key generated",
            ),
        ]
    )

    assertpy.assert_that(stored_entity.instanceId).is_equal_to("i-1234567890")
    assertpy.assert_that(stored_entity.privateIp).is_equal_to("192.168.2.1")
    assertpy.assert_that(stored_entity.publicIp).is_equal_to("192.168.2.2")
    assertpy.assert_that(stored_entity.sshKeyPath).is_equal_to("/ec2/keypair/i-123")
    assertpy.assert_that(stored_entity.status).is_equal_to(product_status.ProductStatus.Updating)


@freeze_time("2023-12-07")
def test_handle_when_successful_should_update_provisioning_parameters(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_instance_mgmt_srv,
    get_provisioned_product,
    mock_versions_query_service,
    mock_container_mgmt_srv,
):
    # ARRANGE
    provisioning_params = [
        provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
        provisioning_parameter.ProvisioningParameter(key="UserSecurityGroupId"),
    ]
    command = complete_provisioned_product_update.CompleteProvisionedProductUpdateCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        sc_provisioned_product_id="sc-pp-123",
        status=product_status.ProductStatus.Updating,
        new_provisioning_parameters=provisioning_params,
        provisioning_parameters=None,
        old_instance_id="i-01234567890abcdef",
    )

    # ACT
    complete_update.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_provisioned_products_qs,
        products_srv=mock_products_srv,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
        versions_qs=mock_versions_query_service,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_upgraded.ProvisionedProductUpgraded(
            provisionedProductId="pp-123",
            oldInstanceId="i-01234567890abcdef",
            instanceId="i-1234567890",
            awsAccountId="001234567890",
            region="us-east-1",
            projectId="proj-123",
            owner="T0011AA",
            privateIp="192.168.1.1",
            productType=provisioned_product.ProvisionedProductType.VirtualTarget,
            productName="Pied Piper",
        )
    )
    mock_unit_of_work.commit.assert_called_once()

    args, kwargs = mock_provisioned_product_repo.update_entity.call_args
    stored_entity: provisioned_product.ProvisionedProduct = kwargs.get("entity")

    assertpy.assert_that(stored_entity.provisioningParameters).contains_only(*provisioning_params)
    mock_products_srv.get_provisioned_product_details.assert_called_once_with(
        provisioned_product_id="sc-pp-123", aws_account_id="001234567890", region="us-east-1", user_id="T0011AA"
    )


def test_when_unsuccessful_should_fetch_state_and_publish_failed_event(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_instance_mgmt_srv,
    get_provisioned_product,
    mock_versions_query_service,
    mock_container_mgmt_srv,
):
    # ARRANGE
    command = complete_provisioned_product_update.CompleteProvisionedProductUpdateCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        sc_provisioned_product_id="sc-pp-123",
        status=product_status.ProductStatus.Updating,
        provisioning_parameters=None,
    )
    mock_products_srv.get_provisioned_product_details.side_effect = Exception("Test")

    # ACT
    complete_update.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_provisioned_products_qs,
        products_srv=mock_products_srv,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
        versions_qs=mock_versions_query_service,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_upgrade_failed.ProvisionedProductUpgradeFailed(provisionedProductId="pp-123")
    )
    mock_unit_of_work.commit.assert_called_once()

    args, kwargs = mock_provisioned_product_repo.update_entity.call_args
    stored_entity: provisioned_product.ProvisionedProduct = kwargs.get("entity")

    assertpy.assert_that(stored_entity.statusReason).is_equal_to("Test")
    assertpy.assert_that(stored_entity.status).is_equal_to(product_status.ProductStatus.ProvisioningError)


def test_when_no_new_version_was_published_during_upgrade_should_unmark_for_upgrade(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_instance_mgmt_srv,
    get_provisioned_product,
    mock_versions_query_service,
    get_test_version,
    mock_container_mgmt_srv,
):
    # ARRANGE
    actual_upgraded_version = get_test_version(version_id="vers-321", version_name="2.0.1")
    mock_versions_query_service.get_by_provisioning_artifact_id.return_value = actual_upgraded_version

    command = complete_provisioned_product_update.CompleteProvisionedProductUpdateCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        sc_provisioned_product_id="sc-pp-123",
        status=product_status.ProductStatus.Updating,
        upgrade_available=True,
        new_version_id="vers-321",
        new_version_name="2.0.1",
    )

    mock_products_srv.get_provisioned_product_details.return_value = (
        provisioned_product_details.ProvisionedProductDetails(
            Tags=[],
            Status=product_status.ServiceCatalogStatus.Available,
            Id="pp-123",
            ProvisioningArtifactId="sc-vers-123",
        )
    )

    # ACT
    complete_update.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_provisioned_products_qs,
        products_srv=mock_products_srv,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
        versions_qs=mock_versions_query_service,
    )

    # ASSERT
    args, kwargs = mock_provisioned_product_repo.update_entity.call_args
    stored_entity: provisioned_product.ProvisionedProduct = kwargs.get("entity")

    assertpy.assert_that(stored_entity.newVersionId).is_none()
    assertpy.assert_that(stored_entity.upgradeAvailable).is_false()
    assertpy.assert_that(stored_entity.newVersionName).is_none()
    assertpy.assert_that(stored_entity.versionName).is_equal_to("2.0.1")
    assertpy.assert_that(stored_entity.versionId).is_equal_to("vers-321")


def test_when_new_version_was_published_should_keep_marked_for_upgrade(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_instance_mgmt_srv,
    get_provisioned_product,
    mock_versions_query_service,
    get_test_version,
    mock_container_mgmt_srv,
):
    # ARRANGE
    actual_upgraded_version = get_test_version(version_id="vers-321", version_name="2.0.1")
    latest_upgrade_version = get_test_version(
        version_id="vers-456", version_name="3.0.1", sc_provisioning_artifact_id="sc-vers-321"
    )
    mock_versions_query_service.get_by_provisioning_artifact_id.return_value = actual_upgraded_version
    mock_versions_query_service.get_product_version_distributions.return_value = [latest_upgrade_version]

    command = complete_provisioned_product_update.CompleteProvisionedProductUpdateCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        sc_provisioned_product_id="sc-pp-123",
        status=product_status.ProductStatus.Updating,
        upgrade_available=True,
        new_version_id="vers-456",
        new_version_name="3.0.1",
    )

    mock_products_srv.get_provisioned_product_details.return_value = (
        provisioned_product_details.ProvisionedProductDetails(
            Tags=[],
            Status=product_status.ServiceCatalogStatus.Available,
            Id="pp-123",
            ProvisioningArtifactId="sc-vers-123",
        )
    )

    # ACT
    complete_update.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_provisioned_products_qs,
        products_srv=mock_products_srv,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
        versions_qs=mock_versions_query_service,
    )

    # ASSERT
    args, kwargs = mock_provisioned_product_repo.update_entity.call_args
    stored_entity: provisioned_product.ProvisionedProduct = kwargs.get("entity")

    assertpy.assert_that(stored_entity.newVersionId).is_equal_to("vers-456")
    assertpy.assert_that(stored_entity.upgradeAvailable).is_true()
    assertpy.assert_that(stored_entity.newVersionName).is_equal_to("3.0.1")
    assertpy.assert_that(stored_entity.versionName).is_equal_to("2.0.1")
    assertpy.assert_that(stored_entity.versionId).is_equal_to("vers-321")


@freeze_time("2023-12-07")
def test_handle_if_newer_version_sets_upgrade_newer_version(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_instance_mgmt_srv,
    get_provisioned_product,
    mock_versions_query_service,
    get_test_version,
    mock_container_mgmt_srv,
):
    # ARRANGE
    actual_upgraded_version = get_test_version(version_id="vers-321", version_name="2.0.1")
    product_version_distributions = [
        get_test_version(version_id="vers-456", version_name="3.0.1", sc_provisioning_artifact_id="sc-vers-321"),
        get_test_version(version_id="vers-457", version_name="3.4.1", sc_provisioning_artifact_id="sc-vers-322"),
    ]
    mock_versions_query_service.get_by_provisioning_artifact_id.return_value = actual_upgraded_version
    mock_versions_query_service.get_product_version_distributions.return_value = product_version_distributions

    command = complete_provisioned_product_update.CompleteProvisionedProductUpdateCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        sc_provisioned_product_id="sc-pp-123",
        status=product_status.ProductStatus.Updating,
        upgrade_available=True,
        new_version_id="vers-456",
        new_version_name="3.0.1",
    )

    mock_products_srv.get_provisioned_product_details.return_value = (
        provisioned_product_details.ProvisionedProductDetails(
            Tags=[],
            Status=product_status.ServiceCatalogStatus.Available,
            Id="pp-123",
            ProvisioningArtifactId="sc-vers-123",
        )
    )

    # ACT
    complete_update.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_provisioned_products_qs,
        products_srv=mock_products_srv,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
        versions_qs=mock_versions_query_service,
    )

    # ASSERT
    args, kwargs = mock_provisioned_product_repo.update_entity.call_args
    stored_entity: provisioned_product.ProvisionedProduct = kwargs.get("entity")

    assertpy.assert_that(stored_entity.newVersionId).is_equal_to("vers-457")
    assertpy.assert_that(stored_entity.upgradeAvailable).is_true()
    assertpy.assert_that(stored_entity.newVersionName).is_equal_to("3.4.1")
    assertpy.assert_that(stored_entity.versionName).is_equal_to("2.0.1")
    assertpy.assert_that(stored_entity.versionId).is_equal_to("vers-321")
    assertpy.assert_that(stored_entity.instanceRecommendationReason).is_none()
    assertpy.assert_that(stored_entity.recommendedInstanceType).is_none()
