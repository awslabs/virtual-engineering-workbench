from datetime import datetime, timezone
from unittest import mock

import assertpy
import pytest

from app.publishing.domain.ports import amis_query_service, template_service
from app.publishing.domain.query_services import amis_domain_query_service
from app.publishing.domain.read_models import ami

TEST_PROJECT_ID = "proj-12345"


@pytest.fixture
def get_test_ami():
    def _get_test_ami():
        return ami.Ami(
            projectId=TEST_PROJECT_ID,
            amiId="ami-0001",
            amiName="AMI name",
            amiDescription="AMI description",
            createDate=datetime.now(timezone.utc).isoformat(),
            lastUpdateDate=datetime.now(timezone.utc).isoformat(),
        )

    return _get_test_ami


@pytest.fixture
def template_service_mock():
    file_mock = mock.create_autospec(spec=template_service.TemplateService)
    file_mock.get_object.return_value = '["ami-1", "ami-2", "ami-3", "ami-4", "ami-5"]'
    return file_mock


def test_get_amis_when_exists_should_filter_retired_amis(get_test_ami, template_service_mock):
    # ARRANGE
    mock_qs = mock.create_autospec(spec=amis_query_service.AMIsQueryService)
    mock_qs.get_amis.return_value = [
        get_test_ami(),
        get_test_ami(),
    ]
    domain_service = amis_domain_query_service.AMIsDomainQueryService(
        ami_qry_srv=mock_qs,
        template_srv=template_service_mock,
        used_ami_list_file_path="amis/used-ami-list.json",
    )

    # ACT
    amis = domain_service.get_amis(TEST_PROJECT_ID)

    # ASSERT
    assertpy.assert_that(amis).is_not_none()
    assertpy.assert_that(amis).is_length(2)


def test_get_ami_returns_correct_ami(get_test_ami, template_service_mock):
    # ARRANGE
    mock_qs = mock.create_autospec(spec=amis_query_service.AMIsQueryService)
    mock_qs.get_ami.return_value = get_test_ami()
    domain_service = amis_domain_query_service.AMIsDomainQueryService(
        ami_qry_srv=mock_qs,
        template_srv=template_service_mock,
        used_ami_list_file_path="amis/used-ami-list.json",
    )

    # ACT
    ami = domain_service.get_ami("ami-0001")

    # ASSERT
    assertpy.assert_that(ami).is_not_none()
    assertpy.assert_that(ami.amiId).is_equal_to("ami-0001")


def test_get_used_ami_list_returns_ami_list(template_service_mock):
    # ARRANGE
    mock_qs = mock.create_autospec(spec=amis_query_service.AMIsQueryService)
    domain_service = amis_domain_query_service.AMIsDomainQueryService(
        ami_qry_srv=mock_qs,
        template_srv=template_service_mock,
        used_ami_list_file_path="amis/used-ami-list.json",
    )

    # ACT
    ami_list = domain_service.get_used_ami_list()

    # ASSERT
    assertpy.assert_that(ami_list).is_not_none()
    assertpy.assert_that(ami_list).is_length(5)
    assertpy.assert_that(ami_list).contains("ami-1")
