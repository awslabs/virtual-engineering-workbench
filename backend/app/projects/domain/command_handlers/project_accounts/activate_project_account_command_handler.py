from datetime import datetime, timezone

from app.projects.domain.commands.project_accounts import activate_project_account_command
from app.projects.domain.exceptions import domain_exception
from app.projects.domain.model import project_account
from app.projects.domain.ports import projects_query_service
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle_activate_project_account_command(
    cmd: activate_project_account_command.ActivateProjectAccountCommand,
    unit_of_work: unit_of_work.UnitOfWork,
    projects_qry_srv: projects_query_service.ProjectsQueryService,
):
    project = projects_qry_srv.get_project_by_id(cmd.project_id.value)
    if not project:
        raise domain_exception.DomainException("Provided project does not exist.")

    project_accounts = projects_qry_srv.list_project_accounts(cmd.project_id.value)
    current_time = datetime.now(timezone.utc).isoformat()

    with unit_of_work:
        for pa in project_accounts:
            if (
                pa.accountStatus == project_account.ProjectAccountStatusEnum.Inactive
                and cmd.account_status.value == project_account.ProjectAccountStatusEnum.Active
                and pa.id == cmd.account_id.value
            ):
                pa.lastUpdateDate = current_time
                pa.accountStatus = cmd.account_status.value
                unit_of_work.get_repository(
                    project_account.ProjectAccountPrimaryKey, project_account.ProjectAccount
                ).update_entity(
                    project_account.ProjectAccountPrimaryKey(projectId=cmd.project_id.value, id=pa.id),
                    pa,
                )
                unit_of_work.commit()
