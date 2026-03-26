import assertpy
import pytest
from botocore.exceptions import ClientError

from app.packaging.adapters.exceptions import adapter_exception
from app.packaging.adapters.services import aws_recipe_version_testing_service
from app.packaging.adapters.tests.conftest import GlobalVariables
from app.packaging.domain.model.recipe import recipe_version_test_execution


def test_should_get_testing_environment_instance_type(
    mock_aws_recipe_version_testing_service, mock_security_group, mock_subnets
):
    # ARRANGE & ACT
    instance_type = mock_aws_recipe_version_testing_service.get_testing_environment_instance_type(
        architecture=GlobalVariables.TEST_ARCHITECTURE.value,
        platform=GlobalVariables.TEST_PLATFORM.value,
        os_version=GlobalVariables.TEST_OS_VERSION.value,
    )

    # ASSERT
    assertpy.assert_that(instance_type).is_equal_to(GlobalVariables.TEST_INSTANCE_TYPE.value)


def test_should_launch_testing_environment(
    mock_aws_recipe_version_testing_service,
    mock_instance_profile,
    mock_security_group,
    mock_subnets,
):
    # ARRANGE & ACT
    instance_id = mock_aws_recipe_version_testing_service.launch_testing_environment(
        image_upstream_id=GlobalVariables.TEST_AMI_ID.value,
        instance_type=GlobalVariables.TEST_INSTANCE_TYPE.value,
        volume_size=int(GlobalVariables.TEST_VOLUME_SIZE.value),
    )

    # ASSERT
    assertpy.assert_that(instance_id).matches(r"^i-[a-z0-9]{17}$")


@pytest.mark.parametrize("error_code", ["InsufficientInstanceCapacity", "Unsupported"])
def test_launch_should_retry_all_subnets_on_retryable_error(
    error_code,
    mock_aws_recipe_version_testing_service_factory,
    mock_instance_profile,
    mock_security_group,
    mock_subnets,
    mock_moto_ec2_calls,
    mock_ec2_launch_instances_call,
    mock_ec2_client,
    mock_vpc,
):
    # ARRANGE
    subnets = []
    for i, mask in enumerate(["24", "25"]):
        subnets.append(
            mock_ec2_client.create_subnet(
                CidrBlock=f"10.0.{i+100}.0/{mask}",
                VpcId=mock_vpc.get("Vpc").get("VpcId"),
                TagSpecifications=[
                    {
                        "ResourceType": "subnet",
                        "Tags": [
                            {
                                "Key": "Name",
                                "Value": f"subnet-{i}",
                            }
                        ],
                    }
                ],
            )
        )

    mock_ec2_launch_instances_call.side_effect = [
        ClientError(error_response={"Error": {"Code": error_code}}, operation_name="RunInstances"),
        {"Instances": [{"InstanceId": "i-0000000000"}]},
    ]
    mock_aws_recipe_version_testing_service = mock_aws_recipe_version_testing_service_factory(
        ami_factory_subnet_names=["subnet-0", "subnet-1"]
    )

    # ACT
    instance_id = mock_aws_recipe_version_testing_service.launch_testing_environment(
        image_upstream_id=GlobalVariables.TEST_AMI_ID.value,
        instance_type=GlobalVariables.TEST_INSTANCE_TYPE.value,
        volume_size=int(GlobalVariables.TEST_VOLUME_SIZE.value),
    )

    # ASSERT
    assertpy.assert_that(instance_id).is_equal_to("i-0000000000")

    assertpy.assert_that(mock_ec2_launch_instances_call.call_count).is_equal_to(2)

    for i, mock_call in enumerate(mock_ec2_launch_instances_call.mock_calls):
        assertpy.assert_that(mock_call.kwargs["SubnetId"]).is_equal_to(subnets[i]["Subnet"]["SubnetId"])


