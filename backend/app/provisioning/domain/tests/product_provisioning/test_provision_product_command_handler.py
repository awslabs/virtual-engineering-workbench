import ipaddress
from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.provisioning.domain.aggregates.internal import networking_helpers
from app.provisioning.domain.command_handlers.product_provisioning import provision_product
from app.provisioning.domain.commands.product_provisioning import provision_product_command
from app.provisioning.domain.events.product_provisioning import product_launch_failed, product_provisioning_started
from app.provisioning.domain.exceptions import domain_exception
from app.provisioning.domain.model import (
    connection_option,
    network_interface,
    network_route_table,
    network_subnet,
    product_status,
    provisioned_product,
    provisioning_parameter,
    user_profile,
)
from app.provisioning.domain.value_objects import ip_address_value_object, provisioned_product_id_value_object


@freeze_time("2023-12-06")
@pytest.mark.parametrize("authorize_user_ip_address_param_value", [True, False])
def test_provision_virtual_target_product_should_provision_catalog_product(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
    get_provisioned_product,
    default_subnet_selector,
    authorize_user_ip_address_param_value,
):
    # ARRANGE
    command = provision_product_command.ProvisionProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(key="UserSecurityGroupId", isTechnicalParameter=True),
            provisioning_parameter.ProvisioningParameter(key="InstanceType", value="r8g.metal-24xl"),
            provisioning_parameter.ProvisioningParameter(key="OwnerTID", value="T0011AA"),
        ]
    )

    # ACT
    provision_product.handle(
        command=command,
        publisher=mock_publisher,
        products_srv=mock_products_srv,
        virtual_targets_qs=mock_provisioned_products_qs,
        parameter_srv=mock_parameter_srv,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        logger=mock_logger,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        subnet_selector=default_subnet_selector,
        authorize_user_ip_address_param_value=authorize_user_ip_address_param_value,
        uow=mock_unit_of_work,
    )

    # ASSERT
    mock_products_srv.provision_product.assert_called_with(
        user_id="T0011AA",
        aws_account_id="001234567890",
        sc_product_id="sc-prod-123",
        sc_provisioning_artifact_id="sc-pa-123",
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(
                key="UserSecurityGroupId", value="sg-12345", isTechnicalParameter=True
            ),
            provisioning_parameter.ProvisioningParameter(key="InstanceType", value="r8g.metal-24xl"),
            provisioning_parameter.ProvisioningParameter(key="OwnerTID", value="T0011AA"),
        ],
        name="my name",
        region="us-east-1",
        tags=[
            {"Key": "UserTID", "Value": "T0011AA"},
            {"Key": "OwnerID", "Value": "T0011AA"},
            {"Key": "OwnerDomains", "Value": "domain"},
            {"Key": "vew:provisionedProduct:ownerDomains", "Value": "domain"},
            {"Key": "vew:provisionedProduct:productType", "Value": "VIRTUAL_TARGET"},
            {"Key": "vew:provisionedProduct:id", "Value": "pp-123"},
            {"Key": "vew:provisionedProduct:ownerId", "Value": "T0011AA"},
            {"Key": "vew:provisionedProduct:versionName", "Value": "1.0.0"},
            {"Key": "vew:product:name", "Value": "Pied Piper"},
            {"Key": "vew:product:versionName", "Value": "1.0.0"},
            {"Key": "vew:product:type", "Value": "VIRTUAL_TARGET"},
            {"Key": "vew:product:category", "Value": "BareMetal"},
        ],
    )
    mock_message_bus.publish.assert_called_once_with(
        product_provisioning_started.ProductProvisioningStarted(
            projectId="proj-123",
            provisionedProductId="pp-123",
        )
    )
    mock_unit_of_work.commit.assert_called_once()
    mock_provisioned_product_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        provisioned_product.ProvisionedProduct.construct(
            projectId="proj-123",
            provisionedProductId="pp-123",
            provisionedProductName=mock.ANY,
            provisionedProductType=provisioned_product.ProvisionedProductType.VirtualTarget,
            userId="T0011AA",
            userDomains=["domain"],
            status=product_status.ProductStatus.Provisioning,
            productId="prod-123",
            productName="Pied Piper",
            productDescription="Compression",
            technologyId="tech-123",
            versionId="vers-123",
            versionName="1.0.0",
            awsAccountId="001234567890",
            accountId="acc-123",
            instanceId="i-01234567890abcdef",
            stage=provisioned_product.ProvisionedProductStage.DEV,
            region="us-east-1",
            amiId="ami-123",
            scProductId="sc-prod-123",
            scProvisioningArtifactId="sc-pa-123",
            scProvisionedProductId="pp-123",
            provisioningParameters=[
                provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
                provisioning_parameter.ProvisioningParameter(
                    key="UserSecurityGroupId", value="sg-12345", isTechnicalParameter=True
                ),
                provisioning_parameter.ProvisioningParameter(key="InstanceType", value="r8g.metal-24xl"),
                provisioning_parameter.ProvisioningParameter(key="OwnerTID", value="T0011AA"),
            ],
            createDate="2023-12-05T00:00:00+00:00",
            lastUpdateDate="2023-12-06T00:00:00+00:00",
            createdBy="T0011AA",
            lastUpdatedBy="T0011AA",
        ),
    )
    mock_instance_mgmt_srv.create_user_security_group.assert_called_once_with(
        user_id="T0011AA",
        aws_account_id="001234567890",
        region="us-east-1",
        vpc_id="vpc-12345",
    )
    if authorize_user_ip_address_param_value:
        for option in connection_option.ConnectionOption.list():
            for rule in connection_option.CONNECTION_OPTION_TO_SECURITY_GROUP_RULES_MAP[option]:
                mock_instance_mgmt_srv.authorize_user_ip_address.assert_any_call(
                    user_id="T0011AA",
                    aws_account_id="001234567890",
                    region="us-east-1",
                    connection_option=option,
                    ip_address="127.0.0.1/32",
                    port=rule.from_port,
                    to_port=rule.to_port,
                    protocol=rule.protocol.value,
                    user_sg_id=None,  # We cannot mock get_user_security_group_id
                )
    else:
        mock_instance_mgmt_srv.authorize_user_ip_address.assert_not_called()


