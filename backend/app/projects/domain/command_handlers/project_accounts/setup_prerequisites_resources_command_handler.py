from app.projects.domain.commands.project_accounts import setup_prerequisites_resources_command
from app.projects.domain.ports import iac_service

PREREQUISITES = {"prerequisites": "true"}


def handle(
    cmd: setup_prerequisites_resources_command.SetupPrerequisitesResourcesCommand,
    iac_srv: iac_service.IACService,
):
    iac_srv.deploy_iac(
        aws_account_id=cmd.aws_account_id.value,
        region=cmd.region.value,
        variables={**cmd.variables.value, **PREREQUISITES} if cmd.variables else PREREQUISITES,
    )
