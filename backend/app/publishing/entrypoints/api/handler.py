from http import HTTPStatus

from aws_lambda_powertools import logging, tracing
from aws_lambda_powertools.event_handler import api_gateway, content_types
from aws_lambda_powertools.event_handler.openapi.models import Server
from aws_lambda_powertools.event_handler.openapi.params import Query
from aws_lambda_powertools.shared.types import Annotated
from aws_lambda_powertools.utilities import typing
from aws_xray_sdk.core import patch_all

from app.publishing.domain.commands import (
    archive_product_command,
    create_product_command,
    create_version_command,
    promote_version_command,
    restore_version_command,
    retire_version_command,
    retry_version_command,
    set_recommended_version_command,
    update_version_command,
    validate_version_command,
)
from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.value_objects import (
    ami_id_value_object,
    aws_account_id_value_object,
    image_digest_value_object,
    image_tag_value_object,
    major_version_name_value_object,
    product_description_value_object,
    product_id_value_object,
    product_name_value_object,
    product_type_value_object,
    project_id_value_object,
    region_value_object,
    stage_value_object,
    tech_id_value_object,
    tech_name_value_object,
    user_id_value_object,
    user_role_value_object,
    version_description_value_object,
    version_id_value_object,
    version_release_type_value_object,
    version_template_definition_value_object,
)
from app.publishing.entrypoints.api import bootstrapper, config
from app.publishing.entrypoints.api.model import api_model
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
    path="/_swagger",
    title="Publishing BC API",
    servers=[Server(url=f"{app_config.get_api_base_path()}")],
)

logger = logging.Logger()
tracer = tracing.Tracer()

dependencies = bootstrapper.bootstrap(app_config, logger)

TAG_PRODUCTS = "Products"
TAG_PRODUCT_VERSIONS = "Product Versions"
TAG_AMI = "Images"
logger.debug("Dummy change to trigger env variable deployment.")


@tracer.capture_method
@app.post("/projects/<project_id>/products", tags=[TAG_PRODUCTS])
def create_product(
    request: api_model.CreateProductRequest,
    project_id: str,
) -> api_gateway.Response[api_model.CreateProductResponse]:
    """Creates a new product."""

    product_id = product_id_value_object.generate_product_id()

    # Parse input
    command = create_product_command.CreateProductCommand(
        projectId=project_id_value_object.from_str(project_id),
        productId=product_id_value_object.from_str(product_id),
        productName=product_name_value_object.from_str(request.productName),
        productType=product_type_value_object.from_str(request.productType),
        productDescription=product_description_value_object.from_str(request.productDescription),
        technologyId=tech_id_value_object.from_str(request.technologyId),
        technologyName=tech_name_value_object.from_str(request.technologyName),
        userId=user_id_value_object.from_str(app.context.get("user_principal").user_name),
    )

    # Call command handler
    dependencies.command_bus.handle(command)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.CreateProductResponse(productId=product_id),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get("/projects/<project_id>/products", tags=[TAG_PRODUCTS])