@freeze_time("2023-12-06")
def test_provision_product_when_product_has_subnet_id_parameter_should_fetch_private_subnet_id_with_tgw(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
    get_provisioned_product,
):
    # ARRANGE
    command = provision_product_command.ProvisionProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
    )

    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(
                key="SubnetId", isTechnicalParameter=True, parameterType="AWS::EC2::Subnet::Id"
            ),
        ],
    )

    # ACT
    provision_product.handle(
        command=command,
        publisher=mock_publisher,
        products_srv=mock_products_srv,
        virtual_targets_qs=mock_provisioned_products_qs,
        parameter_srv=mock_parameter_srv,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        logger=mock_logger,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        subnet_selector=networking_helpers.get_provisioning_subnet_selector("PrivateSubnetWithTransitGateway"),
        authorize_user_ip_address_param_value=True,
        uow=mock_unit_of_work,
    )

    # ASSERT
    mock_products_srv.provision_product.assert_called_with(
        user_id="T0011AA",
        aws_account_id="001234567890",
        sc_product_id="sc-prod-123",
        sc_provisioning_artifact_id="sc-pa-123",
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(
                key="SubnetId", value="s-prv", isTechnicalParameter=True, parameterType="AWS::EC2::Subnet::Id"
            ),
        ],
        name="my name-az-1",
        region="us-east-1",
        tags=[
            {"Key": "UserTID", "Value": "T0011AA"},
            {"Key": "OwnerID", "Value": "T0011AA"},
            {"Key": "OwnerDomains", "Value": "domain"},
            {"Key": "vew:provisionedProduct:ownerDomains", "Value": "domain"},
            {"Key": "vew:provisionedProduct:productType", "Value": "VIRTUAL_TARGET"},
            {"Key": "vew:provisionedProduct:id", "Value": "pp-123"},
            {"Key": "vew:provisionedProduct:ownerId", "Value": "T0011AA"},
            {"Key": "vew:provisionedProduct:versionName", "Value": "1.0.0"},
            {"Key": "vew:product:name", "Value": "Pied Piper"},
            {"Key": "vew:product:versionName", "Value": "1.0.0"},
            {"Key": "vew:product:type", "Value": "VIRTUAL_TARGET"},
            {"Key": "vew:product:category", "Value": None},
        ],
    )

    mock_unit_of_work.commit.assert_called_once()
    mock_provisioned_product_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        provisioned_product.ProvisionedProduct.construct(
            projectId="proj-123",
            provisionedProductId="pp-123",
            provisionedProductName=mock.ANY,
            provisionedProductType=provisioned_product.ProvisionedProductType.VirtualTarget,
            userId="T0011AA",
            userDomains=["domain"],
            status=product_status.ProductStatus.Provisioning,
            productId="prod-123",
            productName="Pied Piper",
            productDescription="Compression",
            technologyId="tech-123",
            versionId="vers-123",
            versionName="1.0.0",
            awsAccountId="001234567890",
            accountId="acc-123",
            instanceId="i-01234567890abcdef",
            stage=provisioned_product.ProvisionedProductStage.DEV,
            region="us-east-1",
            amiId="ami-123",
            scProductId="sc-prod-123",
            scProvisioningArtifactId="sc-pa-123",
            scProvisionedProductId="pp-123",
            provisioningParameters=[
                provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
                provisioning_parameter.ProvisioningParameter(
                    key="SubnetId", value="s-prv", isTechnicalParameter=True, parameterType="AWS::EC2::Subnet::Id"
                ),
            ],
            createDate="2023-12-05T00:00:00+00:00",
            lastUpdateDate="2023-12-06T00:00:00+00:00",
            createdBy="T0011AA",
            lastUpdatedBy="T0011AA",
            availabilityZonesTriggered=["az-1"],
        ),
    )
    mock_instance_mgmt_srv.describe_vpc_route_tables.assert_called_once_with(
        user_id="T0011AA", aws_account_id="001234567890", region="us-east-1", vpc_id="vpc-12345"
    )
    mock_instance_mgmt_srv.describe_vpc_subnets.assert_called_once_with(
        user_id="T0011AA", aws_account_id="001234567890", region="us-east-1", vpc_id="vpc-12345"
    )


