import assertpy
import pytest

from app.provisioning.domain.command_handlers.product_provisioning import authorize_user_ip_address
from app.provisioning.domain.commands.product_provisioning import authorize_user_ip_address_command
from app.provisioning.domain.exceptions import domain_exception
from app.provisioning.domain.model import connection_option
from app.provisioning.domain.value_objects import (
    ip_address_value_object,
    provisioned_product_id_value_object,
    user_id_value_object,
)


@pytest.mark.parametrize("authorize_user_ip_address_param_value", [True, False])
def test_authorize_user_ip_address_should_authorize_user_ip_address(
    mock_logger,
    mock_provisioned_products_qs,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
    authorize_user_ip_address_param_value,
):
    # ARRANGE
    command = authorize_user_ip_address_command.AuthorizeUserIpAddressCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
        user_id=user_id_value_object.from_str("T0011AA"),
    )
    mock_instance_mgmt_srv.get_user_security_group_id.return_value = "sg-12345"

    # ACT
    authorize_user_ip_address.handle(
        command=command,
        virtual_targets_qs=mock_provisioned_products_qs,
        parameter_srv=mock_parameter_srv,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        logger=mock_logger,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        authorize_user_ip_address_param_value=authorize_user_ip_address_param_value,
    )

    # ASSERT
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
                    user_sg_id="sg-12345",
                )
    else:
        mock_instance_mgmt_srv.authorize_user_ip_address.assert_not_called()


def test_authorize_user_ip_address_should_not_authorize_user_ip_address_if_an_exception_is_raised(
    mock_logger,
    mock_provisioned_products_qs,
    mock_parameter_srv,
    mock_instance_mgmt_srv,
):
    # ARRANGE
    command = authorize_user_ip_address_command.AuthorizeUserIpAddressCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
        user_id=user_id_value_object.from_str("T0011AB"),
    )

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        authorize_user_ip_address.handle(
            command=command,
            virtual_targets_qs=mock_provisioned_products_qs,
            parameter_srv=mock_parameter_srv,
            instance_mgmt_srv=mock_instance_mgmt_srv,
            logger=mock_logger,
            spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
            authorize_user_ip_address_param_value=True,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        "User T0011AB is not authorized to authorize IP address for provisioned product pp-123"
    )
    mock_instance_mgmt_srv.authorize_user_ip_address.assert_not_called()
