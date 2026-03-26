from app.publishing.domain.commands import (
    publish_version_command,
    rename_version_distributions_command,
    unpublish_product_command,
    unpublish_version_command,
    update_product_availability_command,
)
from app.publishing.domain.value_objects import (
    aws_account_id_value_object,
    event_name_value_object,
    product_id_value_object,
    project_id_value_object,
    region_value_object,
    version_id_value_object,
)


def test_handler_product_version_ami_shared_event(
    mock_dependencies,
    generate_event,
    lambda_context,
    product_version_ami_shared_event_payload,
    mock_publish_version_command_handler,
):
    # ARRANGE
    from app.publishing.entrypoints.domain_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event(
        detail_type="ProductVersionAmiShared",
        detail=product_version_ami_shared_event_payload,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mock_publish_version_command_handler.assert_called_once_with(
        publish_version_command.PublishVersionCommand(
            productId=product_id_value_object.from_str(product_version_ami_shared_event_payload["productId"]),
            versionId=version_id_value_object.from_str(product_version_ami_shared_event_payload["versionId"]),
            awsAccountId=aws_account_id_value_object.from_str(product_version_ami_shared_event_payload["awsAccountId"]),
            previousEventName=event_name_value_object.from_str(
                product_version_ami_shared_event_payload["previousEventName"]
            ),
        )
    )


def test_product_version_name_updated_event(
    mock_dependencies,
    generate_event,
    lambda_context,
    product_version_name_updated_event_payload,
    mock_rename_version_distributions_command_handler,
):
    from app.publishing.entrypoints.domain_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event(
        detail_type="ProductVersionNameUpdated",
        detail=product_version_name_updated_event_payload,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mock_rename_version_distributions_command_handler.assert_called_once_with(
        rename_version_distributions_command.RenameVersionDistributionsCommand(
            productId=product_id_value_object.from_str(product_version_name_updated_event_payload["productId"]),
            versionId=version_id_value_object.from_str(product_version_name_updated_event_payload["versionId"]),
            awsAccountId=aws_account_id_value_object.from_str(
                product_version_name_updated_event_payload["awsAccountId"]
            ),
        )
    )


def test_product_archiving_started_handler(
    mock_dependencies,
    generate_event,
    lambda_context,
    product_archiving_started_event_payload,
    mock_unpublish_product_command_handler,
):
    from app.publishing.entrypoints.domain_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event(
        detail_type="ProductArchivingStarted",
        detail=product_archiving_started_event_payload,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mock_unpublish_product_command_handler.assert_called_once_with(
        unpublish_product_command.UnpublishProductCommand(
            projectId=project_id_value_object.from_str(product_archiving_started_event_payload["projectId"]),
            productId=product_id_value_object.from_str(product_archiving_started_event_payload["productId"]),
        )
    )


def test_product_version_retirement_started_handler(
    mock_dependencies,
    generate_event,
    lambda_context,
    product_version_retire_started_event_payload,
    mock_unpublish_version_command_handler,
):
    from app.publishing.entrypoints.domain_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event(
        detail_type="ProductVersionRetirementStarted",
        detail=product_version_retire_started_event_payload,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mock_unpublish_version_command_handler.assert_called_once_with(
        unpublish_version_command.UnpublishVersionCommand(
            productId=product_id_value_object.from_str(product_version_retire_started_event_payload["productId"]),
            versionId=version_id_value_object.from_str(product_version_retire_started_event_payload["versionId"]),
            awsAccountId=aws_account_id_value_object.from_str(
                product_version_retire_started_event_payload["awsAccountId"]
            ),
            region=region_value_object.from_str(product_version_retire_started_event_payload["region"]),
        )
    )


def test_product_version_published_handler(
    mock_dependencies,
    generate_event,
    lambda_context,
    product_version_published_event_payload,
    mock_update_product_availability_command_handler,
):
    from app.publishing.entrypoints.domain_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event(
        detail_type="ProductVersionPublished",
        detail=product_version_published_event_payload,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mock_update_product_availability_command_handler.assert_called_once_with(
        update_product_availability_command.UpdateProductAvailabilityCommand(
            projectId=project_id_value_object.from_str(product_version_published_event_payload["projectId"]),
            productId=product_id_value_object.from_str(product_version_published_event_payload["productId"]),
        )
    )


def test_product_version_unpublished_handler(
    mock_dependencies,
    generate_event,
    lambda_context,
    product_version_unpublished_event_payload,
    mock_update_product_availability_command_handler,
):
    from app.publishing.entrypoints.domain_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event(
        detail_type="ProductVersionUnpublished",
        detail=product_version_unpublished_event_payload,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mock_update_product_availability_command_handler.assert_called_once_with(
        update_product_availability_command.UpdateProductAvailabilityCommand(
            projectId=project_id_value_object.from_str(product_version_unpublished_event_payload["projectId"]),
            productId=product_id_value_object.from_str(product_version_unpublished_event_payload["productId"]),
        )
    )


def test_product_unpublished_handler(
    mock_dependencies,
    generate_event,
    lambda_context,
    product_unpublished_event_payload,
    mock_update_product_availability_command_handler,
):
    from app.publishing.entrypoints.domain_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event(detail_type="ProductUnpublished", detail=product_unpublished_event_payload)

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mock_update_product_availability_command_handler.assert_called_once_with(
        update_product_availability_command.UpdateProductAvailabilityCommand(
            projectId=project_id_value_object.from_str(product_unpublished_event_payload["projectId"]),
            productId=product_id_value_object.from_str(product_unpublished_event_payload["productId"]),
        )
    )
