import abc
import logging

from app.provisioning.domain.aggregates.state import (
    complete_start_handlers,
    complete_stop_handlers,
    handler,
    start_handlers,
    stop_handlers,
)
from app.provisioning.domain.exceptions import domain_exception
from app.provisioning.domain.model import provisioned_product
from app.provisioning.domain.ports import (
    container_management_service,
    instance_management_service,
)


class AbstractFactory(abc.ABC):

    @abc.abstractmethod
    def get_complete_start_handler(self) -> handler.Handler: ...

    @abc.abstractmethod
    def get_complete_stop_handler(self) -> handler.Handler: ...

    @abc.abstractmethod
    def get_stop_handler(self) -> handler.Handler: ...

    @abc.abstractmethod
    def get_start_handler(self) -> handler.Handler: ...


class ContainerHandlerFactory(AbstractFactory):

    def __init__(
        self,
        container_mgmt_srv: container_management_service.ContainerManagementService,
        logger: logging.Logger,
    ):
        self.__container_mgmt_srv = container_mgmt_srv
        self.__logger = logger

    def get_complete_start_handler(self) -> handler.Handler:
        return complete_start_handlers.ContainerHandler(self.__container_mgmt_srv, self.__logger)

    def get_complete_stop_handler(self) -> handler.Handler:
        return complete_stop_handlers.ContainerHandler(self.__container_mgmt_srv, self.__logger)

    def get_stop_handler(self) -> handler.Handler:
        return stop_handlers.ContainerHandler(self.__container_mgmt_srv)

    def get_start_handler(self):
        return start_handlers.ContainerHandler(self.__container_mgmt_srv, self.__logger)


class InstanceHandlerFactory(AbstractFactory):

    def __init__(
        self,
        instance_mgmt_srv: instance_management_service.InstanceManagementService,
        logger: logging.Logger,
    ):
        self.__instance_management_service = instance_mgmt_srv
        self.__logger = logger

    def get_complete_start_handler(self) -> handler.Handler:
        return complete_start_handlers.InstanceHandler(self.__instance_management_service, self.__logger)

    def get_complete_stop_handler(self) -> handler.Handler:
        return complete_stop_handlers.InstanceHandler(self.__instance_management_service, self.__logger)

    def get_stop_handler(self):
        return stop_handlers.InstanceHandler(self.__instance_management_service)

    def get_start_handler(self):
        return start_handlers.InstanceHandler(self.__instance_management_service, self.__logger)


def get_handler_factory(
    product_type: provisioned_product.ProvisionedProductType,
    container_mgmt_srv: container_management_service.ContainerManagementService,
    instance_mgmt_srv: instance_management_service.InstanceManagementService,
    logger: logging.Logger,
) -> AbstractFactory:
    match product_type:
        case p if p in provisioned_product.PRODUCT_CONTAINER_TYPES:
            return ContainerHandlerFactory(
                container_mgmt_srv=container_mgmt_srv,
                logger=logger,
            )
        case p if p in provisioned_product.PRODUCT_INSTANCE_TYPES:
            return InstanceHandlerFactory(
                instance_mgmt_srv=instance_mgmt_srv,
                logger=logger,
            )
        case _:
            raise domain_exception.DomainException(
                f"Cannot resolve provisioned product state handler factory for {product_type}"
            )
