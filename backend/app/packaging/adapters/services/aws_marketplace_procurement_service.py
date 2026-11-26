from decimal import Decimal
from typing import Any, NoReturn, Optional

import boto3
from aws_lambda_powertools import logging
from botocore.exceptions import ClientError

from app.packaging.adapters.exceptions import adapter_exception
from app.packaging.domain.exceptions.marketplace_conflict_exception import MarketplaceConflictException
from app.packaging.domain.exceptions.marketplace_request_rejected_exception import MarketplaceRequestRejectedException
from app.packaging.domain.ports.marketplace_procurement_service import MarketplaceProcurementService
from app.packaging.domain.read_models.agreement_request import (
    AcceptedAgreement,
    AgreementChargeSummary,
    AgreementRequestQuote,
)

logger = logging.Logger()

MARKETPLACE_AGREEMENT = "marketplace-agreement"
# Discovery + Agreements APIs are only available in us-east-1.
MARKETPLACE_REGION = "us-east-1"
NEW_INTENT = "NEW"
CONFLICT_ERROR_CODE = "ConflictException"
VALIDATION_ERROR_CODE = "ValidationException"
CANCEL_NOT_SUPPORTED_HINT = (
    "AWS does not cancel an agreement in the first minutes after it was accepted "
    "(refused for at least 77 seconds in a live test, accepted after 158). "
    "Try again in a few minutes, or cancel it in the AWS Marketplace console under Manage subscriptions."
)


def _raise_write_error(e: ClientError, message: str, rejection_hint: Optional[str] = None) -> NoReturn:
    """Re-raise a failed Agreements API write in the domain's terms.

    A ``ConflictException`` becomes :class:`MarketplaceConflictException`
    carrying AWS's identification of the conflicting resource, because a
    conflict can mean the write already happened (a replay) and the command
    handler needs to tell that apart. When the caller passes a
    ``rejection_hint`` (create, accept and cancel), a ``ValidationException`` becomes
    :class:`MarketplaceRequestRejectedException`, which the API reports as a
    400 with AWS's reason and the hint. Every other ``ClientError`` stays an
    ``AdapterException``.
    """
    code = e.response.get("Error", {}).get("Code")
    if code == CONFLICT_ERROR_CODE:
        raise MarketplaceConflictException(
            message,
            resource_type=e.response.get("resourceType"),
            resource_id=e.response.get("resourceId"),
        ) from e
    if code == VALIDATION_ERROR_CODE and rejection_hint is not None:
        raise MarketplaceRequestRejectedException(f"{message} {rejection_hint}".strip()) from e
    raise adapter_exception.AdapterException(message) from e


class AwsMarketplaceProcurementService(MarketplaceProcurementService):
    """AWS-backed adapter for the buyer-side Agreements API write surface
    (``CreateAgreementRequest`` / ``AcceptAgreementRequest`` /
    ``CancelAgreement``).

    Paired with :class:`AwsMarketplaceOfferDiscoveryService`, this closes
    the "quote → purchase → manage" loop at the ports/adapters layer.

    ``ConflictException`` from any of the three writes is raised as
    :class:`MarketplaceConflictException`; any other ``ClientError`` is
    raised as ``AdapterException``.
    """

    def __init__(self, region: str, boto_session: Any = None):
        self._region = region
        self._boto_session = boto_session

    def _get_client(self):
        return (
            self._boto_session.client(MARKETPLACE_AGREEMENT, region_name=MARKETPLACE_REGION)
            if self._boto_session
            else boto3.client(MARKETPLACE_AGREEMENT, region_name=MARKETPLACE_REGION)
        )

    def create_agreement_request(
        self,
        client_token: str,
        agreement_proposal_identifier: str,
        requested_terms: list[dict[str, Any]],
    ) -> AgreementRequestQuote:
        try:
            response = self._get_client().create_agreement_request(
                clientToken=client_token,
                intent=NEW_INTENT,
                agreementProposalIdentifier=agreement_proposal_identifier,
                requestedTerms=requested_terms,
            )
        except ClientError as e:
            logger.warning("CreateAgreementRequest(proposal=%s) failed: %s", agreement_proposal_identifier, e)
            _raise_write_error(
                e,
                f"Failed to create Marketplace agreement request for proposal {agreement_proposal_identifier}: {e}",
                rejection_hint="",
            )
        return AgreementRequestQuote(
            agreementRequestId=response["agreementRequestId"],
            chargeSummary=self._parse_charge_summary(response.get("chargeSummary")),
        )

    def accept_agreement_request(self, agreement_request_id: str) -> AcceptedAgreement:
        try:
            response = self._get_client().accept_agreement_request(agreementRequestId=agreement_request_id)
        except ClientError as e:
            logger.warning("AcceptAgreementRequest(%s) failed: %s", agreement_request_id, e)
            _raise_write_error(
                e,
                f"Failed to accept Marketplace agreement request {agreement_request_id}: {e}",
                rejection_hint="",
            )
        return AcceptedAgreement(agreementId=response["agreementId"])

    def cancel_agreement(self, agreement_id: str) -> None:
        try:
            self._get_client().cancel_agreement(agreementId=agreement_id)
        except ClientError as e:
            logger.warning("CancelAgreement(%s) failed: %s", agreement_id, e)
            _raise_write_error(
                e,
                f"Failed to cancel Marketplace agreement {agreement_id}: {e}",
                rejection_hint=CANCEL_NOT_SUPPORTED_HINT,
            )

    @staticmethod
    def _parse_charge_summary(payload: Any) -> AgreementChargeSummary | None:
        """Project the AWS ``ChargeSummary`` (``newAgreementValue``,
        ``newAgreementValueAfterTax``, ``currencyCode``) into the
        domain-side :class:`AgreementChargeSummary`.

        AWS returns ``newAgreementValue`` as a ``BoundedString`` (string
        that may or may not parse to a Decimal). We coerce defensively —
        if parsing fails, the field is dropped rather than propagated as
        garbage.
        """
        if not payload or not isinstance(payload, dict):
            return None
        raw_value = payload.get("newAgreementValue")
        raw_after_tax = payload.get("newAgreementValueAfterTax")
        return AgreementChargeSummary(
            newAgreementValue=_coerce_decimal(raw_value),
            newAgreementValueAfterTax=_coerce_decimal(raw_after_tax),
            currencyCode=payload.get("currencyCode"),
        )


def _coerce_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (ValueError, ArithmeticError):
        return None
