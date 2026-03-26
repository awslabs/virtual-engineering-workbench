import assertpy
import pytest

from app.packaging.adapters.exceptions import adapter_exception
from app.packaging.adapters.tests.conftest import GlobalVariables


def test_get_list_allowed_build_instance_types_for_amd64(
    get_test_ec2_image_builder_pipeline_srv, mock_pipelines_configuration_mapping
):
    # ARRANGE & ACT
    response = get_test_ec2_image_builder_pipeline_srv.get_pipeline_allowed_build_instance_types(
        architecture=GlobalVariables.SUPPORTED_ARCHITECTURES.value[0]
    )
    # ASSERT
    assertpy.assert_that(len(response)).is_equal_to(4)
    assertpy.assert_that(response).contains("m8a.2xlarge")


def test_get_list_allowed_build_instance_types_for_arm64(
    get_test_ec2_image_builder_pipeline_srv, mock_pipelines_configuration_mapping
):
    # ARRANGE & ACT
    response = get_test_ec2_image_builder_pipeline_srv.get_pipeline_allowed_build_instance_types(
        architecture=GlobalVariables.SUPPORTED_ARCHITECTURES.value[1]
    )
    # ASSERT
    assertpy.assert_that(len(response)).is_equal_to(2)
    assertpy.assert_that(response).contains("m8g.2xlarge")


def test_get_list_allowed_build_instance_types_for_unsupported_arch(
    get_test_ec2_image_builder_pipeline_srv, mock_pipelines_configuration_mapping
):
    # ARRANGE & ACT
    with pytest.raises(adapter_exception.AdapterException) as exec_info:
        get_test_ec2_image_builder_pipeline_srv.get_pipeline_allowed_build_instance_types(architecture="RISC-V")
    # ASSERT
    assertpy.assert_that(exec_info.value.args[0]).is_equal_to(
        "No pipelines configuration found for architecture: RISC-V"
    )


def test_should_create_distribution_configuration(get_test_ec2_image_builder_pipeline_srv, mock_moto_calls):
    # ARRANGE
    description = GlobalVariables.TEST_PIPELINE_DESCRIPTION.value
    image_tags = {"Name": "Test name"}
    pipeline_id = GlobalVariables.TEST_PIPELINE_ID.value

    # ACT
    response = get_test_ec2_image_builder_pipeline_srv.create_distribution_config(
        description=description, image_tags=image_tags, name=pipeline_id
    )

    # ASSERT
    mock_moto_calls["CreateDistributionConfiguration"].assert_called_once_with(
        description=description,
        distributions=[
            {
                "amiDistributionConfiguration": {
                    "amiTags": image_tags,
                    "kmsKeyId": f"arn:aws:kms:{GlobalVariables.TEST_REGION.value}:{GlobalVariables.TEST_AMI_FACTORY_AWS_ACCOUNT_ID.value}:alias/{GlobalVariables.TEST_IMAGE_KEY_NAME.value}",
                },
                "region": GlobalVariables.TEST_REGION.value,
            },
        ],
        name=pipeline_id,
    )
    assertpy.assert_that(response).is_equal_to(GlobalVariables.TEST_PIPELINE_DISTRIBUTION_CONFIG_ARN.value)


def test_should_create_infrastructure_configuration(
    get_test_ec2_image_builder_pipeline_srv, mock_moto_calls, mock_security_group, mock_subnets
):
    # ARRANGE
    description = GlobalVariables.TEST_PIPELINE_DESCRIPTION.value
    instance_types = ["m8a.4xlarge", "m8i.4xlarge"]
    pipeline_id = GlobalVariables.TEST_PIPELINE_ID.value

    # ACT
    response = get_test_ec2_image_builder_pipeline_srv.create_infrastructure_config(
        description=description, instance_types=instance_types, name=pipeline_id
    )

    # ASSERT
    mock_moto_calls["CreateInfrastructureConfiguration"].assert_called_once_with(
        description=description,
        instanceMetadataOptions={"httpTokens": "required"},
        instanceProfileName=GlobalVariables.TEST_INSTANCE_PROFILE_NAME.value,
        instanceTypes=instance_types,
        name=pipeline_id,
        securityGroupIds=[mock_security_group.get("GroupId")],
        snsTopicArn=GlobalVariables.TEST_PIPELINE_SNS_TOPIC_ARN.value,
        subnetId=mock_subnets.get("Subnet").get("SubnetId"),
    )
    assertpy.assert_that(response).is_equal_to(GlobalVariables.TEST_PIPELINE_INFRASTRUCTURE_CONFIG_ARN.value)


