import json

from app.publishing.domain.ports import amis_query_service, template_service
from app.publishing.domain.read_models import ami


class AMIsDomainQueryService:
    def __init__(
        self,
        ami_qry_srv: amis_query_service.AMIsQueryService,
        template_srv: template_service.TemplateService,
        used_ami_list_file_path: str,
    ) -> None:
        self._ami_qry_srv = ami_qry_srv
        self._template_srv = template_srv
        self._used_ami_list_file_path = used_ami_list_file_path

    def get_amis(self, project_id: str) -> list[ami.Ami]:
        return self._ami_qry_srv.get_amis(project_id)

    def get_ami(self, ami_id: str) -> ami.Ami:
        return self._ami_qry_srv.get_ami(ami_id)

    def get_used_ami_list(self) -> list[str]:
        return json.loads(self._template_srv.get_object(object_path=self._used_ami_list_file_path))
