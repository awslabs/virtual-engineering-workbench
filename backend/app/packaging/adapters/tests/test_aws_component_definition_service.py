import base64

import assertpy
import pytest

from app.packaging.adapters.services import aws_component_definition_service
from app.packaging.adapters.tests.conftest import GlobalVariables


@pytest.fixture()
def get_aws_component_definition_srv():
    """Fixture for AWSComponentDefinitionService."""
    return aws_component_definition_service.AWSComponentDefinitionService(
        admin_role=GlobalVariables.TEST_ADMIN_ROLE.value,
        ami_factory_aws_account_id=GlobalVariables.AWS_ACCOUNT_ID.value,
        boto_session=None,
        bucket_name=GlobalVariables.FAKE_BUCKET_NAME.value,
        region=GlobalVariables.TEST_REGION.value,
    )


def test_service_initialization(get_aws_component_definition_srv):
    """Test that the service initializes correctly."""
    service = get_aws_component_definition_srv

    assertpy.assert_that(service._admin_role).is_equal_to(GlobalVariables.TEST_ADMIN_ROLE.value)
    assertpy.assert_that(service._ami_factory_aws_account_id).is_equal_to(GlobalVariables.AWS_ACCOUNT_ID.value)
    assertpy.assert_that(service._region).is_equal_to(GlobalVariables.TEST_REGION.value)
    assertpy.assert_that(service._bucket_name).is_equal_to(GlobalVariables.FAKE_BUCKET_NAME.value)


def test_upload_maintains_backward_compatibility_without_vector_storage(
    mock_s3_client, get_aws_component_definition_srv
):
    """Test that upload method works without vector storage integration."""
    service = get_aws_component_definition_srv

    component_id = GlobalVariables.TEST_COMPONENT_ID.value
    component_version = GlobalVariables.TEST_COMPONENT_VERSION_NAME.value
    component_definition = b"name: TestComponent\ndescription: Test component"

    s3_uri = service.upload(
        component_id=component_id,
        component_version=component_version,
        component_definition=component_definition,
    )

    assertpy.assert_that(s3_uri).starts_with("s3://")
    assertpy.assert_that(s3_uri).contains(component_id)


def test_upload_maintains_backward_compatibility(mock_s3_client, get_aws_component_definition_srv):
    """Test that upload method maintains backward compatibility with existing S3 functionality."""
    component_id = GlobalVariables.TEST_COMPONENT_ID.value
    component_version = f"{GlobalVariables.TEST_COMPONENT_VERSION_NAME.value}-rc.1"
    object_key = f"{component_id}/{GlobalVariables.TEST_COMPONENT_VERSION_NAME.value}/component.yaml"

    get_aws_component_definition_srv.upload(
        component_id=component_id,
        component_version=component_version,
        component_definition=b"component definition",
    )

    object = mock_s3_client.get_object(Bucket=GlobalVariables.FAKE_BUCKET_NAME.value, Key=object_key)
    object_tags = mock_s3_client.get_object_tagging(Bucket=GlobalVariables.FAKE_BUCKET_NAME.value, Key=object_key)

    assertpy.assert_that(object.get("Body").read()).is_equal_to(b"component definition")
    assertpy.assert_that(object.get("TagCount")).is_equal_to(1)
    assertpy.assert_that(object_tags["TagSet"][0]["Key"]).is_equal_to("release-candidate")
    assertpy.assert_that(object_tags["TagSet"][0]["Value"]).is_equal_to("rc.1")


def test_get_component_version_definition_maintains_compatibility(
    get_mock_component_version, get_aws_component_definition_srv
):
    """Test that get_component_version_definition maintains backward compatibility."""
    component_version_object = get_mock_component_version()
    yaml_definition_obj, yaml_definition_b64 = get_aws_component_definition_srv.get_component_version_definition(
        component_version=component_version_object
    )

    assertpy.assert_that(yaml_definition_obj).is_not_empty()
    assertpy.assert_that(yaml_definition_obj).is_equal_to({"Name": "Test component"})
    assertpy.assert_that(yaml_definition_b64).is_not_empty()
    assertpy.assert_that(yaml_definition_b64).is_equal_to(
        base64.b64encode(GlobalVariables.TEST_COMPONENT_VERSION_YAML_DEFINITION.value.encode("utf-8")).decode("utf-8")
    )
