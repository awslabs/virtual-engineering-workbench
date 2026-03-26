import enum
import typing

from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.model import product, shared_ami, version
from app.publishing.domain.ports import image_service
from app.publishing.domain.value_objects import (
    ami_id_value_object,
    aws_account_id_value_object,
    product_id_value_object,
    product_type_value_object,
    region_value_object,
    version_id_value_object,
)
from app.shared.adapters.unit_of_work_v2 import unit_of_work


class ShareAmiDecision(str, enum.Enum):
    Done = "DONE"
    Share = "SHARE"
    Copy = "COPY"
    NOT_REQUIRED = "NOT_REQUIRED"

    def __str__(self):
        return str(self.value)


class SharedAMIsDomainQueryService:
    def __init__(
        self,
        unit_of_work: unit_of_work.UnitOfWork,
        image_svc: image_service.ImageService,
        default_original_ami_region: str,
    ) -> None:
        self._uow = unit_of_work
        self._image_svc = image_svc
        self._default_original_ami_region = default_original_ami_region

    def make_share_ami_decision(
        self,
        product_id: product_id_value_object.ProductIdValueObject,
        version_id: version_id_value_object.VersionIdValueObject,
        aws_account_id: aws_account_id_value_object.AWSAccountIDValueObject,
        product_type: product_type_value_object.ProductTypeValueObject,
    ) -> typing.Tuple[ShareAmiDecision, str, str, str]:
        # Get the version entity & shared ami entity
        shared_ami_entity = None
        with self._uow:
            version_entity: version.Version = self._uow.get_repository(version.VersionPrimaryKey, version.Version).get(
                pk=version.VersionPrimaryKey(
                    productId=product_id.value, versionId=version_id.value, awsAccountId=aws_account_id.value
                )
            )
            # lets add a skip decision is its a container product type
            if product_type.value == product.ProductType.Container:
                return ShareAmiDecision.NOT_REQUIRED, version_entity.region, "", ""
            shared_ami_entity = self._uow.get_repository(shared_ami.SharedAmiPrimaryKey, shared_ami.SharedAmi).get(
                pk=shared_ami.SharedAmiPrimaryKey(
                    originalAmiId=version_entity.originalAmiId, awsAccountId=aws_account_id.value
                )
            )

        # Make the decision
        copied_ami_id = None
        if shared_ami_entity:
            decision = ShareAmiDecision.Done
            copied_ami_id = shared_ami_entity.copiedAmiId
        elif version_entity.region == self._default_original_ami_region:
            decision = ShareAmiDecision.Share
        elif version_entity.region != self._default_original_ami_region:
            decision = ShareAmiDecision.Copy
        else:
            raise domain_exception.DomainException("Unsupported logic when making the decision")

        return decision, version_entity.region, version_entity.originalAmiId, copied_ami_id

    def verify_copy(
        self,
        region: region_value_object.RegionValueObject,
        copied_ami_id: ami_id_value_object.AmiIdValueObject,
    ) -> bool:
        copied_ami_status = self._image_svc.get_copied_ami_status(copied_ami_id.value, region.value)
        if copied_ami_status == "available":
            return True
        elif copied_ami_status == "pending":
            return False
        else:
            raise domain_exception.DomainException(f"Unsupported copied ami status {copied_ami_status}")
