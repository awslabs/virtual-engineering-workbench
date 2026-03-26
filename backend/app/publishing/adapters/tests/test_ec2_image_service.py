import assertpy
from mypy_boto3_ec2 import client

from app.publishing.adapters.services import ec2_image_service


def test_copy_ami_copies_ami(mock_ec2: client.EC2Client):
    # ARRANGE
    ec2_img_srv = ec2_image_service.EC2ImageService("ImageSrvRole", "123456789012", "test-key", "us-east-1")
    original_ami_id = mock_ec2.describe_images(Owners=["amazon"])["Images"][0]["ImageId"]

    # ACT
    copied_ami_id = ec2_img_srv.copy_ami("eu-west-3", original_ami_id, "Great AMI", "Great AMI description")

    # ASSERT
    assertpy.assert_that(copied_ami_id).is_not_none()


def test_share_ami_shares_ami(mock_moto_calls):
    # ARRANGE
    ec2_img_srv = ec2_image_service.EC2ImageService("ImageSrvRole", "123456789012", "test-key", "us-east-1")

    # ACT
    ec2_img_srv.share_ami("eu-west-3", "ami-54321", "123456789012")

    # ASSERT
    mock_moto_calls["ModifyImageAttribute"].assert_called_once_with(
        ImageId="ami-54321", LaunchPermission={"Add": [{"UserId": "123456789012"}]}
    )


def test_grant_kms_access_creates_grant_for_encrypted_snapshots(mock_moto_calls):
    # ARRANGE
    ec2_img_srv = ec2_image_service.EC2ImageService("ImageSrvRole", "123456789012", "test-key", "us-east-1")

    # ACT
    ec2_img_srv.grant_kms_access("eu-west-3", "ami-12345", "322234948118")

    # ASSERT
    mock_moto_calls["DescribeImages"].assert_called_once_with(ImageIds=["ami-12345"], Owners=["self"])
    mock_moto_calls["CreateGrant"].assert_called_once_with(
        KeyId="string",
        GranteePrincipal="arn:aws:iam::322234948118:root",
        Operations=["Decrypt", "DescribeKey", "CreateGrant", "GenerateDataKey", "ReEncryptFrom", "ReEncryptTo"],
    )


def test_get_copied_ami_status(mock_ec2: client.EC2Client):
    # ARRANGE
    ec2_img_srv = ec2_image_service.EC2ImageService("ImageSrvRole", "123456789012", "test-key", "us-east-1")
    copied_ami_id = mock_ec2.describe_images(Owners=["amazon"])["Images"][0]["ImageId"]

    # ACT
    copied_ami_status = ec2_img_srv.get_copied_ami_status(copied_ami_id, "eu-west-3")
    # ASSERT
    assertpy.assert_that(copied_ami_status).is_not_none()
    assertpy.assert_that(copied_ami_status).is_equal_to("available")