@freeze_time("2023-12-06")
def test_provision_product_when_product_has_subnets_ids_parameter_should_fetch_private_subnets_ids_with_tgw(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
    get_provisioned_product,
    mock_subnet,
    mock_private_route_table,
):
    # ARRANGE
    command = provision_product_command.ProvisionProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
    )

    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(
                key="SubnetsIds", isTechnicalParameter=True, parameterType="List<AWS::EC2::Subnet::Id>"
            ),
        ],
    )

    mock_instance_mgmt_srv.describe_vpc_route_tables.return_value = [
        mock_private_route_table(
            associations=[
                network_route_table.NetworkRouteTableAssociation(
                    subnet_id="s-prv-1",
                ),
                network_route_table.NetworkRouteTableAssociation(
                    subnet_id="s-prv-2",
                ),
            ]
        )
    ]
    mock_instance_mgmt_srv.describe_vpc_subnets.return_value = [
        mock_subnet(subnet_id="s-prv-1", available_ip_address_count=100, availability_zone="az-1"),
        mock_subnet(subnet_id="s-prv-2", available_ip_address_count=80, availability_zone="az-2"),
    ]

    # ACT
    provision_product.handle(
        command=command,
        publisher=mock_publisher,
        products_srv=mock_products_srv,
        virtual_targets_qs=mock_provisioned_products_qs,
        parameter_srv=mock_parameter_srv,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        logger=mock_logger,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        subnet_selector=networking_helpers.get_provisioning_subnet_selector("PrivateSubnetWithTransitGateway"),
        authorize_user_ip_address_param_value=True,
        uow=mock_unit_of_work,
    )

    # ASSERT
    mock_products_srv.provision_product.assert_called_with(
        user_id="T0011AA",
        aws_account_id="001234567890",
        sc_product_id="sc-prod-123",
        sc_provisioning_artifact_id="sc-pa-123",
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(
                key="SubnetsIds",
                value="s-prv-1,s-prv-2",
                isTechnicalParameter=True,
                parameterType="List<AWS::EC2::Subnet::Id>",
            ),
        ],
        name="my name",
        region="us-east-1",
        tags=[
            {"Key": "UserTID", "Value": "T0011AA"},
            {"Key": "OwnerID", "Value": "T0011AA"},
            {"Key": "OwnerDomains", "Value": "domain"},
            {"Key": "vew:provisionedProduct:ownerDomains", "Value": "domain"},
            {"Key": "vew:provisionedProduct:productType", "Value": "VIRTUAL_TARGET"},
            {"Key": "vew:provisionedProduct:id", "Value": "pp-123"},
            {"Key": "vew:provisionedProduct:ownerId", "Value": "T0011AA"},
            {"Key": "vew:provisionedProduct:versionName", "Value": "1.0.0"},
            {"Key": "vew:product:name", "Value": "Pied Piper"},
            {"Key": "vew:product:versionName", "Value": "1.0.0"},
            {"Key": "vew:product:type", "Value": "VIRTUAL_TARGET"},
            {"Key": "vew:product:category", "Value": None},
        ],
    )

    mock_unit_of_work.commit.assert_called_once()
    mock_provisioned_product_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        provisioned_product.ProvisionedProduct.construct(
            projectId="proj-123",
            provisionedProductId="pp-123",
            provisionedProductName=mock.ANY,
            provisionedProductType=provisioned_product.ProvisionedProductType.VirtualTarget,
            userId="T0011AA",
            userDomains=["domain"],
            status=product_status.ProductStatus.Provisioning,
            productId="prod-123",
            productName="Pied Piper",
            productDescription="Compression",
            technologyId="tech-123",
            versionId="vers-123",
            versionName="1.0.0",
            awsAccountId="001234567890",
            accountId="acc-123",
            instanceId="i-01234567890abcdef",
            stage=provisioned_product.ProvisionedProductStage.DEV,
            region="us-east-1",
            amiId="ami-123",
            scProductId="sc-prod-123",
            scProvisioningArtifactId="sc-pa-123",
            scProvisionedProductId="pp-123",
            provisioningParameters=[
                provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
                provisioning_parameter.ProvisioningParameter(
                    key="SubnetsIds",
                    value="s-prv-1,s-prv-2",
                    isTechnicalParameter=True,
                    parameterType="List<AWS::EC2::Subnet::Id>",
                ),
            ],
            createDate="2023-12-05T00:00:00+00:00",
            lastUpdateDate="2023-12-06T00:00:00+00:00",
            createdBy="T0011AA",
            lastUpdatedBy="T0011AA",
        ),
    )
    mock_instance_mgmt_srv.describe_vpc_route_tables.assert_called_once_with(
        user_id="T0011AA", aws_account_id="001234567890", region="us-east-1", vpc_id="vpc-12345"
    )
    mock_instance_mgmt_srv.describe_vpc_subnets.assert_called_once_with(
        user_id="T0011AA", aws_account_id="001234567890", region="us-east-1", vpc_id="vpc-12345"
    )


@freeze_time("2023-12-06")
@pytest.mark.parametrize(
    "param_name,param_type,param_value",
    [("SubnetId", "AWS::EC2::Subnet::Id", "s-prv-2"), ("AZName", "AWS::EC2::AvailabilityZone::Name", "az-2")],
)
def test_provision_product_when_product_has_subnet_id_parameter_and_no_user_profile_az_should_fetch_subnet_with_most_ips(
    param_name,
    param_type,
    param_value,
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
    get_provisioned_product,
    mock_subnet,
    mock_private_route_table,
    mock_unit_of_work,
    mock_user_profile_repo,
):
    # ARRANGE
    command = provision_product_command.ProvisionProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
    )

    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(
                key=param_name, isTechnicalParameter=True, parameterType=param_type
            ),
        ],
    )
    mock_instance_mgmt_srv.describe_vpc_route_tables.return_value = [
        mock_private_route_table(
            associations=[
                network_route_table.NetworkRouteTableAssociation(
                    subnet_id="s-prv-1",
                ),
                network_route_table.NetworkRouteTableAssociation(
                    subnet_id="s-prv-2",
                ),
            ]
        )
    ]
    mock_instance_mgmt_srv.describe_vpc_subnets.return_value = [
        mock_subnet(subnet_id="s-prv-1", available_ip_address_count=100, availability_zone="az-1"),
        mock_subnet(subnet_id="s-prv-2", available_ip_address_count=120, availability_zone="az-2"),
    ]

    mock_user_profile_repo.get.return_value = None

    # ACT
    provision_product.handle(
        command=command,
        publisher=mock_publisher,
        products_srv=mock_products_srv,
        virtual_targets_qs=mock_provisioned_products_qs,
        parameter_srv=mock_parameter_srv,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        logger=mock_logger,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        subnet_selector=networking_helpers.get_provisioning_subnet_selector("PrivateSubnetWithTransitGateway"),
        authorize_user_ip_address_param_value=True,
        uow=mock_unit_of_work,
    )

    # ASSERT
    mock_products_srv.provision_product.assert_called_with(
        user_id="T0011AA",
        aws_account_id="001234567890",
        sc_product_id="sc-prod-123",
        sc_provisioning_artifact_id="sc-pa-123",
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(
                key="SomeParam", value="some-test-param-value", parameterType=None
            ),
            provisioning_parameter.ProvisioningParameter(
                key=param_name, value=param_value, isTechnicalParameter=True, parameterType=param_type
            ),
        ],
        name="my name-az-2",
        region="us-east-1",
        tags=[
            {"Key": "UserTID", "Value": "T0011AA"},
            {"Key": "OwnerID", "Value": "T0011AA"},
            {"Key": "OwnerDomains", "Value": "domain"},
            {"Key": "vew:provisionedProduct:ownerDomains", "Value": "domain"},
            {"Key": "vew:provisionedProduct:productType", "Value": "VIRTUAL_TARGET"},
            {"Key": "vew:provisionedProduct:id", "Value": "pp-123"},
            {"Key": "vew:provisionedProduct:ownerId", "Value": "T0011AA"},
            {"Key": "vew:provisionedProduct:versionName", "Value": "1.0.0"},
            {"Key": "vew:product:name", "Value": "Pied Piper"},
            {"Key": "vew:product:versionName", "Value": "1.0.0"},
            {"Key": "vew:product:type", "Value": "VIRTUAL_TARGET"},
            {"Key": "vew:product:category", "Value": None},
        ],
    )
    mock_user_profile_repo.add.assert_called_once_with(
        user_profile.UserProfile(
            userId="T0011AA",
            preferredRegion="us-east-1",
            preferredNetwork=None,
            preferredMaintenanceWindows=None,
            createDate="2023-12-06T00:00:00+00:00",
            lastUpdateDate="2023-12-06T00:00:00+00:00",
            persistentHomeDrives=None,
            preferredAvailabilityZone="az-2",
        )
    )


