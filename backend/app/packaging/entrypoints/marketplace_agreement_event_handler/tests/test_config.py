import assertpy
import pytest

from app.packaging.entrypoints.marketplace_agreement_event_handler import config


def test_get_default_region_accepts_us_east_1(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    assertpy.assert_that(config.AppConfig().get_default_region()).is_equal_to("us-east-1")


@pytest.mark.parametrize("wrong_region", ["us-west-2", "eu-central-1", "eu-west-1", "ap-southeast-1", ""])
def test_get_default_region_rejects_other_regions(monkeypatch, wrong_region):
    """AWS emits aws.agreement-marketplace only in us-east-1. Any other
    region → hard-fail at cold start rather than silent no-op."""
    monkeypatch.setenv("AWS_DEFAULT_REGION", wrong_region)
    with pytest.raises(RuntimeError, match="us-east-1"):
        config.AppConfig().get_default_region()


def test_get_default_region_rejects_missing_env(monkeypatch):
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)
    with pytest.raises(RuntimeError, match="us-east-1"):
        config.AppConfig().get_default_region()
