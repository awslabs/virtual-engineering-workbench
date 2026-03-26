from datetime import datetime, timezone

from app.projects.domain.commands.project_accounts import reonboard_project_account_command
from app.projects.domain.events.project_accounts import project_account_on_boarding_restarted
from app.projects.domain.exceptions import domain_exception
from app.projects.domain.model import project_account
from app.projects.domain.ports import projects_query_service
from app.projects.domain.value_objects import account_type_value_object
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work

ACCOUNT_TYPES = {
    account_type_value_object.AccountTypeEnum.USER: "workbench-user",
    account_type_value_object.AccountTypeEnum.TOOLCHAIN: "workbench-toolchain",
}


def handle(
    command: reonboard_project_account_command.ReonboardProjectAccountCommand,
    unit_of_work: unit_of_work.UnitOfWork,
    projects_query_service: projects_query_service.ProjectsQueryService,
    message_bus: message_bus.MessageBus,
    web_application_account_id: str,
    web_application_environment: str,
    web_application_region: str,
    image_service_account_id: str,
    catalog_service_account_id: str,
):
    project = projects_query_service.get_project_by_id(command.project_id.value)
    if not project:
        raise domain_exception.DomainException("Provided project does not exist.")

    with unit_of_work:
        account = unit_of_work.get_repository(
            project_account.ProjectAccountPrimaryKey, project_account.ProjectAccount
        ).get(
            project_account.ProjectAccountPrimaryKey(
                projectId=command.project_id.value,
                id=command.account_id.value,
            )
        )

    if not account:
        raise domain_exception.DomainException("Account does not exist.")

    current_time = datetime.now(timezone.utc).isoformat()

    account.lastUpdateDate = current_time
    account.accountStatus = (
        project_account.ProjectAccountStatusEnum.OnBoarding
        if account.accountStatus != project_account.ProjectAccountStatusEnum.Active
        else project_account.ProjectAccountStatusEnum.ReOnboarding
    )

    with unit_of_work:
        unit_of_work.get_repository(
            project_account.ProjectAccountPrimaryKey, project_account.ProjectAccount
        ).update_entity(
            project_account.ProjectAccountPrimaryKey(
                projectId=command.project_id.value,
                id=command.account_id.value,
            ),
            account,
        )
        unit_of_work.commit()

    message_bus.publish(
        project_account_on_boarding_restarted.ProjectAccountOnBoardingRestarted(
            programAccountId=command.account_id.value,
            accountId=account.awsAccountId,
            accountType=ACCOUNT_TYPES[account.accountType],
            programId=project.projectId,
            programName=project.projectName,
            accountEnvironment=account.stage,
            region=account.region,
            variables={
                "account": account.awsAccountId,
                "environment": web_application_environment,
                "region": account.region,
                "web-application-account-id": web_application_account_id,
                "web-application-region": web_application_region,
                "image-service-account": image_service_account_id,
                "catalog-service-account": catalog_service_account_id,
            },
        )
    )