def get_products(
    project_id: str,
) -> api_gateway.Response[api_model.GetProductsResponse]:
    """Lists products associated to a project."""

    products = dependencies.products_domain_qry_srv.get_products(
        project_id=project_id_value_object.from_str(project_id),
    )

    products_parsed = [api_model.Product.parse_obj(product) for product in products]

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetProductsResponse(products=products_parsed),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get("/projects/<project_id>/products/<product_id>/latest-template", tags=[TAG_PRODUCTS])
def get_latest_template(
    project_id: str,
    product_id: str,
    version_id_param: Annotated[list[str] | None, Query(alias="versionId")] = None,
) -> api_gateway.Response[api_model.GetLatestTemplateResponse]:
    """Gets the latest template for the product."""

    version_id = None
    if version_id_param:
        version_id = version_id_value_object.from_str(version_id_param.pop())

    template = dependencies.template_domain_qry_srv.get_latest_draft_template(
        project_id=project_id_value_object.from_str(project_id),
        product_id=product_id_value_object.from_str(product_id),
        version_id=version_id,
    )

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetLatestTemplateResponse(template=template),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.post("/projects/<project_id>/products/<product_id>/versions", tags=[TAG_PRODUCT_VERSIONS])
def create_product_version(
    request: api_model.CreateProductVersionRequest,
    project_id: str,
    product_id: str,
) -> api_gateway.Response[api_model.CreateProductVersionResponse]:
    """Creates a new product version."""

    # Parse input
    command = create_version_command.CreateVersionCommand(
        amiId=ami_id_value_object.from_str(request.amiId) if request.amiId else None,
        imageTag=(image_tag_value_object.from_str(request.imageTag) if request.imageTag else None),
        imageDigest=(image_digest_value_object.from_str(request.imageDigest) if request.imageDigest else None),
        majorVersionName=(
            major_version_name_value_object.from_int(request.majorVersionName) if request.majorVersionName else None
        ),
        versionReleaseType=version_release_type_value_object.from_str(request.versionReleaseType),
        versionDescription=version_description_value_object.from_str(request.productVersionDescription),
        versionTemplateDefinition=version_template_definition_value_object.from_str(request.versionTemplateDefinition),
        projectId=project_id_value_object.from_str(project_id),
        productId=product_id_value_object.from_str(product_id),
        createdBy=user_id_value_object.from_str(app.context.get("user_principal").user_name),
    )

    # Call command handler
    dependencies.command_bus.handle(command)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.CreateProductVersionResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.post(
    "/projects/<project_id>/products/<product_id>/versions/validate",
    tags=[TAG_PRODUCT_VERSIONS],
)
def validate_product_version(
    request: api_model.ValidateProductVersionRequest,
    project_id: str,
    product_id: str,
) -> api_gateway.Response[api_model.ValidateProductVersionResponse]:
    """Validates the template for a product version."""

    # Parse input
    command = validate_version_command.ValidateVersionCommand(
        projectId=project_id_value_object.from_str(project_id),
        productId=product_id_value_object.from_str(product_id),
        versionTemplateDefinition=version_template_definition_value_object.from_str(request.versionTemplateDefinition),
    )

    # Call command handler
    dependencies.command_bus.handle(command)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.ValidateProductVersionResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.put(
    "/projects/<project_id>/products/<product_id>/versions/<version_id>",
    tags=[TAG_PRODUCT_VERSIONS],
)
def update_product_version(
    request: api_model.UpdateProductVersionRequest,
    project_id: str,
    product_id: str,
    version_id: str,
) -> api_gateway.Response[api_model.UpdateProductVersionResponse]:
    """Updating an existing product version."""

    # Parse input
    command = update_version_command.UpdateVersionCommand(
        amiId=ami_id_value_object.from_str(request.amiId) if request.amiId else None,
        imageTag=(image_tag_value_object.from_str(request.imageTag) if request.imageTag else None),
        imageDigest=(image_digest_value_object.from_str(request.imageDigest) if request.imageDigest else None),
        versionDescription=version_description_value_object.from_str(request.productVersionDescription),
        versionTemplateDefinition=version_template_definition_value_object.from_str(request.versionTemplateDefinition),
        projectId=project_id_value_object.from_str(project_id),
        productId=product_id_value_object.from_str(product_id),
        versionId=version_id_value_object.from_str(version_id),
        lastUpdatedBy=user_id_value_object.from_str(app.context.get("user_principal").user_name),
    )

    # Call command handler
    dependencies.command_bus.handle(command)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.UpdateProductVersionResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.patch(
    "/projects/<project_id>/products/<product_id>/versions/<version_id>",
    tags=[TAG_PRODUCT_VERSIONS],
)
def retry_product_version(
    request: api_model.RetryProductVersionRequest,
    project_id: str,
    product_id: str,
    version_id: str,
) -> api_gateway.Response[api_model.RetryProductVersionResponse]:
    """Retries an existing product version."""

    # Parse input
    command = retry_version_command.RetryVersionCommand(
        projectId=project_id_value_object.from_str(project_id),
        productId=product_id_value_object.from_str(product_id),
        versionId=version_id_value_object.from_str(version_id),
        awsAccountIds=[aws_account_id_value_object.from_str(acc) for acc in request.awsAccountIds],
        lastUpdatedBy=user_id_value_object.from_str(app.context.get("user_principal").user_name),
    )

    # Call command handler
    dependencies.command_bus.handle(command)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.RetryProductVersionResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.post(
    "/projects/<project_id>/products/<product_id>/versions/<version_id>",
    tags=[TAG_PRODUCT_VERSIONS],
)
def promote_product_version(
    request: api_model.PromoteProductVersionRequest,
    project_id: str,
    product_id: str,
    version_id: str,
) -> api_gateway.Response[api_model.PromoteProductVersionResponse]:
    """Promotes an existing product version to QA/PROD"""

    # Parse input
    command = promote_version_command.PromoteVersionCommand(
        projectId=project_id_value_object.from_str(project_id),
        productId=product_id_value_object.from_str(product_id),
        versionId=version_id_value_object.from_str(version_id),
        createdBy=user_id_value_object.from_str(app.context.get("user_principal").user_name),
        userRoles=[user_role_value_object.from_str(role) for role in app.context.get("user_principal").user_roles],
        stage=stage_value_object.from_str(request.stage),
    )

    # Call command handler
    dependencies.command_bus.handle(command)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.PromoteProductVersionResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get(
    "/projects/<project_id>/products/<product_id>/versions/<version_id>",
    tags=[TAG_PRODUCT_VERSIONS],
)
def get_product_version(
    project_id: str, product_id: str, version_id: str
) -> api_gateway.Response[api_model.GetProductVersionResponse]:
    """Get a single product version and its distributions."""
    product, version_summary = dependencies.products_domain_qry_srv.get_product(
        project_id=project_id_value_object.from_str(project_id),
        product_id=product_id_value_object.from_str(product_id),
    )
    summary, distributions, draft_template = dependencies.versions_domain_qry_srv.get_product_version(
        product_id=product_id_value_object.from_str(product_id),
        version_id=version_id_value_object.from_str(version_id),
    )

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetProductVersionResponse(
            product=api_model.Product.parse_obj(product),
            version=api_model.VersionSummary.parse_obj(summary),
            distributions=[api_model.VersionDistribution.parse_obj(d) for d in distributions],
            draft_template=draft_template,
        ),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get("/internal/products/<product_id>/versions/<version_id>", tags=[TAG_PRODUCT_VERSIONS])
