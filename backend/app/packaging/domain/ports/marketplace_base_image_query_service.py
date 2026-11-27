from abc import ABC, abstractmethod

from app.packaging.domain.read_models.marketplace_base_image import MarketplaceBaseImage


class MarketplaceBaseImageQueryService(ABC):
    @abstractmethod
    def get_base_image(self, product_id: str) -> MarketplaceBaseImage:
        """Resolves a subscribed Marketplace AMI product to the AMI a recipe version builds on.

        Raises DomainException when the product is not subscribed or cannot be used as a base image.
        """
        ...

    @abstractmethod
    def get_imported_base_image(self, project_id: str, image_id: str) -> MarketplaceBaseImage:
        """Resolves an AMI that AWS publishes (Windows Server, RHEL, SUSE, Ubuntu Pro, ...) and that was
        imported into the project (imageSource AWS_PUBLISHED_AMI) to the AMI a recipe version builds on.

        AWS is the seller of record: there is no subscription, license or grant, so the result carries
        none. Raises DomainException when the image cannot be used as a base image.
        """
        ...
