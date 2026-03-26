import json
from http import HTTPStatus
from urllib.parse import unquote

from aws_lambda_powertools import logging, tracing
from aws_lambda_powertools.event_handler import api_gateway, content_types
from aws_lambda_powertools.event_handler.openapi.models import Server
from aws_lambda_powertools.event_handler.openapi.params import Query
from aws_lambda_powertools.shared.types import Annotated
from aws_lambda_powertools.utilities import typing
from aws_xray_sdk.core import patch_all

from app.provisioning.domain.commands.product_provisioning import (
    launch_product_command,
    remove_provisioned_product_command,
)
from app.provisioning.domain.commands.provisioned_product_state import (
    initiate_provisioned_product_start_command,
    initiate_provisioned_product_stop_command,
)
from app.provisioning.domain.exceptions import domain_exception
from app.provisioning.domain.value_objects import (
    additional_configurations_value_object,
    deployment_option_value_object,
    ip_address_value_object,
    product_id_value_object,
    product_name_value_object,
    product_status_value_object,
    product_type_value_object,
    product_version_id_value_object,
    product_version_name_value_object,
    project_id_value_object,
    provisioned_product_id_value_object,
    provisioned_product_stage_value_object,
    provisioned_product_type_value_object,
    provisioning_parameters_value_object,
    region_value_object,
    user_domains_value_object,
    user_id_value_object,
    version_stage_value_object,
)
from app.provisioning.entrypoints.s2s_api import bootstrapper, config
from app.provisioning.entrypoints.s2s_api.model import api_model, api_model_mappers
from app.shared.logging.helpers import clear_auth_headers
from app.shared.middleware import authorization, exception_handler
from app.shared.middleware.metric import metric_handlers
from app.shared.middleware.metric.types import MetricDimensionNames

patch_all()

app_config = config.AppConfig(**config.config)
default_region_name = app_config.get_default_region()
secret_name = app_config.get_audit_logging_key_name()

cors_config = api_gateway.CORSConfig(**app_config.cors_config)
app = api_gateway.APIGatewayRestResolver(
    cors=cors_config,
    strip_prefixes=app_config.get_strip_prefixes(),
    enable_validation=True,
)
app.use(middlewares=[authorization.require_auth_context])
app.enable_swagger(
    path="/_swagger", title="Provisioning BC API", servers=[Server(url=f"{app_config.get_api_base_path()}")]
)

logger = logging.Logger()
tracer = tracing.Tracer()

dependencies = bootstrapper.bootstrap(app_config, logger, app)

TAG_AVAILABLE_PRODUCTS = "Available Products"
TAG_PROVISIONED_PRODUCTS = "Provisioned Products"
PROVISIONING_S2S_API_USER = "PROVISIONING_S2S_API_USER"


