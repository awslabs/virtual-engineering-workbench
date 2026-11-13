from freezegun import freeze_time

from app.packaging.domain.read_models.marketplace_ami import MarketplaceAmi


def _ami(deprecation_time: str | None) -> MarketplaceAmi:
    return MarketplaceAmi(
        amiId="ami-123",
        productCode="pc-1",
        state="available",
        region="us-east-1",
        deprecationTime=deprecation_time,
    )


@freeze_time("2025-06-01T12:00:00Z")
def test_deprecated_is_true_after_deprecation_time():
    assert _ami("2025-06-01T11:59:59Z").deprecated is True


@freeze_time("2025-06-01T12:00:00Z")
def test_deprecated_is_false_before_scheduled_deprecation_time():
    assert _ami("2025-06-01T12:00:01Z").deprecated is False


def test_deprecated_is_false_without_deprecation_time():
    assert _ami(None).deprecated is False