def get_product_version_distribution_internal(
    product_id: str,
    version_id: str,
    account_param: Annotated[list[str], Query(alias="awsAccountId")],
) -> api_gateway.Response[api_model.GetProductVersionInternalResponse]:
    """Get a single product version distribution."""

    version_enriched = dependencies.versions_domain_qry_srv.get_version_distribution(
        product_id=product_id_value_object.from_str(product_id),
        version_id=version_id_value_object.from_str(version_id),
        aws_account_id=aws_account_id_value_object.from_str(account_param.pop()),
    )

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetProductVersionInternalResponse(
            version=(
                api_model.AvailableVersionDistributionEnriched.parse_obj(version_enriched) if version_enriched else None
            ),
        ),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.post(
    "/projects/<project_id>/products/<product_id>/versions/<version_id>/restore",
    tags=[TAG_PRODUCT_VERSIONS],
)
def restore_product_version(
    project_id: str,
    product_id: str,
    version_id: str,
) -> api_gateway.Response[api_model.RestoreProductVersionResponse]:
    """Restores a retired product version to DEV"""

    # Parse input
    command = restore_version_command.RestoreVersionCommand(
        projectId=project_id_value_object.from_str(project_id),
        productId=product_id_value_object.from_str(product_id),
        versionId=version_id_value_object.from_str(version_id),
        restoredBy=user_id_value_object.from_str(app.context.get("user_principal").user_name),
    )

    # Call command handler
    restored_version_name = dependencies.command_bus.handle(command)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.RestoreProductVersionResponse(restoredVersionName=restored_version_name),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.put(
    "/projects/<project_id>/products/<product_id>/versions/<version_id>/set-recommended",
    tags=[TAG_PRODUCT_VERSIONS],
)
def set_recommended_product_version(
    project_id: str,
    product_id: str,
    version_id: str,
) -> api_gateway.Response[api_model.SetRecommendedVersionResponse]:
    """Sets the specified version as recommended"""

    # Parse input
    command = set_recommended_version_command.SetRecommendedVersionCommand(
        projectId=project_id_value_object.from_str(project_id),
        productId=product_id_value_object.from_str(product_id),
        versionId=version_id_value_object.from_str(version_id),
        userId=user_id_value_object.from_str(app.context.get("user_principal").user_name),
    )

    # Call command handler
    dependencies.command_bus.handle(command)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.SetRecommendedVersionResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get("/projects/<project_id>/products/<product_id>", tags=[TAG_PRODUCTS])