@pytest.mark.parametrize("error_code", ["InsufficientInstanceCapacity", "Unsupported"])
def test_launch_should_raise_when_subnets_exhausted(
    error_code,
    mock_aws_recipe_version_testing_service_factory,
    mock_instance_profile,
    mock_security_group,
    mock_subnets,
    mock_moto_ec2_calls,
    mock_ec2_launch_instances_call,
    mock_ec2_client,
    mock_vpc,
):
    # ARRANGE
    subnets = []
    for i, mask in enumerate(["24", "25"]):
        subnets.append(
            mock_ec2_client.create_subnet(
                CidrBlock=f"10.0.{i+100}.0/{mask}",
                VpcId=mock_vpc.get("Vpc").get("VpcId"),
                TagSpecifications=[
                    {
                        "ResourceType": "subnet",
                        "Tags": [
                            {
                                "Key": "Name",
                                "Value": f"subnet-{i}",
                            }
                        ],
                    }
                ],
            )
        )

    err = ClientError(error_response={"Error": {"Code": error_code}}, operation_name="RunInstances")

    mock_ec2_launch_instances_call.side_effect = [err, err]

    mock_aws_recipe_version_testing_service = mock_aws_recipe_version_testing_service_factory(
        ami_factory_subnet_names=["subnet-0", "subnet-1"]
    )

    # ACT
    with pytest.raises(adapter_exception.AdapterException) as e:
        mock_aws_recipe_version_testing_service.launch_testing_environment(
            image_upstream_id=GlobalVariables.TEST_AMI_ID.value,
            instance_type=GlobalVariables.TEST_INSTANCE_TYPE.value,
            volume_size=int(GlobalVariables.TEST_VOLUME_SIZE.value),
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        "Unable to launch a test EC2 instance - all subnets have been tried."
    )


def test_should_raise_an_exception_with_no_subnets_available(
    mock_aws_recipe_version_testing_service, mock_vpc, mock_security_group
):
    # ARRANGE & ACT
    with pytest.raises(adapter_exception.AdapterException) as exec_info:
        mock_aws_recipe_version_testing_service.launch_testing_environment(
            image_upstream_id=GlobalVariables.TEST_AMI_ID.value,
            instance_type=GlobalVariables.TEST_INSTANCE_TYPE.value,
            volume_size=int(GlobalVariables.TEST_VOLUME_SIZE.value),
        )

    # ASSERT
    assertpy.assert_that(exec_info.value.args[0]).is_equal_to(
        f"No subnets found with id: {GlobalVariables.TEST_AMI_FACTORY_SUBNET_NAMES.value[0]}."
    )


def test_should_raise_an_exception_with_no_security_groups_available(
    mock_aws_recipe_version_testing_service, mock_subnets
):
    # ARRANGE & ACT
    with pytest.raises(adapter_exception.AdapterException) as exec_info:
        mock_aws_recipe_version_testing_service.launch_testing_environment(
            image_upstream_id=GlobalVariables.TEST_AMI_ID.value,
            instance_type=GlobalVariables.TEST_INSTANCE_TYPE.value,
            volume_size=int(GlobalVariables.TEST_VOLUME_SIZE.value),
        )

    # ASSERT
    assertpy.assert_that(exec_info.value.args[0]).is_equal_to(
        f"Security group with name {GlobalVariables.TEST_INSTANCE_SECURITY_GROUP_NAME.value} not found"
    )


def test_should_get_testing_environment_creation_time(
    mock_aws_recipe_version_testing_service, mock_instance_profile, mock_ec2_instance
):
    # ARRANGE
    instance_id = mock_ec2_instance.get("Instances")[0].get("InstanceId")

    # ACT
    response = mock_aws_recipe_version_testing_service.get_testing_environment_creation_time(instance_id=instance_id)

    # ASSERT
    assertpy.assert_that(response).is_equal_to("2023-10-13 00:00:00")


def test_should_get_testing_environment_status(
    mock_aws_recipe_version_testing_service, mock_moto_calls, mock_ec2_instance
):
    # ARRANGE
    instance_id = mock_ec2_instance.get("Instances")[0].get("InstanceId")

    # ARRANGE & ACT
    response = mock_aws_recipe_version_testing_service.get_testing_environment_status(instance_id=instance_id)

    # ASSERT
    assertpy.assert_that(response).is_equal_to(
        recipe_version_test_execution.RecipeVersionTestExecutionInstanceStatus.Connected
    )


