from datetime import datetime, timezone

from app.projects.domain.commands.project_accounts import (
    complete_project_account_onboarding_command,
)
from app.projects.domain.events.project_accounts import project_account_on_boarded
from app.projects.domain.exceptions import domain_exception
from app.projects.domain.model import project_account
from app.projects.domain.ports import projects_query_service
from app.shared.adapters.boto import boto_provider, parameter_service_v2
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(
    command: complete_project_account_onboarding_command.CompleteProjectAccountOnboarding,
    projects_qs: projects_query_service.ProjectsQueryService,
    parameters_qs: parameter_service_v2.ParameterService,
    account_parameters_path: str,
    uow: unit_of_work.UnitOfWork,
    message_bus: message_bus.MessageBus,
):
    if not projects_qs.get_project_by_id(id=command.project_id.value):
        raise domain_exception.DomainException(f"Project {command.project_id.value} does not exist")

    if not (
        account := projects_qs.get_project_account_by_id(
            project_id=command.project_id.value, account_id=command.account_id.value
        )
    ):
        raise domain_exception.DomainException(f"Account {command.account_id.value} does not exist")

    account.accountStatus = project_account.ProjectAccountStatusEnum.Active
    account.lastOnboardingResult = project_account.ProjectAccountOnboardingResult.Succeeded
    account.lastOnboardingErrorMessage = None
    account.parameters = parameters_qs.get_parameters_by_path(
        path=account_parameters_path,
        provider_options=boto_provider.BotoProviderOptions(
            aws_account_id=account.awsAccountId,
            aws_region=account.region,
        ),
    )
    account.lastUpdateDate = datetime.now(timezone.utc).isoformat()

    with uow:
        uow.get_repository(project_account.ProjectAccountPrimaryKey, project_account.ProjectAccount).update_entity(
            project_account.ProjectAccountPrimaryKey(projectId=command.project_id.value, id=command.account_id.value),
            account,
        )
        uow.commit()

    message_bus.publish(
        project_account_on_boarded.ProjectAccountOnBoarded(
            projectId=account.projectId,
            technologyId=account.technologyId,
            awsAccountId=account.awsAccountId,
            accountId=account.id,
            accountType=account.accountType,
            stage=account.stage,
            region=account.region,
        )
    )
