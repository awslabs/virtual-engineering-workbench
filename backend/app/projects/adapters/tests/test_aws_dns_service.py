import assertpy
import pytest

from app.projects.adapters.exceptions.adapter_exception import AdapterException
from app.projects.adapters.tests.conftest import GlobalVariables


def test_associate_vpc_with_zone_should_succeed(mock_aws_dns_service, mock_route53):
    # ARRANGE
    zone_id = (
        mock_route53.create_hosted_zone(
            CallerReference=f"{GlobalVariables.DNS_NAME.value}-{GlobalVariables.VPC_ID.value}-{GlobalVariables.VPC_REGION.value}",
            HostedZoneConfig={
                "Comment": GlobalVariables.COMMENT.value,
                "PrivateZone": True,
            },
            Name=GlobalVariables.DNS_NAME.value,
            VPC={"VPCId": GlobalVariables.VPC_ID.value, "VPCRegion": GlobalVariables.VPC_REGION.value},
        )
        .get("HostedZone")
        .get("Id")
    )

    # ACT
    result = mock_aws_dns_service.associate_vpc_with_zone(
        vpc_id="vpc-5f678900a1b2c3d4e",
        vpc_region=GlobalVariables.VPC_REGION.value,
        zone_id=zone_id,
    )

    # ASSERT
    assertpy.assert_that(result).is_none()


def test_create_dns_record_should_succeed(mock_aws_dns_service, mock_route53):
    # ARRANGE
    name, ttl, type, value = f"www.{GlobalVariables.DNS_NAME.value}", 300, "A", "127.0.0.1"
    zone_id = (
        mock_route53.create_hosted_zone(
            CallerReference=f"{GlobalVariables.DNS_NAME.value}-{GlobalVariables.VPC_ID.value}-{GlobalVariables.VPC_REGION.value}",
            HostedZoneConfig={
                "Comment": GlobalVariables.COMMENT.value,
                "PrivateZone": True,
            },
            Name=GlobalVariables.DNS_NAME.value,
            VPC={"VPCId": GlobalVariables.VPC_ID.value, "VPCRegion": GlobalVariables.VPC_REGION.value},
        )
        .get("HostedZone")
        .get("Id")
    )

    # ACT
    result = mock_aws_dns_service.create_dns_record(
        name=name,
        ttl=ttl,
        type=type,
        value=value,
        zone_id=zone_id,
    )

    # ASSERT
    assertpy.assert_that(result).is_none()


def test_create_private_zone_should_return_zone_id(mock_aws_dns_service):
    # ARRANGE & ACT
    zone_id = mock_aws_dns_service.create_private_zone(
        comment=GlobalVariables.COMMENT.value,
        dns_name=GlobalVariables.DNS_NAME.value,
        vpc_id=GlobalVariables.VPC_ID.value,
        vpc_region=GlobalVariables.VPC_REGION.value,
    )

    # ASSERT
    assertpy.assert_that(zone_id).is_not_none()


def test_is_vpc_associated_with_zone_should_return_false_when_not_associated(mock_aws_dns_service):
    # ARRANGE
    mock_aws_dns_service.create_private_zone(
        comment=GlobalVariables.COMMENT.value,
        dns_name=GlobalVariables.DNS_NAME.value,
        vpc_id=GlobalVariables.VPC_ID.value,
        vpc_region=GlobalVariables.VPC_REGION.value,
    )

    # ACT
    result = mock_aws_dns_service.is_vpc_associated_with_zone(
        dns_name=GlobalVariables.DNS_NAME.value,
        vpc_id="vpc-5f678900a1b2c3d4e",
        vpc_region=GlobalVariables.VPC_REGION.value,
    )

    # ASSERT
    assertpy.assert_that(result).is_false()


def test_is_vpc_associated_with_zone_should_return_true_when_associated(mock_aws_dns_service, mock_route53):
    # ARRANGE
    vpc_2_id = "vpc-5f678900a1b2c3d4e"
    zone_id = mock_aws_dns_service.create_private_zone(
        comment=GlobalVariables.COMMENT.value,
        dns_name=GlobalVariables.DNS_NAME.value,
        vpc_id=GlobalVariables.VPC_ID.value,
        vpc_region=GlobalVariables.VPC_REGION.value,
    )

    mock_aws_dns_service.associate_vpc_with_zone(
        vpc_id=vpc_2_id,
        vpc_region=GlobalVariables.VPC_REGION.value,
        zone_id=zone_id,
    )

    # ACT
    result_1 = mock_aws_dns_service.is_vpc_associated_with_zone(
        dns_name=GlobalVariables.DNS_NAME.value,
        vpc_id=GlobalVariables.VPC_ID.value,
        vpc_region=GlobalVariables.VPC_REGION.value,
    )
    result_2 = mock_aws_dns_service.is_vpc_associated_with_zone(
        dns_name=GlobalVariables.DNS_NAME.value,
        vpc_id=vpc_2_id,
        vpc_region=GlobalVariables.VPC_REGION.value,
    )

    # ASSERT
    assertpy.assert_that(result_1).is_true()
    assertpy.assert_that(result_2).is_true()


def test_get_zone_id_should_raise_exception_when_multiple_zones_exists(mock_aws_dns_service, mock_route53):
    # ARRANGE
    for _ in range(2):
        mock_route53.create_hosted_zone(
            CallerReference=f"{GlobalVariables.DNS_NAME.value}-{GlobalVariables.VPC_ID.value}-{GlobalVariables.VPC_REGION.value}",
            HostedZoneConfig={
                "Comment": GlobalVariables.COMMENT.value,
                "PrivateZone": True,
            },
            Name=GlobalVariables.DNS_NAME.value,
            VPC={"VPCId": GlobalVariables.VPC_ID.value, "VPCRegion": GlobalVariables.VPC_REGION.value},
        )

    # ACT
    with pytest.raises(AdapterException) as exc_info:
        mock_aws_dns_service.get_zone_id(dns_name=GlobalVariables.DNS_NAME.value)

    # ASSERT
    assertpy.assert_that(str(exc_info.value)).is_equal_to("Multiple hosted zones found.")


def test_get_zone_id_should_return_none_when_not_found(mock_aws_dns_service):
    # ARRANGE & ACT
    result = mock_aws_dns_service.get_zone_id(dns_name=GlobalVariables.DNS_NAME.value)

    # ASSERT
    assertpy.assert_that(result).is_none()


def test_get_zone_id_should_return_zone_id_when_found(mock_aws_dns_service, mock_route53):
    # ARRANGE
    zone_id = (
        mock_route53.create_hosted_zone(
            CallerReference=f"{GlobalVariables.DNS_NAME.value}-{GlobalVariables.VPC_ID.value}-{GlobalVariables.VPC_REGION.value}",
            HostedZoneConfig={
                "Comment": GlobalVariables.COMMENT.value,
                "PrivateZone": True,
            },
            Name=GlobalVariables.DNS_NAME.value,
            VPC={"VPCId": GlobalVariables.VPC_ID.value, "VPCRegion": GlobalVariables.VPC_REGION.value},
        )
        .get("HostedZone")
        .get("Id")
    )

    # ACT
    result = mock_aws_dns_service.get_zone_id(dns_name=GlobalVariables.DNS_NAME.value)

    # ASSERT
    assertpy.assert_that(result).is_equal_to(zone_id)