@freeze_time("2023-12-06")
@pytest.mark.parametrize(
    "param_name,param_type,param_value",
    [("SubnetId", "AWS::EC2::Subnet::Id", "s-prv-2"), ("AZName", "AWS::EC2::AvailabilityZone::Name", "az-2")],
)
def test_provision_product_when_product_has_subnet_id_parameter_and_no_az_inuser_profile_should_fetch_subnet_with_most_ips(
    param_name,
    param_type,
    param_value,
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
    get_provisioned_product,
    mock_subnet,
    mock_private_route_table,
    mock_unit_of_work,
    mock_user_profile_repo,
):
    # ARRANGE
    command = provision_product_command.ProvisionProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
    )

    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(
                key=param_name, isTechnicalParameter=True, parameterType=param_type
            ),
        ],
    )
    mock_instance_mgmt_srv.describe_vpc_route_tables.return_value = [
        mock_private_route_table(
            associations=[
                network_route_table.NetworkRouteTableAssociation(
                    subnet_id="s-prv-1",
                ),
                network_route_table.NetworkRouteTableAssociation(
                    subnet_id="s-prv-2",
                ),
            ]
        )
    ]
    mock_instance_mgmt_srv.describe_vpc_subnets.return_value = [
        mock_subnet(subnet_id="s-prv-1", available_ip_address_count=100, availability_zone="az-1"),
        mock_subnet(subnet_id="s-prv-2", available_ip_address_count=120, availability_zone="az-2"),
    ]

    mock_user_profile_repo.get.return_value = user_profile.UserProfile(
        userId="test-user",
        preferredRegion="eu-central-1",
        createDate="",
        lastUpdateDate="",
    )

    # ACT
    provision_product.handle(
        command=command,
        publisher=mock_publisher,
        products_srv=mock_products_srv,
        virtual_targets_qs=mock_provisioned_products_qs,
        parameter_srv=mock_parameter_srv,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        logger=mock_logger,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        subnet_selector=networking_helpers.get_provisioning_subnet_selector("PrivateSubnetWithTransitGateway"),
        authorize_user_ip_address_param_value=True,
        uow=mock_unit_of_work,
    )

    # ASSERT
    provisioning_parameters = mock_products_srv.provision_product.call_args.kwargs.get("provisioning_parameters")
    provisioning_param = next(p for p in provisioning_parameters if p.key == param_name)
    assertpy.assert_that(provisioning_param.value).is_equal_to(param_value)
    mock_user_profile_repo.update_entity.assert_called_once_with(
        pk=user_profile.UserProfilePrimaryKey(userId="test-user"),
        entity=user_profile.UserProfile(
            userId="test-user",
            preferredRegion="eu-central-1",
            preferredNetwork=None,
            preferredMaintenanceWindows=None,
            createDate="2023-12-06T00:00:00+00:00",
            lastUpdateDate="2023-12-06T00:00:00+00:00",
            persistentHomeDrives=None,
            preferredAvailabilityZone="az-2",
        ),
    )


@freeze_time("2023-12-06")
@pytest.mark.parametrize(
    "param_name,param_type,param_value",
    [("SubnetId", "AWS::EC2::Subnet::Id", "s-prv-1"), ("AZName", "AWS::EC2::AvailabilityZone::Name", "az-1")],
)
def test_provision_product_when_product_has_subnet_id_parameter_and_user_profile_az_should_select_users_az_subnet(
    param_name,
    param_type,
    param_value,
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
    get_provisioned_product,
    mock_subnet,
    mock_private_route_table,
    mock_user_profile_repo,
    mock_unit_of_work,
):
    # ARRANGE
    command = provision_product_command.ProvisionProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
    )

    mock_user_profile_repo.get.return_value = user_profile.UserProfile(
        userId="test-user",
        preferredRegion="eu-central-1",
        createDate="",
        lastUpdateDate="",
        preferredAvailabilityZone="az-1",
    )

    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(
                key=param_name, isTechnicalParameter=True, parameterType=param_type
            ),
        ],
    )
    mock_instance_mgmt_srv.describe_vpc_route_tables.return_value = [
        mock_private_route_table(
            associations=[
                network_route_table.NetworkRouteTableAssociation(
                    subnet_id="s-prv-1",
                ),
                network_route_table.NetworkRouteTableAssociation(
                    subnet_id="s-prv-2",
                ),
            ]
        )
    ]
    mock_instance_mgmt_srv.describe_vpc_subnets.return_value = [
        mock_subnet(subnet_id="s-prv-1", available_ip_address_count=100, availability_zone="az-1"),
        mock_subnet(subnet_id="s-prv-2", available_ip_address_count=120, availability_zone="az-2"),
    ]

    # ACT
    provision_product.handle(
        command=command,
        publisher=mock_publisher,
        products_srv=mock_products_srv,
        virtual_targets_qs=mock_provisioned_products_qs,
        parameter_srv=mock_parameter_srv,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        logger=mock_logger,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        subnet_selector=networking_helpers.get_provisioning_subnet_selector("PrivateSubnetWithTransitGateway"),
        authorize_user_ip_address_param_value=True,
        uow=mock_unit_of_work,
    )

    # ASSERT
    provisioning_parameters = mock_products_srv.provision_product.call_args.kwargs.get("provisioning_parameters")
    provisioning_param = next(p for p in provisioning_parameters if p.key == param_name)
    assertpy.assert_that(provisioning_param.value).is_equal_to(param_value)
    mock_user_profile_repo.add.assert_not_called()
    mock_user_profile_repo.update_entity.assert_not_called()


