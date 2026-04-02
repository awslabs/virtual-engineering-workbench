from aws_lambda_powertools import Tracer
from aws_lambda_powertools.event_handler.api_gateway import Router

from app.projects.entrypoints.s2s_api import bootstrapper
from app.projects.entrypoints.s2s_api.model import api_model

tracer = Tracer()


def init(dependencies: bootstrapper.Dependencies) -> Router:
    router = Router()

    @tracer.capture_method
    @router.get("/projects")
    def get_projects() -> api_model.GetProjectsResponse:
        """Returns a list of all projects with paging."""

        page_size = int(router.current_event.get_query_string_value("pageSize") or 10)
        next_token = router.current_event.get_query_string_value("nextToken")

        projects, last_evaluated_key, assignments = dependencies.projects_query_service.list_projects(
            page_size=page_size,
            next_token=next_token,
            user_id=None,
        )

        projects_parsed = [api_model.Project.model_validate(p.model_dump()) for p in projects]
        return api_model.GetProjectsResponse(
            projects=projects_parsed,
            nextToken=last_evaluated_key,
        )

    return router
