from abc import ABC, abstractmethod

from app.packaging.domain.model.pipeline import pipeline


class PipelineQueryService(ABC):
    @abstractmethod
    def get_pipelines(self, project_id: str) -> list[pipeline.Pipeline]: ...

    @abstractmethod
    def get_pipeline(self, project_id: str, pipeline_id: str) -> pipeline.Pipeline | None: ...

    @abstractmethod
    def get_pipeline_by_pipeline_id(self, pipeline_id: str) -> pipeline.Pipeline | None: ...
