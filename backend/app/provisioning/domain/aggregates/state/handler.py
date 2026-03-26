import abc

from app.provisioning.domain.model import provisioned_product
from app.shared.adapters.message_bus import message_bus


class Handler(abc.ABC):

    @abc.abstractmethod
    def process(self, provisioned_product: provisioned_product.ProvisionedProduct) -> message_bus.Message | None: ...