def test_should_raise_an_exception_with_no_subnets_available(get_test_ec2_image_builder_pipeline_srv, mock_vpc):
    # ARRANGE
    description = GlobalVariables.TEST_PIPELINE_DESCRIPTION.value
    instance_types = ["m8a.4xlarge", "m8i.4xlarge"]
    pipeline_id = GlobalVariables.TEST_PIPELINE_ID.value

    # ACT
    with pytest.raises(adapter_exception.AdapterException) as exec_info:
        get_test_ec2_image_builder_pipeline_srv.create_infrastructure_config(
            description=description, instance_types=instance_types, name=pipeline_id
        )

    # ASSERT
    assertpy.assert_that(exec_info.value.args[0]).is_equal_to(
        f"No subnets found with id: {GlobalVariables.TEST_AMI_FACTORY_SUBNET_NAMES.value[0]}."
    )


def test_should_raise_an_exception_with_no_security_groups_available(
    get_test_ec2_image_builder_pipeline_srv, mock_subnets
):
    # ARRANGE
    description = GlobalVariables.TEST_PIPELINE_DESCRIPTION.value
    instance_types = ["m8a.4xlarge", "m8i.4xlarge"]
    pipeline_id = GlobalVariables.TEST_PIPELINE_ID.value

    # ACT
    with pytest.raises(adapter_exception.AdapterException) as exec_info:
        get_test_ec2_image_builder_pipeline_srv.create_infrastructure_config(
            description=description, instance_types=instance_types, name=pipeline_id
        )

    # ASSERT
    assertpy.assert_that(exec_info.value.args[0]).is_equal_to(
        f"Security group with name {GlobalVariables.TEST_INSTANCE_SECURITY_GROUP_NAME.value} not found."
    )


def test_should_create_pipeline(get_test_ec2_image_builder_pipeline_srv, mock_moto_calls):
    # ARRANGE
    description = GlobalVariables.TEST_PIPELINE_DESCRIPTION.value
    pipeline_id = GlobalVariables.TEST_PIPELINE_ID.value
    schedule = GlobalVariables.TEST_PIPELINE_SCHEDULE.value

    # ACT
    response = get_test_ec2_image_builder_pipeline_srv.create_pipeline(
        description=description,
        distribution_config_arn=GlobalVariables.TEST_PIPELINE_DISTRIBUTION_CONFIG_ARN.value,
        infrastructure_config_arn=GlobalVariables.TEST_PIPELINE_INFRASTRUCTURE_CONFIG_ARN.value,
        name=pipeline_id,
        recipe_version_arn=GlobalVariables.TEST_IMAGE_RECIPE_ARN.value,
        schedule=schedule,
    )

    # ASSERT
    mock_moto_calls["CreateImagePipeline"].assert_called_once_with(
        description=description,
        distributionConfigurationArn=GlobalVariables.TEST_PIPELINE_DISTRIBUTION_CONFIG_ARN.value,
        imageRecipeArn=GlobalVariables.TEST_IMAGE_RECIPE_ARN.value,
        infrastructureConfigurationArn=GlobalVariables.TEST_PIPELINE_INFRASTRUCTURE_CONFIG_ARN.value,
        name=pipeline_id,
        schedule={
            "scheduleExpression": f"cron({schedule})",
            "pipelineExecutionStartCondition": "EXPRESSION_MATCH_ONLY",
        },
    )
    assertpy.assert_that(response).is_equal_to(GlobalVariables.TEST_PIPELINE_ARN.value)


