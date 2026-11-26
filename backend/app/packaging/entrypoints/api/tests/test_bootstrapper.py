import logging

import assertpy

from app.packaging.entrypoints.api import bootstrapper, config


def test_bootstrapper():
    # ARRANGE
    app_config = config.AppConfig(**config.config)

    # ACT
    dependencies = bootstrapper.bootstrap(app_config=app_config, logger=logging.getLogger())

    # ASSERT
    assertpy.assert_that(dependencies).is_not_none()


def test_marketplace_commands_report_a_put_events_entry_failure():
    """PutEvents rejects an entry inside an HTTP 200 response. For the
    Marketplace write commands that must reach the publish-failure metric
    rather than pass as a successful publish."""
    # ARRANGE
    from unittest import mock

    from app.packaging.adapters.services import aws_marketplace_discovery_service, aws_marketplace_procurement_service
    from app.packaging.domain.command_handlers.marketplace import event_publication
    from app.packaging.domain.commands.marketplace import cancel_agreement_command
    from app.packaging.domain.value_objects.marketplace import agreement_id_value_object
    from app.shared.api import aws_events_api
    from app.shared.instrumentation import power_tools_metrics

    failed = aws_events_api.PutEventsResponse(
        FailedEntryCount=1, Entries=[{"ErrorCode": "InternalFailure", "ErrorMessage": "try again"}]
    )
    app_config = config.AppConfig(**config.config)
    with (
        mock.patch.object(aws_events_api.AWSEventsApi, "put_event", return_value=failed),
        mock.patch.object(aws_marketplace_procurement_service.AwsMarketplaceProcurementService, "cancel_agreement"),
        mock.patch.object(
            aws_marketplace_discovery_service.AwsMarketplaceDiscoveryService, "is_ami_agreement", return_value=True
        ),
        mock.patch.object(power_tools_metrics.PowerToolsMetrics, "publish_counter") as publish_counter,
    ):
        dependencies = bootstrapper.bootstrap(app_config=app_config, logger=logging.getLogger())

        # ACT
        dependencies.command_bus.handle(
            command=cancel_agreement_command.CancelAgreementCommand(
                agreementId=agreement_id_value_object.from_str("agmt-1234567890abc")
            )
        )

    # ASSERT
    metric_names = [call.kwargs.get("metric_name") for call in publish_counter.call_args_list]
    assertpy.assert_that(metric_names).contains(event_publication.PUBLISH_FAILED_METRIC)


def test_bootstrapper_wires_aws_published_resolve_endpoint():
    """The resolve endpoint's query service must get the resolver instance.

    Built-but-unwired would not fail anything: the endpoint would answer
    "cannot resolve" for every product.
    """
    from app.packaging.domain.query_services.aws_published_ami_domain_query_service import (
        AwsPublishedAmiDomainQueryService,
    )

    app_config = config.AppConfig(**config.config)
    dependencies = bootstrapper.bootstrap(app_config=app_config, logger=logging.getLogger())

    svc = dependencies.aws_published_ami_qry_svc
    assertpy.assert_that(svc).is_instance_of(AwsPublishedAmiDomainQueryService)
    assertpy.assert_that(svc._resolver).is_same_as(dependencies.aws_published_ami_resolver)
