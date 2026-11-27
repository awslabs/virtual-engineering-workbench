from typing import Optional

from pydantic import BaseModel, Field


class MarketplaceProductDetails(BaseModel):
    """Product detail projection returned by the Discovery API GetProduct
    call, used by the ``CreateAgreementRequestCommand`` handler to
    verify that every product associated with a chosen offer is an AMI-type
    Marketplace product (i.e. its fulfillment options include
    ``AMAZON_MACHINE_IMAGE``).

    Only the fields the domain guard needs are surfaced. Additional fields
    can be added later if downstream (e.g. quote review UI) needs them.
    """

    productId: str = Field(..., title="ProductId")
    productName: Optional[str] = Field(None, title="ProductName")
    fulfillmentOptionTypes: list[str] = Field(default_factory=list, title="FulfillmentOptionTypes")

    def is_ami_product(self) -> bool:
        """True iff at least one fulfillment option is
        ``AMAZON_MACHINE_IMAGE``. Matches the ``AmiProduct`` classification
        of the Discovery API ``ProductType`` filter.
        """
        return "AMAZON_MACHINE_IMAGE" in self.fulfillmentOptionTypes