def test_should_delete_distribution_configuration(get_test_ec2_image_builder_pipeline_srv, mock_moto_calls):
    # ARRANGE & ACT
    get_test_ec2_image_builder_pipeline_srv.delete_distribution_config(
        distribution_config_arn=GlobalVariables.TEST_PIPELINE_DISTRIBUTION_CONFIG_ARN.value
    )

    # ASSERT
    mock_moto_calls["DeleteDistributionConfiguration"].assert_called_once_with(
        distributionConfigurationArn=GlobalVariables.TEST_PIPELINE_DISTRIBUTION_CONFIG_ARN.value
    )


def test_should_delete_infrastructure_configuration(get_test_ec2_image_builder_pipeline_srv, mock_moto_calls):
    # ARRANGE &  ACT
    get_test_ec2_image_builder_pipeline_srv.delete_infrastructure_config(
        infrastructure_config_arn=GlobalVariables.TEST_PIPELINE_INFRASTRUCTURE_CONFIG_ARN.value
    )

    # ASSERT
    mock_moto_calls["DeleteInfrastructureConfiguration"].assert_called_once_with(
        infrastructureConfigurationArn=GlobalVariables.TEST_PIPELINE_INFRASTRUCTURE_CONFIG_ARN.value
    )


def test_should_delete_pipeline(get_test_ec2_image_builder_pipeline_srv, mock_moto_calls):
    # ARRANGE & ACT
    get_test_ec2_image_builder_pipeline_srv.delete_pipeline(pipeline_arn=GlobalVariables.TEST_PIPELINE_ARN.value)

    # ASSERT
    mock_moto_calls["DeleteImagePipeline"].assert_called_once_with(
        imagePipelineArn=GlobalVariables.TEST_PIPELINE_ARN.value
    )


def test_should_start_pipeline_execution(get_test_ec2_image_builder_pipeline_srv, mock_moto_calls):
    # ARRANGE
    pipeline_id = GlobalVariables.TEST_PIPELINE_ID.value

    # ACT
    response = get_test_ec2_image_builder_pipeline_srv.start_pipeline_execution(
        pipeline_arn=(
            f"arn:aws:imagebuilder:{GlobalVariables.TEST_REGION.value}:"
            f"{GlobalVariables.TEST_AMI_FACTORY_AWS_ACCOUNT_ID.value}:image-pipeline/{pipeline_id}"
        )
    )

    # ASSERT
    mock_moto_calls["StartImagePipelineExecution"].assert_called_once_with(
        imagePipelineArn=(
            f"arn:aws:imagebuilder:{GlobalVariables.TEST_REGION.value}:"
            f"{GlobalVariables.TEST_AMI_FACTORY_AWS_ACCOUNT_ID.value}:image-pipeline/{pipeline_id}"
        )
    )
    assertpy.assert_that(response).is_equal_to(
        (
            f"arn:aws:imagebuilder:{GlobalVariables.TEST_REGION.value}:"
            f"{GlobalVariables.TEST_AMI_FACTORY_AWS_ACCOUNT_ID.value}:"
            f"image/{GlobalVariables.TEST_RECIPE_NAME.value}/{GlobalVariables.TEST_RECIPE_VERSION_NAME.value}/1"
        )
    )


def test_should_update_distribution_configuration(get_test_ec2_image_builder_pipeline_srv, mock_moto_calls):
    # ARRANGE
    description = GlobalVariables.TEST_PIPELINE_DESCRIPTION.value
    image_tags = {"Name": "Test name"}

    # ACT
    response = get_test_ec2_image_builder_pipeline_srv.update_distribution_config(
        description=description,
        distribution_config_arn=GlobalVariables.TEST_PIPELINE_DISTRIBUTION_CONFIG_ARN.value,
        image_tags=image_tags,
    )

    # ASSERT
    mock_moto_calls["UpdateDistributionConfiguration"].assert_called_once_with(
        description=description,
        distributionConfigurationArn=GlobalVariables.TEST_PIPELINE_DISTRIBUTION_CONFIG_ARN.value,
        distributions=[
            {
                "amiDistributionConfiguration": {
                    "amiTags": image_tags,
                    "kmsKeyId": f"arn:aws:kms:{GlobalVariables.TEST_REGION.value}:{GlobalVariables.TEST_AMI_FACTORY_AWS_ACCOUNT_ID.value}:alias/{GlobalVariables.TEST_IMAGE_KEY_NAME.value}",
                },
                "region": GlobalVariables.TEST_REGION.value,
            },
        ],
    )
    assertpy.assert_that(response).is_equal_to(GlobalVariables.TEST_PIPELINE_DISTRIBUTION_CONFIG_ARN.value)