def test_should_setup_testing_environment(
    mock_aws_recipe_version_testing_service,
    mock_ssm_client,
    mock_system_configuration_mapping,
):
    # ARRANGE & ACT
    command_id = mock_aws_recipe_version_testing_service.setup_testing_environment(
        architecture=GlobalVariables.TEST_ARCHITECTURE.value,
        instance_id=GlobalVariables.TEST_INSTANCE_ID.value,
        os_version=GlobalVariables.TEST_OS_VERSION.value,
        platform=GlobalVariables.TEST_PLATFORM.value,
    )
    response = mock_ssm_client.get_command_invocation(
        CommandId=command_id,
        InstanceId=GlobalVariables.TEST_INSTANCE_ID.value,
    )

    # ASSERT
    assertpy.assert_that(response.get("DocumentName")).is_equal_to(
        mock_system_configuration_mapping.get(GlobalVariables.TEST_PLATFORM.value)
        .get(GlobalVariables.TEST_ARCHITECTURE.value)
        .get(GlobalVariables.TEST_OS_VERSION.value)
        .get(aws_recipe_version_testing_service.SystemConfigurationMappingAttributes.COMMAND_SSM_DOCUMENT_NAME)
    )
    assertpy.assert_that(response.get("InstanceId")).is_equal_to(GlobalVariables.TEST_INSTANCE_ID.value)


def test_should_get_testing_command_status(mock_aws_recipe_version_testing_service, mock_ssm_client, mock_command_id):
    # ARRANGE & ACT
    response = mock_aws_recipe_version_testing_service.get_testing_command_status(
        command_id=mock_command_id, instance_id=GlobalVariables.TEST_INSTANCE_ID.value
    )

    # ASSERT
    assertpy.assert_that(response).is_equal_to(
        recipe_version_test_execution.RecipeVersionTestExecutionCommandStatus.Success
    )


def test_should_run_testing(
    mock_aws_recipe_version_testing_service,
    mock_ssm_client,
    mock_system_configuration_mapping,
):
    # ARRANGE
    recipe_version_component_arn = "arn:aws:imagebuilder:us-east-1:123456789123:component/comp-12345/1.0.0/1"

    # ACT
    command_id = mock_aws_recipe_version_testing_service.run_testing(
        recipe_version_component_arn=recipe_version_component_arn,
        architecture=GlobalVariables.TEST_ARCHITECTURE.value,
        instance_id=GlobalVariables.TEST_INSTANCE_ID.value,
        os_version=GlobalVariables.TEST_OS_VERSION.value,
        platform=GlobalVariables.TEST_PLATFORM.value,
        recipe_id=GlobalVariables.TEST_RECIPE_ID,
        recipe_version_id=GlobalVariables.TEST_RECIPE_VERSION_ID,
    )
    response = mock_ssm_client.get_command_invocation(
        CommandId=command_id,
        InstanceId=GlobalVariables.TEST_INSTANCE_ID.value,
    )

    # ASSERT
    assertpy.assert_that(response.get("DocumentName")).is_equal_to(
        mock_system_configuration_mapping.get(GlobalVariables.TEST_PLATFORM.value)
        .get(GlobalVariables.TEST_ARCHITECTURE.value)
        .get(GlobalVariables.TEST_OS_VERSION.value)
        .get(aws_recipe_version_testing_service.SystemConfigurationMappingAttributes.COMMAND_SSM_DOCUMENT_NAME)
    )
    assertpy.assert_that(response.get("InstanceId")).is_equal_to(GlobalVariables.TEST_INSTANCE_ID.value)


def test_should_teardown_testing_environment(
    mock_aws_recipe_version_testing_service,
    mock_ec2_client,
    mock_instance_profile,
    mock_ec2_instance,
):
    # ARRANGE
    instance_id = mock_ec2_instance.get("Instances")[0].get("InstanceId")

    # ACT
    response = mock_aws_recipe_version_testing_service.teardown_testing_environment(instance_id=instance_id)
    instance = mock_ec2_client.describe_instances(InstanceIds=[instance_id])

    # ASSERT
    print(instance)
    assertpy.assert_that(instance.get("Reservations")[0].get("Instances")[0].get("ImageId")).is_equal_to(
        GlobalVariables.TEST_AMI_ID.value
    )
    assertpy.assert_that(instance.get("Reservations")[0].get("Instances")[0].get("InstanceType")).is_equal_to(
        GlobalVariables.TEST_INSTANCE_TYPE.value
    )
    assertpy.assert_that(
        instance.get("Reservations")[0].get("Instances")[0].get("SecurityGroups")[0].get("GroupName")
    ).is_equal_to(GlobalVariables.TEST_INSTANCE_SECURITY_GROUP_NAME.value)
    assertpy.assert_that(instance.get("Reservations")[0].get("Instances")[0].get("State").get("Name")).is_equal_to(
        "terminated"
    )
    assertpy.assert_that(response).is_none()