@freeze_time("2023-12-06")
@pytest.mark.parametrize(
    "param_name,param_type,param_value",
    [("SubnetId", "AWS::EC2::Subnet::Id", "s-prv-2"), ("AZName", "AWS::EC2::AvailabilityZone::Name", "az-2")],
)
def test_provision_product_when_product_has_subnet_id_parameter_and_user_profile_az_is_full_should_select_next_available_subnet(
    param_name,
    param_type,
    param_value,
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
    get_provisioned_product,
    mock_subnet,
    mock_private_route_table,
    mock_user_profile_repo,
    mock_unit_of_work,
):
    # ARRANGE
    command = provision_product_command.ProvisionProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
    )

    mock_user_profile_repo.get.return_value = user_profile.UserProfile(
        userId="test-user",
        preferredRegion="eu-central-1",
        createDate="",
        lastUpdateDate="",
        preferredAvailabilityZone="az-1",
    )

    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(
                key=param_name, isTechnicalParameter=True, parameterType=param_type
            ),
        ],
    )
    mock_instance_mgmt_srv.describe_vpc_route_tables.return_value = [
        mock_private_route_table(
            associations=[
                network_route_table.NetworkRouteTableAssociation(
                    subnet_id="s-prv-1",
                ),
                network_route_table.NetworkRouteTableAssociation(
                    subnet_id="s-prv-2",
                ),
            ]
        )
    ]
    mock_instance_mgmt_srv.describe_vpc_subnets.return_value = [
        mock_subnet(subnet_id="s-prv-1", available_ip_address_count=0, availability_zone="az-1"),
        mock_subnet(subnet_id="s-prv-2", available_ip_address_count=120, availability_zone="az-2"),
    ]

    # ACT
    provision_product.handle(
        command=command,
        publisher=mock_publisher,
        products_srv=mock_products_srv,
        virtual_targets_qs=mock_provisioned_products_qs,
        parameter_srv=mock_parameter_srv,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        logger=mock_logger,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        subnet_selector=networking_helpers.get_provisioning_subnet_selector("PrivateSubnetWithTransitGateway"),
        authorize_user_ip_address_param_value=True,
        uow=mock_unit_of_work,
    )

    # ASSERT
    provisioning_parameters = mock_products_srv.provision_product.call_args.kwargs.get("provisioning_parameters")
    provisioning_param = next(p for p in provisioning_parameters if p.key == param_name)
    assertpy.assert_that(provisioning_param.value).is_equal_to(param_value)
    mock_user_profile_repo.add.assert_not_called()
    mock_user_profile_repo.update_entity.assert_not_called()


@freeze_time("2023-12-06")
def test_provision_product_when_product_has_subnet_id_parameter_but_no_private_subnet_with_tgw_should_raise(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
    get_provisioned_product,
    mock_public_route_table,
    mock_unit_of_work,
):
    # ARRANGE
    command = provision_product_command.ProvisionProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
    )

    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(
                key="SubnetId", isTechnicalParameter=True, parameterType="AWS::EC2::Subnet::Id"
            ),
        ],
    )
    mock_instance_mgmt_srv.describe_vpc_route_tables.return_value = [
        mock_public_route_table(),
        network_route_table.NetworkRouteTable(
            associations=[
                network_route_table.NetworkRouteTableAssociation(
                    subnet_id="s-prv",
                )
            ],
            routes=[
                network_route_table.NetworkRouteTableRoute(
                    gateway_id="local",
                )
            ],
        ),
    ]

    # ACT
    provision_product.handle(
        command=command,
        publisher=mock_publisher,
        products_srv=mock_products_srv,
        virtual_targets_qs=mock_provisioned_products_qs,
        parameter_srv=mock_parameter_srv,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        logger=mock_logger,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        subnet_selector=networking_helpers.get_provisioning_subnet_selector("PrivateSubnetWithTransitGateway"),
        authorize_user_ip_address_param_value=True,
        uow=mock_unit_of_work,
    )

    # ASSERT
    mock_products_srv.provision_product.assert_not_called()
    mock_message_bus.publish.assert_called_once_with(
        product_launch_failed.ProductLaunchFailed(
            provisionedProductId="pp-123",
            reason="No private subnet with transit gateway found",
            projectId="proj-123",
            productName="Pied Piper",
            productType=provisioned_product.ProvisionedProductType.VirtualTarget,
            owner="T0011AA",
        )
    )


@freeze_time("2023-12-06")
def test_provision_product_when_product_has_subnets_ids_parameter_but_no_private_subnets_with_tgw_should_raise(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
    get_provisioned_product,
    mock_public_route_table,
    mock_unit_of_work,
):
    # ARRANGE
    command = provision_product_command.ProvisionProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
    )

    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(
                key="SubnetsIds", isTechnicalParameter=True, parameterType="List<AWS::EC2::Subnet::Id>"
            ),
        ],
    )
    mock_instance_mgmt_srv.describe_vpc_route_tables.return_value = [
        mock_public_route_table(),
        network_route_table.NetworkRouteTable(
            associations=[
                network_route_table.NetworkRouteTableAssociation(
                    subnet_id="s-prv",
                )
            ],
            routes=[
                network_route_table.NetworkRouteTableRoute(
                    gateway_id="local",
                )
            ],
        ),
    ]

    # ACT
    provision_product.handle(
        command=command,
        publisher=mock_publisher,
        products_srv=mock_products_srv,
        virtual_targets_qs=mock_provisioned_products_qs,
        parameter_srv=mock_parameter_srv,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        logger=mock_logger,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        subnet_selector=networking_helpers.get_provisioning_subnet_selector("PrivateSubnetWithTransitGateway"),
        authorize_user_ip_address_param_value=True,
        uow=mock_unit_of_work,
    )

    # ASSERT
    mock_products_srv.provision_product.assert_not_called()
    mock_message_bus.publish.assert_called_once_with(
        product_launch_failed.ProductLaunchFailed(
            provisionedProductId="pp-123",
            reason="No private subnet with transit gateway found",
            projectId="proj-123",
            productName="Pied Piper",
            productType=provisioned_product.ProvisionedProductType.VirtualTarget,
            owner="T0011AA",
        )
    )


