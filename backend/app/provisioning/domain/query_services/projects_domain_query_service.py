from app.provisioning.domain.ports import projects_query_service
from app.provisioning.domain.read_models import project


class ProjectsDomainQueryService:
    def __init__(self, projects_qry_srv: projects_query_service.ProjectsQueryService):
        self._projects_qry_srv = projects_qry_srv

    def get_projects(self) -> list[project.Project]:
        return self._projects_qry_srv.get_projects()