@tracer.capture_method
@app.get("/projects/<project_id>/products/available", tags=[TAG_AVAILABLE_PRODUCTS])
def get_available_products(
    project_id: str,
    product_type: Annotated[list[str] | None, Query(alias="productType")] = None,
    filter: Annotated[list[str], Query(alias="filter")] = None,
) -> api_gateway.Response[api_model.GetAvailableProductsResponse]:
    """
    Lists available products associated to a project. Clients can filter results when providing product ids in filter
    query parameter.
    """
    products = dependencies.products_domain_qry_srv.get_available_products(
        project_id=project_id_value_object.from_str(project_id),
        user_roles=[authorization.VirtualWorkbenchRoles.Admin],
        product_type=product_type_value_object.from_str(product_type.pop() if product_type else None),
        product_id_filter=product_id_value_object.from_list(filter) if filter else None,
    )

    products_parsed = [api_model.AvailableProduct.parse_obj(product) for product in products]

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetAvailableProductsResponse(availableProducts=products_parsed),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.post("/projects/<project_id>/products/provisioned", tags=[TAG_PROVISIONED_PRODUCTS])
def launch_product(
    launch_product_request: api_model.LaunchProductRequest,
    project_id: str,
) -> api_gateway.Response[api_model.LaunchProductResponse]:

    command = launch_product_command.LaunchProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.get_new_provisioned_product_id(),
        project_id=project_id_value_object.from_str(project_id),
        user_id=user_id_value_object.from_str(launch_product_request.userName.upper()),
        user_domains=user_domains_value_object.from_list([]),
        product_id=product_id_value_object.from_str(launch_product_request.productId),
        version_id=product_version_id_value_object.from_str(launch_product_request.versionId),
        provisioning_parameters=provisioning_parameters_value_object.from_list(
            [p.dict() for p in launch_product_request.provisioningParameters]
        ),
        additional_configurations=additional_configurations_value_object.from_list(
            launch_product_request.additionalConfigurations
        ),
        stage=provisioned_product_stage_value_object.from_str(launch_product_request.stage),
        region=region_value_object.from_str(launch_product_request.region),
        user_ip_address=ip_address_value_object.from_str(
            app.current_event.raw_event.get("requestContext").get("identity").get("sourceIp")
        ),
        deployment_option=deployment_option_value_object.multi_az(),
    )

    dependencies.command_bus.handle(command)

    return api_gateway.Response(
        status_code=HTTPStatus.ACCEPTED,
        body=api_model.LaunchProductResponse(
            provisionedProductId=command.provisioned_product_id.value,
        ),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get("/projects/<project_id>/products/<product_id>/versions", tags=[TAG_AVAILABLE_PRODUCTS])
def get_available_product_versions(
    project_id: str,
    product_id: str,
) -> api_gateway.Response[api_model.GetAvailableProductVersionsResponse]:
    """Get available product versions by stage and region."""

    stage = None
    if stage_str := app.current_event.get_query_string_value("stage", None):
        stage = version_stage_value_object.from_str(stage_str)

    region = None
    if region_str := app.current_event.get_query_string_value("region", None):
        region = region_value_object.from_str(region_str)

    versions = dependencies.versions_domain_qry_srv.get_versions_ready_for_provisioning(
        product_id=product_id_value_object.from_str(product_id),
        stage=stage,
        region=region,
        return_technical_params=False,
    )

    versions_parsed = [api_model.AvailableVersionDistribution.parse_obj(version) for version in versions]

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetAvailableProductVersionsResponse(availableProductVersions=versions_parsed),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get("/projects/<project_id>/products/provisioned/<provisioned_product_id>", tags=[TAG_PROVISIONED_PRODUCTS])
def get_provisioned_product(
    project_id: str,
    provisioned_product_id: str,
) -> api_gateway.Response[api_model.GetProvisionedProductResponse]:
    (
        provisioned_product_entity,
        version_metadata,
    ) = dependencies.virtual_targets_domain_qry_srv.get_provisioned_product(
        project_id=project_id_value_object.from_str(project_id),
        provisioned_product_id=provisioned_product_id_value_object.from_str(provisioned_product_id),
        return_technical_params=False,
    )
    provisioned_product_parsed = api_model.ProvisionedProduct.parse_obj(
        api_model_mappers.map_provisioned_product(provisioned_product_entity)
    )
    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetProvisionedProductResponse(
            provisionedProduct=provisioned_product_parsed,
            versionMetadata=version_metadata,
        ),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.put("/projects/<project_id>/products/provisioned/<provisioned_product_id>/remove", tags=[TAG_PROVISIONED_PRODUCTS])
def remove_provisioned_product(
    project_id: str,
    provisioned_product_id: str,
) -> api_gateway.Response[api_model.RemoveProvisionedProductResponse]:
    dependencies.command_bus.handle(
        remove_provisioned_product_command.RemoveProvisionedProductCommand(
            provisioned_product_id=provisioned_product_id_value_object.from_str(provisioned_product_id),
            project_id=project_id_value_object.from_str(project_id),
            user_id=user_id_value_object.from_str(PROVISIONING_S2S_API_USER, user_id_value_object.UserIdType.Service),
        )
    )
    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.RemoveProvisionedProductResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.patch(
    "/projects/<project_id>/products/provisioned/<provisioned_product_id>/start", tags=[TAG_PROVISIONED_PRODUCTS]
)
def start_provisioned_product(
    project_id: str,
    provisioned_product_id: str,
) -> api_gateway.Response[api_model.StartProvisionedProductResponse]:
    dependencies.command_bus.handle(
        initiate_provisioned_product_start_command.InitiateProvisionedProductStartCommand(
            provisioned_product_id=provisioned_product_id_value_object.from_str(provisioned_product_id),
            project_id=project_id_value_object.from_str(project_id),
            user_id=user_id_value_object.from_str(PROVISIONING_S2S_API_USER, user_id_value_object.UserIdType.Service),
            user_ip_address=ip_address_value_object.from_str(
                app.current_event.raw_event.get("requestContext").get("identity").get("sourceIp")
            ),
        )
    )
    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.StartProvisionedProductResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.patch("/projects/<project_id>/products/provisioned/<provisioned_product_id>/stop", tags=[TAG_PROVISIONED_PRODUCTS])
def stop_provisioned_product(
    project_id: str,
    provisioned_product_id: str,
) -> api_gateway.Response[api_model.StopProvisionedProductResponse]:
    dependencies.command_bus.handle(
        initiate_provisioned_product_stop_command.InitiateProvisionedProductStopCommand(
            provisioned_product_id=provisioned_product_id_value_object.from_str(provisioned_product_id),
            project_id=project_id_value_object.from_str(project_id),
            user_id=user_id_value_object.from_str(PROVISIONING_S2S_API_USER, user_id_value_object.UserIdType.Service),
        )
    )
    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.StopProvisionedProductResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get("/projects/<project_id>/products/provisioned", tags=[TAG_PROVISIONED_PRODUCTS])
def get_project_provisioned_products_paginated(
    project_id: str,
    page_size: Annotated[list[int] | None, Query(alias="pageSize")] = None,
    paging_key: Annotated[list[str] | None, Query(alias="pagingKey")] = None,
    product_name: Annotated[list[str] | None, Query(alias="productName")] = None,
    version_name: Annotated[list[str] | None, Query(alias="versionName")] = None,
    product_type: Annotated[list[str] | None, Query(alias="productType")] = None,
    owner: Annotated[list[str] | None, Query(alias="owner")] = None,
    status: Annotated[list[str] | None, Query(alias="status")] = None,
    stage: Annotated[list[str] | None, Query(alias="stage")] = None,
    experimental: Annotated[list[bool] | None, Query(alias="experimental")] = None,
) -> api_gateway.Response[api_model.GetPaginatedProvisionedProductsResponse]:
    if paging_key:
        paging_key = unquote(paging_key.pop())
        paging_key = json.loads(paging_key)

    provisioned_products, paging_key = dependencies.virtual_targets_domain_qry_srv.get_paginated_provisioned_products(
        project_id=project_id_value_object.from_str(project_id),
        page_size=page_size.pop() if page_size else app_config.get_default_page_size(),
        paging_key=paging_key,
        product_name=product_name_value_object.from_str(product_name.pop()) if product_name else None,
        version_name=product_version_name_value_object.from_str(version_name.pop()) if version_name else None,
        owner=user_id_value_object.from_str(owner.pop()) if owner else None,
        status=product_status_value_object.from_str(status.pop()) if status else None,
        stage=provisioned_product_stage_value_object.from_str(stage.pop()) if stage else None,
        provisioned_product_type=(
            provisioned_product_type_value_object.from_str(product_type.pop()) if product_type else None
        ),
        experimental=experimental.pop() if experimental else None,
    )

    paging_key = json.dumps(paging_key) if paging_key else None

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetPaginatedProvisionedProductsResponse(
            provisionedProducts=[api_model_mappers.map_provisioned_product(pp) for pp in provisioned_products],
            pagingKey=paging_key,
        ),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_lambda_handler  # type: ignore
@logger.inject_lambda_context  # type: ignore
@exception_handler.handle_exceptions(user_exceptions=[domain_exception.DomainException], cors_config=cors_config)
@metric_handlers.report_invocation_metrics(
    dimensions={MetricDimensionNames.ByAPI: "RestAPI"},
    region_name=default_region_name,
    secret_name=secret_name,
)
def handler(
    event: dict,
    context: typing.LambdaContext,
):
    logger.info(clear_auth_headers(event))
    return app.resolve(event, context)