def get_product(project_id: str, product_id: str) -> api_gateway.Response[api_model.GetProductResponse]:
    """Get a single product and its detail information."""

    product, summaries = dependencies.products_domain_qry_srv.get_product(
        project_id=project_id_value_object.from_str(project_id),
        product_id=product_id_value_object.from_str(product_id),
    )

    product_parsed = api_model.Product.parse_obj(product)
    product_parsed.versions = [api_model.VersionSummary.parse_obj(s) for s in summaries]

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetProductResponse(product=product_parsed),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get(
    "/projects/<project_id>/products/<product_id>/latest-major-versions",
    tags=[TAG_PRODUCT_VERSIONS],
)
def get_latest_major_versions(
    project_id: str,
    product_id: str,
) -> api_gateway.Response[api_model.GetLatestMajorVersionsResponse]:
    """Gets the latest major versions of the product."""

    version_summaries = dependencies.versions_domain_qry_srv.get_latest_major_version_summaries(
        product_id=product_id_value_object.from_str(product_id)
    )
    version_summaries_parsed = [api_model.VersionSummary.parse_obj(vers) for vers in version_summaries]

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetLatestMajorVersionsResponse(versions=version_summaries_parsed),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get(
    "/projects/<project_id>/available-products/<product_id>/versions",
    tags=[TAG_PRODUCT_VERSIONS],
)
def get_available_product_versions(
    project_id: str,
    product_id: str,
    stage_param: Annotated[list[str] | None, Query(alias="stage")] = None,
    region_param: Annotated[list[str] | None, Query(alias="region")] = None,
) -> api_gateway.Response[api_model.GetAvailableProductVersionsResponse]:
    """Get available product versions by stage and region."""

    stage = stage_value_object.from_str(stage_param.pop() if stage_param else None)
    region = region_value_object.from_str(region_param.pop() if region_param else None)

    versions = dependencies.versions_domain_qry_srv.get_versions_ready_for_provisioning(
        product_id=product_id_value_object.from_str(product_id),
        stage=stage,
        region=region,
    )

    versions_parsed = [api_model.AvailableVersionDistribution.parse_obj(version) for version in versions]

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetAvailableProductVersionsResponse(availableProductVersions=versions_parsed),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.delete("/projects/<project_id>/products/<product_id>", tags=[TAG_PRODUCTS])
def archive_product(
    project_id: str,
    product_id: str,
) -> api_gateway.Response[api_model.ArchiveProductResponse]:
    """Archives a product"""

    # Parse input
    command = archive_product_command.ArchiveProductCommand(
        projectId=project_id_value_object.from_str(project_id),
        productId=product_id_value_object.from_str(product_id),
        archivedBy=user_id_value_object.from_str(app.context.get("user_principal").user_name),
    )

    # Call command handler
    dependencies.command_bus.handle(command)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.ArchiveProductResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get("/projects/<project_id>/amis", tags=[TAG_AMI])
