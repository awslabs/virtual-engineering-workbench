from app.projects.domain.commands.project_accounts import setup_static_resources_command
from app.projects.domain.ports import iac_service
from app.shared.adapters.boto import boto_provider, resource_access_management_service


def handle(
    cmd: setup_static_resources_command.SetupStaticResourcesCommand,
    iac_srv: iac_service.IACService,
    ram_srv: resource_access_management_service.ResourceAccessManagementService,
    ram_resource_tag: str,
):

    resource_share_arns = ram_srv.get_resource_shares(
        tag_name=ram_resource_tag, provider_options=boto_provider.BotoProviderOptions(aws_region=cmd.region.value)
    )

    for rs_arn in resource_share_arns:
        ram_srv.associate_resource_share(
            resource_share_arn=rs_arn,
            principals=[cmd.aws_account_id.value],
            provider_options=boto_provider.BotoProviderOptions(aws_region=cmd.region.value),
        )

    args = {"aws_account_id": cmd.aws_account_id.value, "region": cmd.region.value}
    if cmd.variables:
        args["variables"] = cmd.variables.value

    iac_srv.deploy_iac(**args)