@freeze_time("2023-12-06")
def test_provision_product_when_product_does_not_have_subnet_id_should_not_fetch_subnets_from_spoke(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
    get_provisioned_product,
    mock_unit_of_work,
):
    # ARRANGE
    command = provision_product_command.ProvisionProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
    )

    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
        ],
    )

    # ACT
    provision_product.handle(
        command=command,
        publisher=mock_publisher,
        products_srv=mock_products_srv,
        virtual_targets_qs=mock_provisioned_products_qs,
        parameter_srv=mock_parameter_srv,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        logger=mock_logger,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        subnet_selector=networking_helpers.get_provisioning_subnet_selector("PrivateSubnetWithTransitGateway"),
        authorize_user_ip_address_param_value=True,
        uow=mock_unit_of_work,
    )

    # ASSERT
    mock_products_srv.provision_product.assert_called_with(
        user_id="T0011AA",
        aws_account_id="001234567890",
        sc_product_id="sc-prod-123",
        sc_provisioning_artifact_id="sc-pa-123",
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
        ],
        name="my name",
        region="us-east-1",
        tags=[
            {"Key": "UserTID", "Value": "T0011AA"},
            {"Key": "OwnerID", "Value": "T0011AA"},
            {"Key": "OwnerDomains", "Value": "domain"},
            {"Key": "vew:provisionedProduct:ownerDomains", "Value": "domain"},
            {"Key": "vew:provisionedProduct:productType", "Value": "VIRTUAL_TARGET"},
            {"Key": "vew:provisionedProduct:id", "Value": "pp-123"},
            {"Key": "vew:provisionedProduct:ownerId", "Value": "T0011AA"},
            {"Key": "vew:provisionedProduct:versionName", "Value": "1.0.0"},
            {"Key": "vew:product:name", "Value": "Pied Piper"},
            {"Key": "vew:product:versionName", "Value": "1.0.0"},
            {"Key": "vew:product:type", "Value": "VIRTUAL_TARGET"},
            {"Key": "vew:product:category", "Value": None},
        ],
    )
    mock_instance_mgmt_srv.describe_vpc_route_tables.assert_not_called()
    mock_instance_mgmt_srv.describe_vpc_subnets.assert_not_called()


@freeze_time("2023-12-06")
def test_provision_virtual_target_product_when_already_has_sc_provisioned_product_id_should_ignore(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_unit_of_work,
    get_provisioned_product,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
    default_subnet_selector,
):
    # ARRANGE
    command = provision_product_command.ProvisionProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(sc_provisioned_product_id="pp-123")

    # ACT
    provision_product.handle(
        command=command,
        publisher=mock_publisher,
        products_srv=mock_products_srv,
        virtual_targets_qs=mock_provisioned_products_qs,
        parameter_srv=mock_parameter_srv,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        logger=mock_logger,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        subnet_selector=default_subnet_selector,
        authorize_user_ip_address_param_value=True,
        uow=mock_unit_of_work,
    )

    # ASSERT
    mock_message_bus.publish.assert_not_called()
    mock_unit_of_work.commit.assert_not_called()


@pytest.mark.parametrize(
    "virtual_target_status", [s for s in product_status.ProductStatus if s != product_status.ProductStatus.Provisioning]
)
def test_provision_virtual_target_product_when_status_not_provisioning_should_raise(
    virtual_target_status,
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_unit_of_work,
    get_provisioned_product,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
    default_subnet_selector,
):
    # ARRANGE
    command = provision_product_command.ProvisionProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(status=virtual_target_status)

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        provision_product.handle(
            command=command,
            publisher=mock_publisher,
            products_srv=mock_products_srv,
            virtual_targets_qs=mock_provisioned_products_qs,
            parameter_srv=mock_parameter_srv,
            instance_mgmt_srv=mock_instance_mgmt_srv,
            logger=mock_logger,
            spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
            subnet_selector=default_subnet_selector,
            authorize_user_ip_address_param_value=True,
            uow=mock_unit_of_work,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        f"Provisioned product pp-123 must be in PROVISIONING state (current state: {virtual_target_status})"
    )
    mock_message_bus.publish.assert_not_called()
    mock_unit_of_work.commit.assert_not_called()


