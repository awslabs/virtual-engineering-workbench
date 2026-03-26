from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.provisioning.domain.command_handlers.product_provisioning import start_update
from app.provisioning.domain.commands.product_provisioning import (
    start_provisioned_product_update_command,
)
from app.provisioning.domain.events.product_provisioning import (
    provisioned_product_update_initialized,
)
from app.provisioning.domain.exceptions import domain_exception
from app.provisioning.domain.model import (
    product_status,
    provisioned_product,
    provisioning_parameter,
)
from app.provisioning.domain.ports import versions_query_service
from app.provisioning.domain.read_models import version
from app.provisioning.domain.value_objects import (
    ip_address_value_object,
    is_auto_update_value_object,
    product_version_id_value_object,
    project_id_value_object,
    provisioned_product_id_value_object,
    provisioning_parameters_value_object,
    user_id_value_object,
)


@pytest.fixture()
def mock_versions_query_service(get_test_version):
    qs_mock = mock.create_autospec(spec=versions_query_service.VersionsQueryService)
    qs_mock.get_product_version_distributions.return_value = [
        get_test_version(
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
    ]
    return qs_mock


@pytest.fixture()
def get_command():
    def _get_command(
        user_id: str = "T0011AA",
        provisioning_parameters: provisioning_parameters_value_object.ProvisioningParametersValueObject = provisioning_parameters_value_object.from_list(
            [
                {
                    "key": "SomeParam",
                    "value": "some-test-param-value",
                }
            ]
        ),
    ):
        return start_provisioned_product_update_command.StartProvisionedProductUpdateCommand(
            provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
            project_id=project_id_value_object.from_str("proj-123"),
            user_id=user_id_value_object.from_str(user_id),
            provisioning_parameters=provisioning_parameters,
            user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
            version_id=product_version_id_value_object.from_str("vers-321"),
            is_auto_update=is_auto_update_value_object.IsAutoUpdateValueObject(value=False),
        )

    return _get_command


def test_handle_when_user_is_different_should_raise(
    mock_publisher,
    mock_versions_query_service,
    mock_logger,
    mock_provisioned_products_qs,
    get_provisioned_product,
    get_command,
):
    # ARRANGE
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product()

    command = get_command(user_id="T0011BB")

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        start_update.handle(
            command=command,
            publisher=mock_publisher,
            versions_qs=mock_versions_query_service,
            logger=mock_logger,
            provisioned_products_qs=mock_provisioned_products_qs,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to("User is not allowed to modify the requested provisioned product.")


@pytest.mark.parametrize(
    "pp_status",
    [
        product_status.ProductStatus.Updating,
        product_status.ProductStatus.Provisioning,
        product_status.ProductStatus.Deprovisioning,
        product_status.ProductStatus.ProvisioningError,
        product_status.ProductStatus.Starting,
        product_status.ProductStatus.Stopping,
    ],
)
def test_handle_when_status_is_not_allowed_should_raise(
    mock_publisher,
    mock_versions_query_service,
    mock_logger,
    mock_provisioned_products_qs,
    get_provisioned_product,
    get_command,
    pp_status,
):
    # ARRANGE
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(status=pp_status)

    command = get_command()

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        start_update.handle(
            command=command,
            publisher=mock_publisher,
            versions_qs=mock_versions_query_service,
            logger=mock_logger,
            provisioned_products_qs=mock_provisioned_products_qs,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        f"Provisioned product pp-123 must be in one of RUNNING, STOPPED states (current state: {pp_status})"
    )


@pytest.mark.parametrize(
    "current_version,new_version,available_parameters,current_parameters,requested_parameters,new_parameters",
    [
        # Update version if parameters are the same
        (
            "vers-123",
            "vers-321",
            [
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
            ],
            [
                provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
                provisioning_parameter.ProvisioningParameter(key="UserSecurityGroupId", isTechnicalParameter=True),
            ],
            [
                {
                    "key": "SomeParam",
                    "value": "some-test-param-value",
                }
            ],
            [
                provisioning_parameter.ProvisioningParameter(
                    key="SomeParam",
                    value="some-test-param-value",
                    parameterType="String",
                ),
                provisioning_parameter.ProvisioningParameter(
                    key="SomeTechParam",
                    value="/workbench/autosar/adaptive/ami-id/v1-3-x",
                    parameterType="AWS::SSM::Parameter::Value<String>",
                ),
            ],
        ),
        # Update version and parameter if new parameter value requested
        (
            "vers-123",
            "vers-321",
            [
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
            ],
            [
                provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
                provisioning_parameter.ProvisioningParameter(key="UserSecurityGroupId", isTechnicalParameter=True),
            ],
            [
                {
                    "key": "SomeParam",
                    "value": "some-test-new-param-value",
                }
            ],
            [
                provisioning_parameter.ProvisioningParameter(
                    key="SomeParam",
                    value="some-test-new-param-value",
                    parameterType="String",
                ),
                provisioning_parameter.ProvisioningParameter(
                    key="SomeTechParam",
                    value="/workbench/autosar/adaptive/ami-id/v1-3-x",
                    parameterType="AWS::SSM::Parameter::Value<String>",
                ),
            ],
        ),
        # Update version and parameters if parameters value is allowed
        (
            "vers-123",
            "vers-321",
            [
                version.VersionParameter(
                    parameterKey="InstanceType",
                    defaultValue="m8i.4xlarge",
                    parameterType="String",
                    parameterConstraints=version.ParameterConstraints(
                        allowedValues=[
                            "m8i.4xlarge",
                            "m8i.8xlarge",
                            "m8i.16xlarge",
                        ]
                    ),
                ),
                version.VersionParameter(
                    parameterKey="SomeTechParam",
                    defaultValue="/workbench/autosar/adaptive/ami-id/v1-3-x",
                    parameterType="AWS::SSM::Parameter::Value<String>",
                ),
            ],
            [
                provisioning_parameter.ProvisioningParameter(key="InstanceType", value="m8i.4xlarge"),
                provisioning_parameter.ProvisioningParameter(key="UserSecurityGroupId", isTechnicalParameter=True),
            ],
            [
                {
                    "key": "InstanceType",
                    "value": "m8i.8xlarge",
                }
            ],
            [
                provisioning_parameter.ProvisioningParameter(
                    key="InstanceType", value="m8i.8xlarge", parameterType="String"
                ),
                provisioning_parameter.ProvisioningParameter(
                    key="SomeTechParam",
                    value="/workbench/autosar/adaptive/ami-id/v1-3-x",
                    parameterType="AWS::SSM::Parameter::Value<String>",
                ),
            ],
        ),
        # Update version and preserve current parameter value if no new parameters requested
        (
            "vers-123",
            "vers-321",
            [
                version.VersionParameter(
                    parameterKey="InstanceType",
                    defaultValue="m8i.4xlarge",
                    parameterType="String",
                    parameterConstraints=version.ParameterConstraints(
                        allowedValues=[
                            "m8i.4xlarge",
                            "m8i.8xlarge",
                            "m8i.16xlarge",
                        ]
                    ),
                ),
                version.VersionParameter(
                    parameterKey="SomeTechParam",
                    defaultValue="/workbench/autosar/adaptive/ami-id/v1-3-x",
                    parameterType="AWS::SSM::Parameter::Value<String>",
                ),
            ],
            [
                provisioning_parameter.ProvisioningParameter(key="InstanceType", value="m8i.16xlarge"),
                provisioning_parameter.ProvisioningParameter(key="UserSecurityGroupId", isTechnicalParameter=True),
            ],
            [],
            [
                provisioning_parameter.ProvisioningParameter(
                    key="InstanceType", value="m8i.16xlarge", parameterType="String"
                ),
                provisioning_parameter.ProvisioningParameter(
                    key="SomeTechParam",
                    value="/workbench/autosar/adaptive/ami-id/v1-3-x",
                    parameterType="AWS::SSM::Parameter::Value<String>",
                ),
            ],
        ),
        # Update version and set default parameter value if current parameters value is not allowed in new version
        (
            "vers-123",
            "vers-321",
            [
                version.VersionParameter(
                    parameterKey="InstanceType",
                    defaultValue="m8i.4xlarge",
                    parameterType="String",
                    parameterConstraints=version.ParameterConstraints(
                        allowedValues=[
                            "m8i.4xlarge",
                            "m8i.8xlarge",
                        ]
                    ),
                ),
                version.VersionParameter(
                    parameterKey="SomeTechParam",
                    defaultValue="/workbench/autosar/adaptive/ami-id/v1-3-x",
                    parameterType="AWS::SSM::Parameter::Value<String>",
                ),
            ],
            [
                provisioning_parameter.ProvisioningParameter(key="InstanceType", value="m8i.16xlarge"),
                provisioning_parameter.ProvisioningParameter(key="UserSecurityGroupId", isTechnicalParameter=True),
            ],
            [],
            [
                provisioning_parameter.ProvisioningParameter(
                    key="InstanceType", value="m8i.4xlarge", parameterType="String"
                ),
                provisioning_parameter.ProvisioningParameter(
                    key="SomeTechParam",
                    value="/workbench/autosar/adaptive/ami-id/v1-3-x",
                    parameterType="AWS::SSM::Parameter::Value<String>",
                ),
            ],
        ),
        # Update parameter if new parameter requested and version is the same
        (
            "vers-123",
            "vers-123",
            [
                version.VersionParameter(
                    parameterKey="InstanceType",
                    defaultValue="m8i.4xlarge",
                    parameterType="String",
                    parameterConstraints=version.ParameterConstraints(
                        allowedValues=[
                            "m8i.4xlarge",
                            "m8i.8xlarge",
                        ]
                    ),
                ),
                version.VersionParameter(
                    parameterKey="SomeTechParam",
                    defaultValue="/workbench/autosar/adaptive/ami-id/v1-3-x",
                    parameterType="AWS::SSM::Parameter::Value<String>",
                ),
            ],
            [
                provisioning_parameter.ProvisioningParameter(key="InstanceType", value="m8i.4xlarge"),
                provisioning_parameter.ProvisioningParameter(key="UserSecurityGroupId", isTechnicalParameter=True),
            ],
            [
                {
                    "key": "InstanceType",
                    "value": "m8i.8xlarge",
                }
            ],
            [
                provisioning_parameter.ProvisioningParameter(
                    key="InstanceType", value="m8i.8xlarge", parameterType="String"
                ),
                provisioning_parameter.ProvisioningParameter(
                    key="SomeTechParam",
                    value="/workbench/autosar/adaptive/ami-id/v1-3-x",
                    parameterType="AWS::SSM::Parameter::Value<String>",
                ),
            ],
        ),
        # Do not use old parameters if parameter not in new version
        (
            "vers-123",
            "vers-321",
            [
                version.VersionParameter(
                    parameterKey="InstanceType",
                    defaultValue="m8i.4xlarge",
                    parameterType="String",
                    parameterConstraints=version.ParameterConstraints(
                        allowedValues=[
                            "m8i.4xlarge",
                            "m8i.8xlarge",
                        ]
                    ),
                ),
                version.VersionParameter(
                    parameterKey="SomeNewTechParam",
                    defaultValue="/workbench/autosar/adaptive/ami-id/v1-3-x",
                    parameterType="AWS::SSM::Parameter::Value<String>",
                ),
            ],
            [
                provisioning_parameter.ProvisioningParameter(key="InstanceType", value="m8i.4xlarge"),
                # Parameter from old version
                provisioning_parameter.ProvisioningParameter(key="SomeTechParam", isTechnicalParameter=True),
            ],
            [
                {
                    "key": "InstanceType",
                    "value": "m8i.8xlarge",
                }
            ],
            [
                provisioning_parameter.ProvisioningParameter(
                    key="InstanceType", value="m8i.8xlarge", parameterType="String"
                ),
                provisioning_parameter.ProvisioningParameter(
                    key="SomeNewTechParam",
                    value="/workbench/autosar/adaptive/ami-id/v1-3-x",
                    parameterType="AWS::SSM::Parameter::Value<String>",
                ),
            ],
        ),
    ],
)
@freeze_time("2023-12-05")
def test_handle_should_set_new_provisioning_parameters_and_publish(
    current_version,
    new_version,
    available_parameters,
    current_parameters,
    requested_parameters,
    new_parameters,
    mock_publisher,
    mock_versions_query_service,
    mock_logger,
    mock_provisioned_products_qs,
    get_provisioned_product,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    get_test_version,
):
    # ARRANGE
    mock_versions_query_service.get_product_version_distributions.return_value = [
        get_test_version(parameters=available_parameters, version_id=new_version)
    ]
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        status=product_status.ProductStatus.Running,
        new_version_id="vers-456-latest-version",
        provisioning_parameters=current_parameters,
        version_id=current_version,
    )

    command = start_provisioned_product_update_command.StartProvisionedProductUpdateCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        project_id=project_id_value_object.from_str("proj-123"),
        user_id=user_id_value_object.from_str("T0011AA"),
        provisioning_parameters=provisioning_parameters_value_object.from_list(requested_parameters),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
        version_id=product_version_id_value_object.from_str(new_version),
        is_auto_update=is_auto_update_value_object.IsAutoUpdateValueObject(value=False),
    )

    # ACT
    start_update.handle(
        command=command,
        publisher=mock_publisher,
        versions_qs=mock_versions_query_service,
        logger=mock_logger,
        provisioned_products_qs=mock_provisioned_products_qs,
    )

    # ASSERT
    mock_provisioned_product_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        get_provisioned_product(
            status=product_status.ProductStatus.Updating,
            version_id=current_version,
            new_version_id=new_version,
            new_version_name="1.0.0",
            provisioning_parameters=current_parameters,
            new_provisioning_parameters=new_parameters,
        ),
    )
    mock_unit_of_work.commit.assert_called_once()
    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_update_initialized.ProvisionedProductUpdateInitialized(
            provisionedProductId="pp-123", userIpAddress="127.0.0.1"
        )
    )
    mock_versions_query_service.get_product_version_distributions.assert_called_once_with(
        product_id="prod-123",
        version_id=new_version,
        region="us-east-1",
        stage=version.VersionStage.DEV,
    )