def get_amis(project_id: str) -> api_gateway.Response[api_model.GetAmisResponse]:
    """Get a single product and its detail information."""

    amis = dependencies.amis_domain_qry_srv.get_amis(project_id)

    amis_parsed = [api_model.Ami.parse_obj(ami_item) for ami_item in amis]

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetAmisResponse(amis=amis_parsed),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.delete(
    "/projects/<project_id>/products/<product_id>/versions/<version_id>",
    tags=[TAG_PRODUCT_VERSIONS],
)
def retire_product_version(
    request: api_model.RetireProductVersionRequest,
    project_id: str,
    product_id: str,
    version_id: str,
) -> api_gateway.Response[api_model.RetireProductVersionResponse]:
    """Retires product version"""

    # Parse input
    command = retire_version_command.RetireVersionCommand(
        projectId=project_id_value_object.from_str(project_id),
        productId=product_id_value_object.from_str(product_id),
        versionId=version_id_value_object.from_str(version_id),
        retiredBy=user_id_value_object.from_str(app.context.get("user_principal").user_name),
        userRoles=[user_role_value_object.from_str(role) for role in app.context.get("user_principal").user_roles],
        retireReason=request.retireReason,
    )

    # Call command handler
    dependencies.command_bus.handle(command)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.RetireProductVersionResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get("/projects/<project_id>/available-products", tags=[TAG_PRODUCTS])
def get_available_products(
    project_id: str,
    product_type: Annotated[list[str] | None, Query(alias="productType")] = None,
) -> api_gateway.Response[api_model.GetAvailableProductsResponse]:
    """Lists products ready for provisioning associated to a project."""

    product_type = product_type_value_object.from_str(product_type.pop() if product_type else None)

    products = dependencies.products_domain_qry_srv.get_products_ready_for_provisioning(
        project_id=project_id_value_object.from_str(project_id),
        user_roles=[user_role_value_object.from_str(role) for role in app.context.get("user_principal").user_roles],
        product_type=product_type,
    )

    products_parsed = [api_model.AvailableProduct.parse_obj(product) for product in products]

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetAvailableProductsResponse(availableProducts=products_parsed),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get("/internal/available-products/<product_id>/versions", tags=[TAG_PRODUCT_VERSIONS])
def get_available_product_versions_internal(
    product_id: str,
) -> api_gateway.Response[api_model.GetAvailableProductVersionsInternalResponse]:
    """Get available product versions"""

    versions_enriched = dependencies.versions_domain_qry_srv.get_enriched_versions_ready_for_provisioning(
        product_id=product_id_value_object.from_str(product_id)
    )

    versions_parsed = [api_model.AvailableVersionDistributionEnriched.parse_obj(v) for v in versions_enriched]

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetAvailableProductVersionsInternalResponse(availableProductVersions=versions_parsed),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get(
    "/internal/available-products/<product_id>/versions/<version_id>",
    tags=[TAG_PRODUCT_VERSIONS],
)
def get_available_product_version_internal(
    product_id: str,
    version_id: str,
) -> api_gateway.Response[api_model.GetAvailableProductVersionsInternalResponse]:
    """Get available product version"""

    versions_enriched = dependencies.versions_domain_qry_srv.get_enriched_versions_ready_for_provisioning(
        product_id=product_id_value_object.from_str(product_id),
        version_id=version_id_value_object.from_str(version_id),
    )

    versions_parsed = [api_model.AvailableVersionDistributionEnriched.parse_obj(v) for v in versions_enriched]

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetAvailableProductVersionsInternalResponse(availableProductVersions=versions_parsed),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get("/internal/published-amis", tags=[TAG_AMI])
def get_published_amis() -> api_gateway.Response[api_model.GetPublishedAmisResponse]:
    """Gets published AMIs"""

    amis = dependencies.amis_domain_qry_srv.get_used_ami_list()

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetPublishedAmisResponse(amis=amis),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_lambda_handler  # type: ignore
@logger.inject_lambda_context  # type: ignore
@exception_handler.handle_exceptions(
    user_exceptions=[domain_exception.DomainException], cors_config=cors_config
)  # TODO: add custom user exceptions to the array
@metric_handlers.report_invocation_metrics(
    dimensions={MetricDimensionNames.ByAPI: "RestAPI"},
    enable_audit=True,
    region_name=default_region_name,
    secret_name=secret_name,
)
def handler(
    event: dict,
    context: typing.LambdaContext,
):
    logger.info(clear_auth_headers(event))
    return app.resolve(event, context)