@freeze_time("2023-12-06")
def test_provision_virtual_target_when_catalog_call_fails_should_fail_provisioning(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
    default_subnet_selector,
):
    # ARRANGE
    command = provision_product_command.ProvisionProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
    )

    mock_products_srv.provision_product.side_effect = [Exception("failed")]
    # ACT
    provision_product.handle(
        command=command,
        publisher=mock_publisher,
        products_srv=mock_products_srv,
        virtual_targets_qs=mock_provisioned_products_qs,
        parameter_srv=mock_parameter_srv,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        logger=mock_logger,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        subnet_selector=default_subnet_selector,
        authorize_user_ip_address_param_value=True,
        uow=mock_unit_of_work,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        product_launch_failed.ProductLaunchFailed(
            projectId="proj-123",
            provisionedProductId="pp-123",
            productName="Pied Piper",
            productType=provisioned_product.ProvisionedProductType.VirtualTarget,
            owner="T0011AA",
        )
    )
    mock_unit_of_work.commit.assert_called_once()
    mock_provisioned_product_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        provisioned_product.ProvisionedProduct.construct(
            projectId="proj-123",
            provisionedProductId="pp-123",
            provisionedProductName=mock.ANY,
            provisionedProductType=provisioned_product.ProvisionedProductType.VirtualTarget,
            userId="T0011AA",
            userDomains=["domain"],
            status=product_status.ProductStatus.ProvisioningError,
            statusReason="failed",
            productId="prod-123",
            productName="Pied Piper",
            productDescription="Compression",
            technologyId="tech-123",
            versionId="vers-123",
            versionName="1.0.0",
            awsAccountId="001234567890",
            accountId="acc-123",
            instanceId="i-01234567890abcdef",
            stage=provisioned_product.ProvisionedProductStage.DEV,
            region="us-east-1",
            amiId="ami-123",
            scProductId="sc-prod-123",
            scProvisioningArtifactId="sc-pa-123",
            provisioningParameters=[
                provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
                provisioning_parameter.ProvisioningParameter(
                    key="UserSecurityGroupId", value="sg-12345", isTechnicalParameter=True
                ),
            ],
            createDate="2023-12-05T00:00:00+00:00",
            lastUpdateDate="2023-12-06T00:00:00+00:00",
            createdBy="T0011AA",
            lastUpdatedBy="T0011AA",
            availabilityZonesTriggered=None,
        ),
    )


@freeze_time("2023-12-06")
def test_provision_virtual_target_when_all_az_triggered_should_fail_provisioning(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
    # default_subnet_selector,
    get_provisioned_product,
):
    # ARRANGE
    command = provision_product_command.ProvisionProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
    )
    default_subnet_selector = mock.MagicMock()
    default_subnet_selector.side_effect = lambda **kwargs: [
        network_subnet.NetworkSubnet(
            subnet_id="s-pub-1",
            available_ip_address_count=80,
            availability_zone="az-1",
            tags=[],
            cidr_block="192.168.1.0/24",
            vpc_id="vpc-123",
        ),
        network_subnet.NetworkSubnet(
            subnet_id="s-pub-2",
            available_ip_address_count=100,
            availability_zone="az-2",
            tags=[],
            cidr_block="192.168.1.0/24",
            vpc_id="vpc-123",
        ),
        network_subnet.NetworkSubnet(
            subnet_id="s-pub-3",
            available_ip_address_count=120,
            availability_zone="az-3",
            tags=[],
            cidr_block="192.168.1.0/24",
            vpc_id="vpc-123",
        ),
    ]

    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        availability_zones_triggered=["az-3", "az-2", "az-1"],
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(
                key="SubnetId", isTechnicalParameter=True, parameterType="AWS::EC2::Subnet::Id"
            )
        ],
    )
    # ACT
    provision_product.handle(
        command=command,
        publisher=mock_publisher,
        products_srv=mock_products_srv,
        virtual_targets_qs=mock_provisioned_products_qs,
        parameter_srv=mock_parameter_srv,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        logger=mock_logger,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        subnet_selector=default_subnet_selector,
        authorize_user_ip_address_param_value=False,
        uow=mock_unit_of_work,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        product_launch_failed.ProductLaunchFailed(
            projectId="proj-123",
            provisionedProductId="pp-123",
            productName="Pied Piper",
            productType=provisioned_product.ProvisionedProductType.VirtualTarget,
            owner="T0011AA",
        )
    )
    mock_unit_of_work.commit.assert_called_once()
    mock_provisioned_product_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        provisioned_product.ProvisionedProduct.construct(
            projectId="proj-123",
            provisionedProductId="pp-123",
            provisionedProductName="my name",
            provisionedProductType=provisioned_product.ProvisionedProductType.VirtualTarget,
            userId="T0011AA",
            userDomains=["domain"],
            status=product_status.ProductStatus.ProvisioningError,
            statusReason="InsufficientCapacityInAllAvailabilityZones",
            productId="prod-123",
            productName="Pied Piper",
            productDescription="Compression",
            technologyId="tech-123",
            versionId="vers-123",
            versionName="1.0.0",
            awsAccountId="001234567890",
            accountId="acc-123",
            instanceId="i-01234567890abcdef",
            stage=provisioned_product.ProvisionedProductStage.DEV,
            region="us-east-1",
            amiId="ami-123",
            scProductId="sc-prod-123",
            scProvisioningArtifactId="sc-pa-123",
            provisioningParameters=[
                provisioning_parameter.ProvisioningParameter(
                    key="SubnetId", isTechnicalParameter=True, parameterType="AWS::EC2::Subnet::Id"
                )
            ],
            createDate="2023-12-05T00:00:00+00:00",
            lastUpdateDate="2023-12-06T00:00:00+00:00",
            createdBy="T0011AA",
            lastUpdatedBy="T0011AA",
            availabilityZonesTriggered=["az-3", "az-2", "az-1"],
        ),
    )


