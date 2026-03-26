from app.provisioning.domain.model import connection_option, container_details, instance_details, product_status
from app.provisioning.domain.ports import instance_management_service, parameter_service


def map_provisioned_product_instance_type_status(
    inst_dtl: instance_details.InstanceDetails,
) -> product_status.ProductStatus:
    ec2_instance_state = product_status.EC2InstanceState(inst_dtl.state.name)
    return product_status.EC2_TO_PRODUCT_STATE_MAP.get(ec2_instance_state)


def map_provisioned_product_container_type_status(
    cont_dtl: container_details.ContainerDetails,
) -> product_status.ProductStatus:
    state = product_status.TaskState(cont_dtl.state.name)
    return product_status.CONTAINER_TO_PRODUCT_STATE_MAP.get(state)


def authorize_user_ip_address(
    instance_mgmt_srv: instance_management_service.InstanceManagementService,
    parameter_srv: parameter_service.ParameterService,
    user_id: str,
    aws_account_id: str,
    region: str,
    ip_address: str,
    spoke_account_vpc_id_param_name: str,
):
    """
    Authorizes the user current IP address to access provisioned products.
    """

    # Get VPC Id in the target account and region
    vpc_id = parameter_srv.get_parameter_value(
        parameter_name=spoke_account_vpc_id_param_name,
        aws_account_id=aws_account_id,
        region=region,
        user_id=user_id,
    )

    # Get user security group ID
    user_sg_id = instance_mgmt_srv.get_user_security_group_id(
        user_id=user_id,
        aws_account_id=aws_account_id,
        region=region,
        vpc_id=vpc_id,
    )

    for option in connection_option.ConnectionOption.list():
        for rule in connection_option.CONNECTION_OPTION_TO_SECURITY_GROUP_RULES_MAP[option]:
            sg_rule_id = instance_mgmt_srv.get_user_ip_address_rule_id(
                user_id=user_id,
                aws_account_id=aws_account_id,
                region=region,
                connection_option=option,
                port=rule.from_port,
                to_port=rule.to_port,
                protocol=rule.protocol.value,
                user_sg_id=user_sg_id,
            )

            if sg_rule_id:
                instance_mgmt_srv.revoke_user_ip_address(
                    user_id=user_id,
                    aws_account_id=aws_account_id,
                    region=region,
                    sg_rule_id=sg_rule_id,
                    user_sg_id=user_sg_id,
                )

            instance_mgmt_srv.authorize_user_ip_address(
                user_id=user_id,
                aws_account_id=aws_account_id,
                region=region,
                connection_option=option,
                ip_address=ip_address,
                port=rule.from_port,
                to_port=rule.to_port,
                protocol=rule.protocol.value,
                user_sg_id=user_sg_id,
            )
