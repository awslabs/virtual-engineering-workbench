from enum import StrEnum


class ProductStatus(StrEnum):
    """
    Available statuses of products.
    """

    Starting = "STARTING"
    Provisioning = "PROVISIONING"
    Stopping = "STOPPING"
    Stopped = "STOPPED"
    Running = "RUNNING"
    ShuttingDown = "SHUTTING_DOWN"
    Deprovisioning = "DEPROVISIONING"
    Terminated = "TERMINATED"
    InstanceError = "INSTANCE_ERROR"
    ProvisioningError = "PROVISIONING_ERROR"
    Updating = "UPDATING"
    ConfigurationInProgress = "CONFIGURATION_IN_PROGRESS"
    ConfigurationFailed = "CONFIGURATION_FAILED"

    @staticmethod
    def list():
        return list(map(lambda p: p.value, ProductStatus))

    @staticmethod
    def active_statuses():
        return {p for p in ProductStatus if p != ProductStatus.Terminated}


class ServiceCatalogStatus(StrEnum):
    Available = "AVAILABLE"
    UnderChange = "UNDER_CHANGE"
    Tainted = "TAINTED"
    Error = "ERROR"
    PlanInProgress = "PLAN_IN_PROGRESS"


class EC2InstanceState(StrEnum):
    Pending = "pending"
    Running = "running"
    ShuttingDown = "shutting-down"
    Terminated = "terminated"
    Stopping = "stopping"
    Stopped = "stopped"


class TaskState(StrEnum):
    Provisioning = "PROVISIONING"
    Pending = "PENDING"
    Activating = "ACTIVATING"
    Running = "RUNNING"
    Deactivating = "DEACTIVATING"
    Stopping = "STOPPING"
    Deprovisioning = "DEPROVISIONING"
    Stopped = "STOPPED"


ACTIVE_PRODUCT_STATUSES = {
    ProductStatus.Running,
    ProductStatus.Stopped,
    ProductStatus.Starting,
    ProductStatus.Stopping,
}

PRODUCT_PROVISION_PROGRESS_STATES = {
    ProductStatus.Provisioning,
    ProductStatus.Updating,
    ProductStatus.ConfigurationInProgress,
}

EC2_TO_PRODUCT_STATE_MAP = {
    EC2InstanceState.Running: ProductStatus.Running,
    EC2InstanceState.Pending: ProductStatus.Starting,
    EC2InstanceState.Stopping: ProductStatus.Stopping,
    EC2InstanceState.Stopped: ProductStatus.Stopped,
}

CONTAINER_TO_PRODUCT_STATE_MAP = {
    TaskState.Provisioning: ProductStatus.Provisioning,
    TaskState.Pending: ProductStatus.Provisioning,
    TaskState.Activating: ProductStatus.Starting,
    TaskState.Running: ProductStatus.Running,
    TaskState.Deactivating: ProductStatus.Stopping,
    TaskState.Deprovisioning: ProductStatus.Stopping,
    TaskState.Stopping: ProductStatus.Stopping,
    TaskState.Stopped: ProductStatus.Stopped,
}
