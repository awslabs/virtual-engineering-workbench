from unittest import mock

import assertpy
import pytest

from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.model import shared_ami, version
from app.publishing.domain.ports import image_service
from app.publishing.domain.query_services import shared_amis_domain_query_service
from app.publishing.domain.value_objects import (
    ami_id_value_object,
    aws_account_id_value_object,
    product_id_value_object,
    product_type_value_object,
    region_value_object,
    version_id_value_object,
)

TEST_ORIGINAL_AMI_REGION = "us-east-1"


@pytest.fixture()
def image_svc_mock():
    image_svc_mock = mock.create_autospec(spec=image_service.ImageService)
    return image_svc_mock


@pytest.mark.parametrize(
    "is_ami_shared,region,decision",
    (
        (True, "us-east-1", shared_amis_domain_query_service.ShareAmiDecision.Done),
        (True, "us-central-1", shared_amis_domain_query_service.ShareAmiDecision.Done),
        (
            False,
            "us-east-1",
            shared_amis_domain_query_service.ShareAmiDecision.Share,
        ),
        (
            False,
            "us-central-1",
            shared_amis_domain_query_service.ShareAmiDecision.Copy,
        ),
    ),
)
def test_make_share_ami_decision_makes_correct_decision(
    is_ami_shared, region, decision, image_svc_mock, mock_unit_of_work, mock_shared_ami_repo, mock_version_repo
):
    # ARRANGE
    mock_version_repo.get.return_value = version.Version(
        versionId="vers-11111111",
        projectId="proj-12345",
        productId="prod-11111111",
        scPortfolioId="port-12345",
        versionDescription="Workbench version description",
        versionName="1.0.0",
        versionType=version.VersionType.Released.text,
        technologyId="tech-12345",
        awsAccountId="123456789012",
        stage="DEV",
        region=region,
        originalAmiId="ami-023c04780e65e723c",
        status=version.VersionStatus.Created,
        isRecommendedVersion=True,
        createDate="2023-06-20T00:00:00+00:00",
        lastUpdateDate="2023-06-20T00:00:00+00:00",
        createdBy="T0037SG",
        lastUpdatedBy="T0037SG",
    )
    mock_shared_ami_repo.get.return_value = (
        shared_ami.SharedAmi(
            originalAmiId="ami-023c04780e65e723c",
            copiedAmiId="ami-copy",
            awsAccountId="123456789012",
            region=region,
            createDate="2023-06-20T00:00:00+00:00",
            lastUpdateDate="2023-06-20T00:00:00+00:00",
        )
        if is_ami_shared
        else None
    )
    domain_service = shared_amis_domain_query_service.SharedAMIsDomainQueryService(
        unit_of_work=mock_unit_of_work, image_svc=image_svc_mock, default_original_ami_region=TEST_ORIGINAL_AMI_REGION
    )

    # ACT
    mock_decision, fetched_region, original_ami_id, copied_ami_id = domain_service.make_share_ami_decision(
        product_id=product_id_value_object.from_str("prod-11111111"),
        version_id=version_id_value_object.from_str("vers-11111111"),
        aws_account_id=aws_account_id_value_object.from_str("123456789012"),
        product_type=product_type_value_object.from_str("WORKBENCH"),
    )
    # ASSERT
    assertpy.assert_that(mock_decision).is_equal_to(decision)
    assertpy.assert_that(fetched_region).is_equal_to(region)
    assertpy.assert_that(original_ami_id).is_equal_to("ami-023c04780e65e723c")
    assertpy.assert_that(copied_ami_id).is_equal_to("ami-copy" if is_ami_shared else None)


@pytest.mark.parametrize(
    "response,outcome",
    [
        ("pending", False),
        ("available", True),
    ],
)
def test_verify_copy_checks_if_copy_is_ready(response, outcome, image_svc_mock, uow_mock):
    # ARRANGE
    image_svc_mock.get_copied_ami_status.return_value = response
    domain_service = shared_amis_domain_query_service.SharedAMIsDomainQueryService(
        unit_of_work=uow_mock, image_svc=image_svc_mock, default_original_ami_region=TEST_ORIGINAL_AMI_REGION
    )
    # ACT
    is_copy_ready = domain_service.verify_copy(
        region_value_object.RegionValueObject("eu-west-3"),
        ami_id_value_object.AmiIdValueObject("copy-12345"),
    )
    # ASSERT
    assertpy.assert_that(is_copy_ready).is_equal_to(outcome)


def test_verify_copy_raises_exception_when_status_invalid(image_svc_mock, uow_mock):
    # ARRANGE
    image_svc_mock.get_copied_ami_status.return_value = "invalid"
    domain_service = shared_amis_domain_query_service.SharedAMIsDomainQueryService(
        unit_of_work=uow_mock, image_svc=image_svc_mock, default_original_ami_region=TEST_ORIGINAL_AMI_REGION
    )
    # ACT & ASSERT
    with pytest.raises(domain_exception.DomainException):
        domain_service.verify_copy(
            region_value_object.RegionValueObject("eu-west-3"),
            ami_id_value_object.AmiIdValueObject("copy-12345"),
        )
