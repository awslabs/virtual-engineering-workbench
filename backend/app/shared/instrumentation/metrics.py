import enum
from abc import ABC, abstractmethod


class MetricType(enum.StrEnum):
    DomainEvent = "DomainEvent"
    SuccessfullCommand = "SuccessfullCommand"
    FailedCommand = "FailedCommand"


class Metrics(ABC):
    @abstractmethod
    def publish_counter(self, metric_name: str, metric_type: MetricType, count: int = 1) -> None: ...
