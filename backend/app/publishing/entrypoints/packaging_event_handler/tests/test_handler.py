from freezegun import freeze_time

from app.publishing.domain.read_models import ami, component_version_detail
from app.publishing.domain.value_objects import ami_id_value_object


@freeze_time("2024-03-06")
def test_image_registration_completed_event(
    mock_dependencies,
    generate_event,
    lambda_context,
    image_registration_completed_event_payload,
    mock_update_ami_read_model_event_handler,
):
    # ARRANGE
    from app.publishing.entrypoints.packaging_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event(
        detail_type="ImageRegistrationCompleted",
        detail=image_registration_completed_event_payload,
    )
    new_ami = ami.Ami(
        projectId="proj-12345",
        amiId=image_registration_completed_event_payload["amiId"],
        amiName=image_registration_completed_event_payload["amiName"],
        amiDescription=image_registration_completed_event_payload["amiDescription"],
        createDate=image_registration_completed_event_payload["createDate"],
        lastUpdateDate="2024-03-06T00:00:00+00:00",
        componentVersionDetails=[
            component_version_detail.ComponentVersionDetail(
                componentName=cmp["componentName"],
                componentVersionType=cmp["componentVersionType"],
                softwareVendor=cmp["softwareVendor"],
                softwareVersion=cmp["softwareVersion"],
                licenseDashboard=cmp["licenseDashboard"],
                notes=cmp["notes"],
            )
            for cmp in image_registration_completed_event_payload["componentsVersionsDetails"]
        ],
        osVersion="Ubuntu 24",
        platform="Linux",
        architecture="amd64",
        integrations=["GitHub"],
    )
    retired_ami_ids = image_registration_completed_event_payload["retiredAmiIds"]

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mock_update_ami_read_model_event_handler.assert_called_once_with(new_ami, retired_ami_ids)


def test_image_deregistered_event(
    mock_dependencies,
    generate_event,
    lambda_context,
    image_deregistered_event_payload,
    mock_delete_ami_read_model_event_handler,
):
    # ARRANGE
    from app.publishing.entrypoints.packaging_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event(detail_type="ImageDeregistered", detail=image_deregistered_event_payload)

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mock_delete_ami_read_model_event_handler.assert_called_once_with(
        ami_id_value_object.from_str(image_deregistered_event_payload["amiId"])
    )


def test_automated_image_registration_completed_event(
    mock_dependencies,
    generate_event,
    lambda_context,
    automated_image_registration_completed_event_payload,
    mock_create_automated_version_event_handler,
):
    # ARRANGE
    from app.publishing.entrypoints.packaging_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event(
        detail_type="AutomatedImageRegistrationCompleted",
        detail=automated_image_registration_completed_event_payload,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mock_create_automated_version_event_handler.assert_called_once()
    call_kwargs = mock_create_automated_version_event_handler.call_args[1]
    assert call_kwargs["ami_id"] == "ami-12345678"
    assert call_kwargs["product_id"] == "product-123"
    assert call_kwargs["project_id"] == "project-456"
    assert call_kwargs["release_type"] == "MINOR"
    assert call_kwargs["user_id"] == "T123456"
    assert call_kwargs["os_version"] == "Ubuntu 24"
    assert call_kwargs["platform"] == "Linux"
    assert call_kwargs["architecture"] == "amd64"
    assert call_kwargs["integrations"] == ["GitHub"]
    assert len(call_kwargs["component_version_details"]) == 1


def test_automated_image_registration_completed_event_with_exception(
    mock_dependencies,
    generate_event,
    lambda_context,
    automated_image_registration_completed_event_payload,
    mock_create_automated_version_event_handler,
):
    # ARRANGE
    from app.publishing.entrypoints.packaging_event_handler import handler

    handler.dependencies = mock_dependencies
    mock_create_automated_version_event_handler.side_effect = Exception("Test error")

    event_bridge_event = generate_event(
        detail_type="AutomatedImageRegistrationCompleted",
        detail=automated_image_registration_completed_event_payload,
    )

    # ACT & ASSERT - Should not raise an exception
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mock_create_automated_version_event_handler.assert_called_once()