def test_should_update_infrastructure_configuration(
    get_test_ec2_image_builder_pipeline_srv, mock_moto_calls, mock_security_group, mock_subnets
):
    # ARRANGE
    description = GlobalVariables.TEST_PIPELINE_DESCRIPTION.value
    instance_types = ["m8a.4xlarge", "m8i.4xlarge"]

    # ACT
    response = get_test_ec2_image_builder_pipeline_srv.update_infrastructure_config(
        description=description,
        infrastructure_config_arn=GlobalVariables.TEST_PIPELINE_INFRASTRUCTURE_CONFIG_ARN.value,
        instance_types=instance_types,
    )

    # ASSERT
    mock_moto_calls["UpdateInfrastructureConfiguration"].assert_called_once_with(
        description=description,
        infrastructureConfigurationArn=GlobalVariables.TEST_PIPELINE_INFRASTRUCTURE_CONFIG_ARN.value,
        instanceMetadataOptions={"httpTokens": "required"},
        instanceProfileName=GlobalVariables.TEST_INSTANCE_PROFILE_NAME.value,
        instanceTypes=instance_types,
        securityGroupIds=[mock_security_group.get("GroupId")],
        snsTopicArn=GlobalVariables.TEST_PIPELINE_SNS_TOPIC_ARN.value,
        subnetId=mock_subnets.get("Subnet").get("SubnetId"),
    )
    assertpy.assert_that(response).is_equal_to(
        GlobalVariables.TEST_PIPELINE_INFRASTRUCTURE_CONFIG_ARN.value,
    )


def test_should_update_pipeline(get_test_ec2_image_builder_pipeline_srv, mock_moto_calls):
    # ARRANGE
    description = GlobalVariables.TEST_PIPELINE_DESCRIPTION.value
    schedule = GlobalVariables.TEST_PIPELINE_SCHEDULE.value

    # ACT
    response = get_test_ec2_image_builder_pipeline_srv.update_pipeline(
        description=description,
        distribution_config_arn=GlobalVariables.TEST_PIPELINE_DISTRIBUTION_CONFIG_ARN.value,
        infrastructure_config_arn=GlobalVariables.TEST_PIPELINE_INFRASTRUCTURE_CONFIG_ARN.value,
        pipeline_arn=GlobalVariables.TEST_PIPELINE_ARN.value,
        recipe_version_arn=GlobalVariables.TEST_RECIPE_VERSION_ARN.value,
        schedule=schedule,
    )

    # ASSERT
    mock_moto_calls["UpdateImagePipeline"].assert_called_once_with(
        description=description,
        distributionConfigurationArn=GlobalVariables.TEST_PIPELINE_DISTRIBUTION_CONFIG_ARN.value,
        imagePipelineArn=GlobalVariables.TEST_PIPELINE_ARN.value,
        imageRecipeArn=GlobalVariables.TEST_RECIPE_VERSION_ARN.value,
        infrastructureConfigurationArn=GlobalVariables.TEST_PIPELINE_INFRASTRUCTURE_CONFIG_ARN.value,
        schedule={
            "scheduleExpression": f"cron({schedule})",
            "pipelineExecutionStartCondition": "EXPRESSION_MATCH_ONLY",
        },
    )
    assertpy.assert_that(response).is_equal_to(
        GlobalVariables.TEST_PIPELINE_ARN.value,
    )
