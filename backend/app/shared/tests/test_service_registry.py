import logging
from unittest import mock

import assertpy
import boto3
import moto
import pytest

from app.shared import config
from app.shared.api import aws_api, bounded_contexts, service_registry


@pytest.fixture
def mock_logger():
    return mock.create_autospec(spec=logging.Logger)


@pytest.fixture(autouse=True)
def aws_credentials(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-central-1")


@pytest.fixture
def mock_ssm():
    with moto.mock_aws():
        client = boto3.client("ssm", region_name="eu-central-1")
        yield client


@pytest.fixture
def registry(mock_ssm, mock_logger):
    return service_registry.ServiceRegistry(
        ssm_client=mock_ssm,
        ssm_prefix="proserve-wb",
        environment="dev",
        region="eu-central-1",
        logger=mock_logger,
    )


# --- service_registry.ServiceRegistry tests ---


def test_api_for_returns_awsapibase(registry):
    # ACT
    result = registry.api_for(bounded_contexts.BoundedContext.PROVISIONING)

    # ASSERT
    assertpy.assert_that(result).is_instance_of(aws_api.AWSAPIBase)


def test_api_for_returns_same_instance_on_second_call(registry):
    # ACT
    first = registry.api_for(bounded_contexts.BoundedContext.PROVISIONING)
    second = registry.api_for(bounded_contexts.BoundedContext.PROVISIONING)

    # ASSERT
    assertpy.assert_that(first).is_same_as(second)


def test_api_for_returns_different_instances_for_different_bcs(registry):
    # ACT
    prov = registry.api_for(bounded_contexts.BoundedContext.PROVISIONING)
    pub = registry.api_for(bounded_contexts.BoundedContext.PUBLISHING)

    # ASSERT
    assertpy.assert_that(prov).is_not_same_as(pub)


# --- service_registry._LazyAWSAPI tests ---


def test_lazy_api_does_not_call_ssm_on_creation(registry):
    # ACT — no exception even though SSM param doesn't exist
    api = registry.api_for(bounded_contexts.BoundedContext.PROVISIONING)

    # ASSERT
    assertpy.assert_that(api).is_instance_of(service_registry._LazyAWSAPI)


def test_lazy_api_resolves_on_first_access(mock_ssm, mock_logger):
    # ARRANGE
    mock_ssm.put_parameter(
        Name="/proserve-wb-provisioning-api-dev/api/url",
        Value="https://api.example.com/v1",
        Type="String",
    )
    registry = service_registry.ServiceRegistry(
        ssm_client=mock_ssm, ssm_prefix="proserve-wb", environment="dev", region="eu-central-1", logger=mock_logger
    )

    # ACT
    api = registry.api_for(bounded_contexts.BoundedContext.PROVISIONING)

    # ASSERT
    assertpy.assert_that(api.api_url.geturl()).is_equal_to("https://api.example.com/v1")


def test_lazy_api_region_available_without_resolve(registry):
    # ACT
    api = registry.api_for(bounded_contexts.BoundedContext.PROVISIONING)

    # ASSERT
    assertpy.assert_that(api.region).is_equal_to("eu-central-1")


def test_lazy_api_raises_after_retries_when_param_missing(mock_ssm, mock_logger, monkeypatch):
    # ARRANGE
    monkeypatch.setattr("time.sleep", lambda _: None)
    registry = service_registry.ServiceRegistry(
        ssm_client=mock_ssm, ssm_prefix="proserve-wb", environment="dev", region="eu-central-1", logger=mock_logger
    )
    api = registry.api_for(bounded_contexts.BoundedContext.PROVISIONING)

    # ACT / ASSERT
    with pytest.raises(service_registry.ServiceRegistryError, match="not found after 3 retries"):
        api.api_url


def test_lazy_api_caches_delegate_after_resolve(mock_ssm, mock_logger):
    # ARRANGE
    mock_ssm.put_parameter(
        Name="/proserve-wb-projects-api-dev/api/url",
        Value="https://projects.example.com",
        Type="String",
    )
    registry = service_registry.ServiceRegistry(
        ssm_client=mock_ssm, ssm_prefix="proserve-wb", environment="dev", region="eu-central-1", logger=mock_logger
    )
    api = registry.api_for(bounded_contexts.BoundedContext.PROJECTS)

    # ACT
    url1 = api.api_url
    url2 = api.api_url

    # ASSERT
    assertpy.assert_that(url1).is_equal_to(url2)


def test_from_config_creates_registry(mock_ssm, mock_logger, monkeypatch):
    # ARRANGE
    monkeypatch.setenv("VEW_ORGANIZATION_PREFIX", "proserve")
    monkeypatch.setenv("VEW_APPLICATION_PREFIX", "wb")
    monkeypatch.setenv("APP_ENVIRONMENT", "dev")
    app_config = config.VEWBaseConfig()

    # ACT
    registry = service_registry.ServiceRegistry.from_config(
        app_config=app_config, ssm_client=mock_ssm, logger=mock_logger
    )

    # ASSERT
    assertpy.assert_that(registry._ssm_prefix).is_equal_to("proserve-wb")
    assertpy.assert_that(registry._environment).is_equal_to("dev")
