from abc import ABC, abstractmethod

from app.packaging.domain.read_models.discovered_marketplace_subscription import DiscoveredMarketplaceSubscription
from app.packaging.domain.value_objects.shared import project_id_value_object


class MarketplaceSubscriptionQueryService(ABC):
    @abstractmethod
    def discover(
        self, project_id: project_id_value_object.ProjectIdValueObject
    ) -> list[DiscoveredMarketplaceSubscription]: ...
