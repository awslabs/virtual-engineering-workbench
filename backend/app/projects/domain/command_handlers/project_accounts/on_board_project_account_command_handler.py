from datetime import datetime, timezone

from app.projects.domain.commands.project_accounts import on_board_project_account_command
from app.projects.domain.events.project_accounts import project_account_on_boarding_started
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


def handle_on_board_project_account_command(
    command: on_board_project_account_command.OnBoardProjectAccountCommand,
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

    account = projects_query_service.list_project_accounts(
        command.project_id.value,
        account_type=command.account_type.value,
        stage=command.stage,
        technology_id=command.technology.value,
    )
    if next((acc for acc in account if acc.region == command.region.value), None):
        raise domain_exception.DomainException("Provided project already has an account of this type, stage and region")

    current_time = datetime.now(timezone.utc).isoformat()

    project_acct = project_account.ProjectAccount(
        awsAccountId=command.account_id.value,
        accountType=command.account_type.value,
        accountName=command.account_name.value,
        accountDescription=command.account_description.value,
        createDate=current_time,
        lastUpdateDate=current_time,
        accountStatus=project_account.ProjectAccountStatusEnum.OnBoarding,
        stage=command.stage,
        technologyId=command.technology.value,
        region=command.region.value,
        projectId=command.project_id.value,
    )

    if projects_query_service.list_project_accounts_by_aws_account(project_acct.awsAccountId):
        raise domain_exception.DomainException(f"Account with id: {project_acct.awsAccountId} already onboarded")

    with unit_of_work:
        unit_of_work.get_repository(project_account.ProjectAccountPrimaryKey, project_account.ProjectAccount).add(
            project_acct
        )
        unit_of_work.commit()

    message_bus.publish(
        project_account_on_boarding_started.ProjectAccountOnBoardingStarted(
            programAccountId=project_acct.id,
            accountId=project_acct.awsAccountId,
            accountType=ACCOUNT_TYPES[project_acct.accountType],
            programId=project.projectId,
            programName=project.projectName,
            accountEnvironment=project_acct.stage,
            region=project_acct.region,
            variables={
                "account": project_acct.awsAccountId,
                "environment": web_application_environment,
                "region": project_acct.region,
                "web-application-account-id": web_application_account_id,
                "web-application-region": web_application_region,
                "image-service-account": image_service_account_id,
                "catalog-service-account": catalog_service_account_id,
            },
        )
    )
