"""How many provisioned products of one product a user may hold in a project and stage.

Launching checks it, and the API reports it so the portal can say how many are left before a launch
is refused.
"""

from pydantic import BaseModel, Field

from app.provisioning.domain.model import product_status, provisioned_product

PROVISIONED_PRODUCT_LIMIT_PER_PRODUCT_AND_USER = 5

# a product on its way out no longer counts against the limit.
UNCOUNTED_STATUSES = [
    product_status.ProductStatus.Terminated,
    product_status.ProductStatus.Deprovisioning,
]


def limit_for_stage(stage: provisioned_product.ProvisionedProductStage) -> int:
    if stage == provisioned_product.ProvisionedProductStage.QA:
        return PROVISIONED_PRODUCT_LIMIT_PER_PRODUCT_AND_USER + 1
    return PROVISIONED_PRODUCT_LIMIT_PER_PRODUCT_AND_USER


class ProvisioningLimit(BaseModel):
    limit: int = Field(..., title="Limit")
    provisioned: int = Field(..., title="Provisioned")

    @property
    def remaining(self) -> int:
        return max(self.limit - self.provisioned, 0)
