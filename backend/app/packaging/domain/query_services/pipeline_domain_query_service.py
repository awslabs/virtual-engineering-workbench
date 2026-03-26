from app.packaging.domain.ports import pipeline_query_service
from app.packaging.domain.value_objects.pipeline import pipeline_id_value_object
from app.packaging.domain.value_objects.shared import project_id_value_object


class PipelineDomainQueryService(pipeline_query_service.PipelineQueryService):
    def __init__(self, pipeline_qry_srv: pipeline_query_service.PipelineQueryService):
        self._pipeline_qry_srv = pipeline_qry_srv

    def get_pipelines(self, project_id: project_id_value_object.ProjectIdValueObject):
        return self._pipeline_qry_srv.get_pipelines(project_id=project_id.value)

    def get_pipeline(
        self,
        project_id: project_id_value_object.ProjectIdValueObject,
        pipeline_id: pipeline_id_value_object.PipelineIdValueObject,
    ):
        return self._pipeline_qry_srv.get_pipeline(project_id=project_id.value, pipeline_id=pipeline_id.value)

    def get_pipeline_by_pipeline_id(self, pipeline_id: pipeline_id_value_object.PipelineIdValueObject):
        return self._pipeline_qry_srv.get_pipeline_by_pipeline_id(pipeline_id=pipeline_id.value)
