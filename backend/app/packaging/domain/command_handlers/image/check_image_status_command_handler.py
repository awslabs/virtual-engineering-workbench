from app.packaging.domain.commands.image import check_image_status_command
from app.packaging.domain.model.image import image
from app.packaging.domain.ports import image_query_service


def handle(
    command: check_image_status_command.CheckImageStatusCommand,
    image_query_service: image_query_service.ImageQueryService,
) -> dict[str, str]:
    image_obj = image_query_service.get_image(project_id=command.projectId.value, image_id=command.imageId.value)

    if not image_obj:
        return {"imageStatus": image.ImageStatus.Failed.value, "imageId": command.imageId.value, "imageUpstreamId": ""}

    if image_obj.status == image.ImageStatus.Created:
        return {
            "imageStatus": image.ImageStatus.Created.value,
            "imageId": command.imageId.value,
            "imageUpstreamId": image_obj.imageUpstreamId,
        }
    elif image_obj.status == image.ImageStatus.Failed:
        return {"imageStatus": image.ImageStatus.Failed.value, "imageId": command.imageId.value, "imageUpstreamId": ""}
    else:
        return {
            "imageStatus": image.ImageStatus.Creating.value,
            "imageId": command.imageId.value,
            "imageUpstreamId": "",
        }
