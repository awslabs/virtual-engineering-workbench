from abc import ABC, abstractmethod

from app.shared.domain.model import task_context


class TaskContextQueryService(ABC):
    @abstractmethod
    def get_task_context(self) -> task_context.TaskContext: ...
