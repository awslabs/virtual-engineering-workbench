import pytest
from pydantic import ValidationError

from app.provisioning.domain.events.product_provisioning import provisioned_product_upgraded


@pytest.mark.parametrize("region_key", ["region", "Region"])
def test_provisioned_product_upgraded_accepts_region_aliases_and_serializes_canonical_name(region_key):
    event = provisioned_product_upgraded.ProvisionedProductUpgraded.model_validate(
        {
            "eventName": "ProvisionedProductUpgraded",
            "provisionedProductId": "pp-123",
            "awsAccountId": "001234567890",
            region_key: "us-east-1",
            "projectId": "proj-123",
            "owner": "T0011AA",
            "productType": "WORKBENCH",
            "productName": "Pied Piper",
        }
    )

    assert event.region == "us-east-1"
    assert event.model_dump(by_alias=True)["region"] == "us-east-1"
    assert "Region" not in event.model_dump(by_alias=True)


@pytest.mark.parametrize("region", [{}, {"region": None}, {"Region": None}])
def test_provisioned_product_upgraded_rejects_missing_or_null_region(region):
    with pytest.raises(ValidationError):
        provisioned_product_upgraded.ProvisionedProductUpgraded.model_validate(
            {
                "eventName": "ProvisionedProductUpgraded",
                "provisionedProductId": "pp-123",
                "awsAccountId": "001234567890",
                "projectId": "proj-123",
                "owner": "T0011AA",
                "productType": "WORKBENCH",
                "productName": "Pied Piper",
                **region,
            }
        )
