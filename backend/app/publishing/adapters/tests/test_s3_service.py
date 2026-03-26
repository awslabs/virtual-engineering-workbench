import os
import tempfile

import assertpy

from app.publishing.adapters.services import s3_file_service

fake_template = {"Key": "fake_key", "Bucket": "fake_bucket", "Body": b"0x10"}


def test_get_product_template_gets_product_template(s3_client_mock, mock_logger):
    # ARRANGE
    s3_srv = s3_file_service.S3FileService("admin", "tools_account_id", "us-east-1", "fake_bucket", mock_logger)

    # ACT & ASSERT
    with tempfile.NamedTemporaryFile() as temp_file:
        fake_template["Key"] = temp_file.name
        s3_client_mock.put_object(**fake_template)
        destination_path = s3_srv.get_template(temp_file.name, os.path.dirname(temp_file.name))
        assertpy.assert_that(destination_path).is_equal_to(temp_file.name)


def test_put_template_creates_object_in_s3(s3_client_mock, mock_logger):
    # ARRANGE
    s3_srv = s3_file_service.S3FileService("admin", "tools_account_id", "us-east-1", "fake_bucket", mock_logger)

    # ACT
    object_key = "/prod-12345abc/vers-12345abc/workbench-template.yml"
    s3_srv.put_template(object_key, b"0x10")

    # ASSERT
    response = s3_client_mock.get_object(Bucket="fake_bucket", Key=object_key)
    assertpy.assert_that(response["Body"].read()).is_equal_to(b"0x10")


def test_put_template_overwrites_object_in_s3_when_already_exists(s3_client_mock, mock_logger):
    # ARRANGE
    s3_srv = s3_file_service.S3FileService("admin", "tools_account_id", "us-east-1", "fake_bucket", mock_logger)
    object_key = "/prod-12345abc/vers-12345abc/workbench-template.yml"
    s3_srv.put_template(object_key, "0x10".encode())

    # ACT
    response = s3_client_mock.get_object(Bucket="fake_bucket", Key=object_key)
    response_text = response["Body"].read().decode("utf-8")
    assertpy.assert_that(response_text).is_equal_to("0x10")
    s3_srv.put_template(object_key, "0x12".encode())

    # ASSERT
    response = s3_client_mock.get_object(Bucket="fake_bucket", Key=object_key)
    response_text = response["Body"].read().decode("utf-8")
    assertpy.assert_that(response_text).is_equal_to("0x12")


def test_does_template_exist_returns_true_when_exists(s3_client_mock, mock_logger):
    # ARRANGE
    s3_srv = s3_file_service.S3FileService("admin", "tools_account_id", "us-east-1", "fake_bucket", mock_logger)
    s3_client_mock.put_object(Bucket="fake_bucket", Key="fake_key", Body=b"0x10")

    # ACT
    does_template_exists = s3_srv.does_template_exist(template_path="fake_key")

    # ASSERT
    assertpy.assert_that(does_template_exists).is_true()


def test_does_template_exist_returns_false_when_not_exist(s3_client_mock, mock_logger):
    # ARRANGE
    s3_srv = s3_file_service.S3FileService("admin", "tools_account_id", "us-east-1", "fake_bucket", mock_logger)

    # ACT
    does_template_exists = s3_srv.does_template_exist(template_path="fake_key")

    # ASSERT
    assertpy.assert_that(does_template_exists).is_false()


def test_get_object_returns_object_as_string(s3_client_mock, mock_logger):
    # ARRANGE
    s3_srv = s3_file_service.S3FileService("admin", "tools_account_id", "us-east-1", "fake_bucket", mock_logger)
    s3_client_mock.put_object(
        Bucket="fake_bucket",
        Key="fake_key",
        Body=b'["ami-1", "ami-2", "ami-3", "ami-4", "ami-5"]',
    )

    # ACT
    object_as_string = s3_srv.get_object("fake_key")

    # ASSERT
    assertpy.assert_that(object_as_string).is_equal_to('["ami-1", "ami-2", "ami-3", "ami-4", "ami-5"]')