@freeze_time("2023-12-06")
def test_provision_product_when_product_has_ip_address_parameter_should_fetch_random_available_ip_address(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
    get_provisioned_product,
):
    # ARRANGE
    command = provision_product_command.ProvisionProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
    )
    mock_instance_mgmt_srv.describe_subnet.return_value = network_subnet.NetworkSubnet(
        AvailabilityZone="az-1",
        CidrBlock="192.168.1.0/24",
        SubnetId="s-prv",
        VpcId="XXXXXXX",
        Tags=[],
        AvailableIpAddressCount=100,
    )
    mock_instance_mgmt_srv.describe_subnet_interfaces.return_value = [
        network_interface.NetworkInterface(
            NetworkInterfaceId="XXXXXXX",
            PrivateIpAddresses=[network_interface.PrivateIpAddress(PrivateIpAddress=str(ip))],
        )
        for ip in ipaddress.IPv4Network("192.168.1.0/24").hosts()
        if not str(ip).endswith((".1", ".2", ".3", ".254"))
    ]

    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(
                key="SubnetId", isTechnicalParameter=True, parameterType="AWS::EC2::Subnet::Id"
            ),
            provisioning_parameter.ProvisioningParameter(
                key="VEWAllocatedIPAddress",
                isTechnicalParameter=True,
            ),
        ],
    )

    # ACT
    provision_product.handle(
        command=command,
        publisher=mock_publisher,
        products_srv=mock_products_srv,
        virtual_targets_qs=mock_provisioned_products_qs,
        parameter_srv=mock_parameter_srv,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        logger=mock_logger,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        subnet_selector=networking_helpers.get_provisioning_subnet_selector("PrivateSubnetWithTransitGateway"),
        authorize_user_ip_address_param_value=True,
        uow=mock_unit_of_work,
    )

    # ASSERT
    mock_products_srv.provision_product.assert_called_with(
        user_id="T0011AA",
        aws_account_id="001234567890",
        sc_product_id="sc-prod-123",
        sc_provisioning_artifact_id="sc-pa-123",
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(
                key="SubnetId", value="s-prv", isTechnicalParameter=True, parameterType="AWS::EC2::Subnet::Id"
            ),
            provisioning_parameter.ProvisioningParameter(
                key="VEWAllocatedIPAddress",
                value="192.168.1.254",
                isTechnicalParameter=True,
            ),
        ],
        name="my name-az-1",
        region="us-east-1",
        tags=[
            {"Key": "UserTID", "Value": "T0011AA"},
            {"Key": "OwnerID", "Value": "T0011AA"},
            {"Key": "OwnerDomains", "Value": "domain"},
            {"Key": "vew:provisionedProduct:ownerDomains", "Value": "domain"},
            {"Key": "vew:provisionedProduct:productType", "Value": "VIRTUAL_TARGET"},
            {"Key": "vew:provisionedProduct:id", "Value": "pp-123"},
            {"Key": "vew:provisionedProduct:ownerId", "Value": "T0011AA"},
            {"Key": "vew:provisionedProduct:versionName", "Value": "1.0.0"},
            {"Key": "vew:product:name", "Value": "Pied Piper"},
            {"Key": "vew:product:versionName", "Value": "1.0.0"},
            {"Key": "vew:product:type", "Value": "VIRTUAL_TARGET"},
            {"Key": "vew:product:category", "Value": None},
        ],
    )

    mock_unit_of_work.commit.assert_called_once()
    mock_provisioned_product_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        provisioned_product.ProvisionedProduct.construct(
            projectId="proj-123",
            provisionedProductId="pp-123",
            provisionedProductName=mock.ANY,
            provisionedProductType=provisioned_product.ProvisionedProductType.VirtualTarget,
            userId="T0011AA",
            userDomains=["domain"],
            status=product_status.ProductStatus.Provisioning,
            productId="prod-123",
            productName="Pied Piper",
            productDescription="Compression",
            technologyId="tech-123",
            versionId="vers-123",
            versionName="1.0.0",
            awsAccountId="001234567890",
            accountId="acc-123",
            instanceId="i-01234567890abcdef",
            stage=provisioned_product.ProvisionedProductStage.DEV,
            region="us-east-1",
            amiId="ami-123",
            scProductId="sc-prod-123",
            scProvisioningArtifactId="sc-pa-123",
            scProvisionedProductId="pp-123",
            provisioningParameters=[
                provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
                provisioning_parameter.ProvisioningParameter(
                    key="SubnetId", value="s-prv", isTechnicalParameter=True, parameterType="AWS::EC2::Subnet::Id"
                ),
                provisioning_parameter.ProvisioningParameter(
                    key="VEWAllocatedIPAddress", value="192.168.1.254", isTechnicalParameter=True
                ),
            ],
            createDate="2023-12-05T00:00:00+00:00",
            lastUpdateDate="2023-12-06T00:00:00+00:00",
            createdBy="T0011AA",
            lastUpdatedBy="T0011AA",
            availabilityZonesTriggered=["az-1"],
            privateIp="192.168.1.254",
        ),
    )


@freeze_time("2023-12-06")
def test_provision_product_when_product_has_ip_address_parameter_should_raise_if_no_more_ips_available(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_unit_of_work,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
    get_provisioned_product,
    mock_message_bus,
):
    # ARRANGE
    command = provision_product_command.ProvisionProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
    )
    mock_instance_mgmt_srv.describe_subnet.return_value = network_subnet.NetworkSubnet(
        AvailabilityZone="az-1",
        CidrBlock="192.168.1.0/24",
        SubnetId="s-prv",
        VpcId="XXXXXXX",
        Tags=[],
        AvailableIpAddressCount=100,
    )
    mock_instance_mgmt_srv.describe_subnet_interfaces.return_value = [
        network_interface.NetworkInterface(
            NetworkInterfaceId="XXXXXXX",
            PrivateIpAddresses=[network_interface.PrivateIpAddress(PrivateIpAddress=str(ip))],
        )
        for ip in ipaddress.IPv4Network("192.168.1.0/24").hosts()
        if not str(ip).endswith((".1", ".2", ".3"))
    ]

    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        provisioning_parameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(
                key="SubnetId", isTechnicalParameter=True, parameterType="AWS::EC2::Subnet::Id"
            ),
            provisioning_parameter.ProvisioningParameter(
                key="VEWAllocatedIPAddress",
                isTechnicalParameter=True,
            ),
        ],
    )

    # ACT
    provision_product.handle(
        command=command,
        publisher=mock_publisher,
        products_srv=mock_products_srv,
        virtual_targets_qs=mock_provisioned_products_qs,
        parameter_srv=mock_parameter_srv,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        logger=mock_logger,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        subnet_selector=networking_helpers.get_provisioning_subnet_selector("PrivateSubnetWithTransitGateway"),
        authorize_user_ip_address_param_value=True,
        uow=mock_unit_of_work,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        product_launch_failed.ProductLaunchFailed(
            provisionedProductId="pp-123",
            projectId="proj-123",
            productName="Pied Piper",
            productType=provisioned_product.ProvisionedProductType.VirtualTarget,
            owner="T0011AA",
        )
    )