def test_handle_when_user_provides_technical_params_should_raise(
    mock_publisher,
    mock_versions_query_service,
    mock_logger,
    mock_provisioned_products_qs,
    get_provisioned_product,
    get_command,
):
    # ARRANGE
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        status=product_status.ProductStatus.Running, new_version_id="vers-321"
    )

    command = get_command(
        provisioning_parameters=provisioning_parameters_value_object.from_list(
            [
                {
                    "key": "SomeParam",
                    "value": "some-test-param-value",
                },
                {
                    "key": "SomeTechParam",
                    "value": "some-test-param-value",
                },
            ]
        )
    )

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        start_update.handle(
            command=command,
            publisher=mock_publisher,
            versions_qs=mock_versions_query_service,
            logger=mock_logger,
            provisioned_products_qs=mock_provisioned_products_qs,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to("Technical parameters SomeTechParam cannot be overridden.")


@pytest.mark.parametrize(
    "current_version,new_version,available_parameters,current_parameters,requested_parameters,new_parameters",
    [
        # Update version if parameters are the same - set VPC Id param with usePreviousValue == True
        (
            "vers-123",
            "vers-321",
            [
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
                version.VersionParameter(
                    parameterKey="VpcIdSSM",
                    parameterType="AWS::SSM::Parameter::Value<String>",
                    isTechnicalParameter=True,
                ),
            ],
            [
                provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
                provisioning_parameter.ProvisioningParameter(key="UserSecurityGroupId", isTechnicalParameter=True),
                # Not migrated VpcIdSSM param
                provisioning_parameter.ProvisioningParameter(
                    key="VpcIdSSM",
                    parameterType="AWS::SSM::Parameter::Value<String>",
                    isTechnicalParameter=True,
                ),
            ],
            [
                {
                    "key": "SomeParam",
                    "value": "some-test-param-value",
                }
            ],
            [
                provisioning_parameter.ProvisioningParameter(
                    key="SomeParam",
                    value="some-test-param-value",
                    parameterType="String",
                ),
                provisioning_parameter.ProvisioningParameter(
                    key="SomeTechParam",
                    value="/workbench/autosar/adaptive/ami-id/v1-3-x",
                    parameterType="AWS::SSM::Parameter::Value<String>",
                ),
                provisioning_parameter.ProvisioningParameter(
                    key="VpcIdSSM",
                    parameterType="AWS::SSM::Parameter::Value<String>",
                    isTechnicalParameter=True,
                    # The expected change
                    usePreviousValue=True,
                ),
            ],
        )
    ],
)
@freeze_time("2023-12-05")
def test_handle_should_set_vpc_is_ssm_param_to_use_previous_value_in_new_provisioning_parameters_and_publish(
    current_version,
    new_version,
    available_parameters,
    current_parameters,
    requested_parameters,
    new_parameters,
    mock_publisher,
    mock_versions_query_service,
    mock_logger,
    mock_provisioned_products_qs,
    get_provisioned_product,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    get_test_version,
):
    # ARRANGE
    mock_versions_query_service.get_product_version_distributions.return_value = [
        get_test_version(parameters=available_parameters, version_id=new_version)
    ]
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        status=product_status.ProductStatus.Running,
        new_version_id="vers-456-latest-version",
        provisioning_parameters=current_parameters,
        version_id=current_version,
    )

    command = start_provisioned_product_update_command.StartProvisionedProductUpdateCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        project_id=project_id_value_object.from_str("proj-123"),
        user_id=user_id_value_object.from_str("T0011AA"),
        provisioning_parameters=provisioning_parameters_value_object.from_list(requested_parameters),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
        version_id=product_version_id_value_object.from_str(new_version),
        is_auto_update=is_auto_update_value_object.IsAutoUpdateValueObject(value=False),
    )

    # ACT
    start_update.handle(
        command=command,
        publisher=mock_publisher,
        versions_qs=mock_versions_query_service,
        logger=mock_logger,
        provisioned_products_qs=mock_provisioned_products_qs,
    )

    # ASSERT
    mock_provisioned_product_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        get_provisioned_product(
            status=product_status.ProductStatus.Updating,
            version_id=current_version,
            new_version_id=new_version,
            new_version_name="1.0.0",
            provisioning_parameters=current_parameters,
            new_provisioning_parameters=new_parameters,
        ),
    )
    mock_unit_of_work.commit.assert_called_once()
    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_update_initialized.ProvisionedProductUpdateInitialized(
            provisionedProductId="pp-123", userIpAddress="127.0.0.1"
        )
    )
    mock_versions_query_service.get_product_version_distributions.assert_called_once_with(
        product_id="prod-123",
        version_id=new_version,
        region="us-east-1",
        stage=version.VersionStage.DEV,
    )
