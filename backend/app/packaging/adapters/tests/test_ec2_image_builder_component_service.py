import assertpy

from app.packaging.adapters.tests.conftest import GlobalVariables


def test_should_get_component_version_build_arn(mock_moto_calls, get_ec2_image_builder_component_srv):
    # ARRANGE
    component_id = GlobalVariables.TEST_COMPONENT_ID.value
    component_version = "1.0.0/1"

    # ACT
    response = get_ec2_image_builder_component_srv.get_build_arn(name=component_id, version=component_version)

    # ASSERT
    list_components_query_kwargs = {
        "filters": [
            {"name": "name", "values": [component_id]},
            {"name": "version", "values": [component_version]},
        ],
    }
    mock_moto_calls["ListComponents"].assert_called_once_with(**list_components_query_kwargs)
    assertpy.assert_that(response).is_equal_to(
        f"arn:aws:imagebuilder:us-east-1:1234567890:component/{component_id}/1.0.0/1"
    )


def test_should_create_component(mock_moto_calls, get_ec2_image_builder_component_srv):
    # ARRANGE
    component_id = GlobalVariables.TEST_COMPONENT_ID.value
    component_version = GlobalVariables.TEST_COMPONENT_VERSION_NAME.value
    component_description = GlobalVariables.TEST_COMPONENT_DESCRIPTION.value
    platform = GlobalVariables.TEST_PLATFORM.value
    supported_os_versions = ["Ubuntu 24"]
    s3_component_uri = f"s3://test-bucket/{component_id}/{component_version}/component.yaml"

    # ACT
    response = get_ec2_image_builder_component_srv.create(
        name=component_id,
        version=component_version,
        description=component_description,
        s3_component_uri=s3_component_uri,
        platform=platform,
        supported_os_versions=supported_os_versions,
    )

    # ASSERT
    create_component_kwargs = {
        "name": component_id,
        "semanticVersion": component_version,
        "description": component_description,
        "platform": platform,
        "supportedOsVersions": supported_os_versions,
        "uri": s3_component_uri,
    }
    mock_moto_calls["CreateComponent"].assert_called_once_with(**create_component_kwargs)
    assertpy.assert_that(response).is_equal_to(
        f"arn:aws:imagebuilder:us-east-1:1234567890:component/{component_id}/1.0.0"
    )


def test_should_delete_component(mock_moto_calls, get_ec2_image_builder_component_srv):
    # ARRANGE
    component_build_version_arn = "arn:aws:imagebuilder:us-east-1:1234567890:component/comp-1234abcd/1.0.0"

    # ACT
    get_ec2_image_builder_component_srv.delete(component_build_version_arn=component_build_version_arn)

    # ASSERT
    delete_component_kwargs = {
        "componentBuildVersionArn": component_build_version_arn,
    }
    mock_moto_calls["DeleteComponent"].assert_called_once_with(**delete_component_kwargs)
