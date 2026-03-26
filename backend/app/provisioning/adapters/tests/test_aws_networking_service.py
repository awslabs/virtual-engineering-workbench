from unittest import mock

import assertpy
import boto3
import moto
import pytest
from aws_lambda_powertools import logging

from app.provisioning.adapters.query_services import aws_networking_query_service
from app.shared.api import ssm_parameter_service

TEST_REGION = "eu-central-1"


@pytest.fixture(autouse=True)
def mock_ssm():
    with moto.mock_aws():
        yield boto3.client("ssm", region_name=TEST_REGION)


@pytest.fixture()
def mock_network_ip_map(mock_ssm):
    mock_ssm.put_parameter(
        Name="/virtual-workbench/dev/network-ip-map", Value='{"192.168.1.1":"10.0.0.1"}', Type="String"
    )


@pytest.fixture()
def mock_network_invalid_ip_map(mock_ssm):
    mock_ssm.put_parameter(Name="/virtual-workbench/dev/network-ip-map", Value="not a json", Type="String")


@pytest.fixture()
def mock_available_networks(mock_ssm):
    mock_ssm.put_parameter(Name="/available-networks", Value='["test-eu", "test-us"]', Type="String")


def test_should_fetch_network_ip_map_into_a_dict(mock_network_ip_map):
    # ARRANGE
    logger_mock = mock.create_autospec(spec=logging.Logger, instance=True)
    ssm_api_instance = ssm_parameter_service.SSMApi(region=TEST_REGION)
    aws_networking_query_svc = aws_networking_query_service.AWSNetworkingService(
        ssm_api=ssm_api_instance,
        network_ip_map_param_name="/virtual-workbench/dev/network-ip-map",
        logger=logger_mock,
        available_networks_param_name="/available-networks",
    )

    # ACT
    ip_map_dict = aws_networking_query_svc.get_network_ip_address_mapping()

    # ASSERT
    assertpy.assert_that(ip_map_dict).is_equal_to({"192.168.1.1": "10.0.0.1"})


def test_should_return_empty_array_if_deserialization_fails(mock_network_invalid_ip_map):
    # ARRANGE
    logger_mock = mock.create_autospec(spec=logging.Logger, instance=True)
    ssm_api_instance = ssm_parameter_service.SSMApi(region=TEST_REGION)
    aws_networking_query_svc = aws_networking_query_service.AWSNetworkingService(
        ssm_api=ssm_api_instance,
        network_ip_map_param_name="/virtual-workbench/dev/network-ip-map",
        logger=logger_mock,
        available_networks_param_name="/available-networks",
    )

    # ACT
    ip_map_dict = aws_networking_query_svc.get_network_ip_address_mapping()

    # ASSERT
    assertpy.assert_that(ip_map_dict).is_equal_to([])
    logger_mock.exception.assert_called_once()


def test_should_return_empty_array_if_parameter_does_not_exist():
    # ARRANGE
    logger_mock = mock.create_autospec(spec=logging.Logger, instance=True)
    ssm_api_instance = ssm_parameter_service.SSMApi(region=TEST_REGION)
    aws_networking_query_svc = aws_networking_query_service.AWSNetworkingService(
        ssm_api=ssm_api_instance,
        network_ip_map_param_name="/virtual-workbench/dev/network-ip-map",
        logger=logger_mock,
        available_networks_param_name="/available-networks",
    )

    # ACT
    ip_map_dict = aws_networking_query_svc.get_network_ip_address_mapping()

    # ASSERT
    assertpy.assert_that(ip_map_dict).is_equal_to([])
    logger_mock.exception.assert_called_once()


def test_should_return_available_networks(mock_available_networks):
    # ARRANGE
    logger_mock = mock.create_autospec(spec=logging.Logger, instance=True)
    ssm_api_instance = ssm_parameter_service.SSMApi(region=TEST_REGION)
    aws_networking_query_svc = aws_networking_query_service.AWSNetworkingService(
        ssm_api=ssm_api_instance,
        network_ip_map_param_name="/virtual-workbench/dev/netowrk-ip-map",
        logger=logger_mock,
        available_networks_param_name="/available-networks",
    )

    # ACT
    result = aws_networking_query_svc.get_available_networks()

    # ASSERT
    assertpy.assert_that(result).is_equal_to(["test-eu", "test-us"])
