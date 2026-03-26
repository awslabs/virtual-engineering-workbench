from app.projects.domain.commands.project_accounts import setup_dynamic_resources_command
from app.projects.domain.exceptions import domain_exception
from app.projects.domain.model import dynamic_parameter
from app.projects.domain.ports import dns_service, network_service
from app.shared.adapters.boto import boto_provider, parameter_service_v2
from app.shared.domain.ports import secret_service

GLOBAL_SCOPE_SUFFIX = "global"


def handle(
    cmd: setup_dynamic_resources_command.SetupDynamicResourcesCommand,
    dns_records: dict,
    dns_srv: dns_service.DNSService,
    network_srv: network_service.NetworkService,
    parameter_srv: parameter_service_v2.ParameterService,
    parameters: list[dynamic_parameter.DynamicParameter],
    secrets_srv: secret_service.SecretsService,
    spoke_account_secrets_scope: str,
    zone_name: str,
):
    provider_options = boto_provider.BotoProviderOptions(
        aws_account_id=cmd.aws_account_id.value,
        aws_region=cmd.region.value,
    )
    __configure_networking_parameters(network_srv, parameter_srv, parameters, provider_options)
    __configure_dns(dns_records, dns_srv, provider_options, network_srv, zone_name)
    __configure_secrets(cmd.region.value, secrets_srv, spoke_account_secrets_scope, provider_options)


def __configure_dns(
    dns_records: dict,
    dns_srv: dns_service.DNSService,
    provider_options: boto_provider.BotoProviderOptions,
    network_srv: network_service.NetworkService,
    zone_name: str,
) -> None:
    # Get VPC Ids
    vpc_ids = network_srv.get_vpcs_ids(provider_options=provider_options)
    if not vpc_ids:
        raise domain_exception.DomainException(
            f"No VPCs found in the account {provider_options.aws_account_id} at region {provider_options.aws_region}"
        )

    zone_id = dns_srv.get_zone_id(dns_name=zone_name, provider_options=provider_options)
    if not zone_id:
        zone_id = dns_srv.create_private_zone(
            comment="Private hosted zone for Virtual Engineering Workbench (VEW).",
            dns_name=zone_name,
            provider_options=provider_options,
            vpc_id=vpc_ids[0],  # Configure the private zone only for 1 VPC
            vpc_region=provider_options.aws_region,
        )

    # If a VPC configured for onboarding exists, we associate the zone with all VPCs
    for vpc_id in vpc_ids:
        if not dns_srv.is_vpc_associated_with_zone(
            dns_name=zone_name,
            provider_options=provider_options,
            vpc_id=vpc_id,
            vpc_region=provider_options.aws_region,
        ):
            dns_srv.associate_vpc_with_zone(
                provider_options=provider_options,
                vpc_id=vpc_id,
                vpc_region=provider_options.aws_region,
                zone_id=zone_id,
            )

    for dns_record in dns_records.get("records"):
        dns_record_name = dns_record.get("name")

        dns_srv.create_dns_record(
            name=f"{dns_record_name}.{zone_name}",
            provider_options=provider_options,
            type=dns_record.get("type"),
            ttl=dns_record.get("ttl"),
            value=dns_record.get("value").get(provider_options.aws_region),
            zone_id=zone_id,
        )


def __configure_networking_parameters(
    network_srv: network_service.NetworkService,
    parameter_srv: parameter_service_v2.ParameterService,
    parameters: list[dynamic_parameter.DynamicParameter],
    provider_options: boto_provider.BotoProviderOptions,
) -> None:
    vpc_id_param = next(
        (param for param in parameters if param.type == dynamic_parameter.DynamicParameterType.VPC_ID), None
    )
    vpc_id = parameter_srv.get_parameter_value(parameter_name=vpc_id_param.name, provider_options=provider_options)
    if not vpc_id:
        return
    backend_subnet_ids_param = next(
        (param for param in parameters if param.type == dynamic_parameter.DynamicParameterType.BACKEND_SUBNET_IDS),
        None,
    )
    if backend_subnet_ids_param:
        backend_subnet_tag_name, backend_subnet_tag_value = backend_subnet_ids_param.tag.split(":")
        backend_subnets = network_srv.get_subnets_by_tag(
            tag_name=backend_subnet_tag_name,
            tag_value=backend_subnet_tag_value,
            vpc_id=vpc_id,
            provider_options=provider_options,
        )
        if backend_subnets:
            backend_subnet_cidrs_param = next(
                (
                    param
                    for param in parameters
                    if param.type == dynamic_parameter.DynamicParameterType.BACKEND_SUBNET_CIDRS
                ),
                None,
            )
            subnet_ids = [subnet.get("SubnetId") for subnet in backend_subnets]
            subnet_cidrs = [subnet.get("CidrBlock") for subnet in backend_subnets]
            parameter_srv.create_string_parameter(
                parameter_name=backend_subnet_ids_param.name,
                parameter_value=",".join(subnet_ids),
                is_overwrite=True,
                provider_options=provider_options,
            )
            if backend_subnet_cidrs_param:
                parameter_srv.create_string_parameter(
                    parameter_name=backend_subnet_cidrs_param.name,
                    parameter_value=",".join(subnet_cidrs),
                    is_overwrite=True,
                    provider_options=provider_options,
                )


def __configure_secrets(
    region: str,
    secrets_srv: secret_service.SecretsService,
    spoke_account_secrets_scope: str,
    provider_options: boto_provider.BotoProviderOptions,
) -> None:
    secrets_ids_to_propagate = secrets_srv.get_secrets_ids_by_path(
        path=f"/{spoke_account_secrets_scope}/{GLOBAL_SCOPE_SUFFIX}"
    ) + secrets_srv.get_secrets_ids_by_path(path=f"/{spoke_account_secrets_scope}/{region}")
    for secret_id in secrets_ids_to_propagate:
        secret_name, description = secrets_srv.describe_secret(secret_name=secret_id)
        secret_value = secrets_srv.get_secret_value(secret_name=secret_id)

        secrets_srv.upsert_secret(
            secret_name=secret_name,
            secret_value=secret_value,
            description=description,
            provider_options=provider_options,
        )
