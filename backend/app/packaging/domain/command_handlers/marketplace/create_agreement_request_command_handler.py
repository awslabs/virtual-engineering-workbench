import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.packaging.domain.command_handlers.marketplace import event_publication
from app.packaging.domain.commands.marketplace import create_agreement_request_command
from app.packaging.domain.events.marketplace import agreement_request_created
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.exceptions.marketplace_conflict_exception import MarketplaceConflictException
from app.packaging.domain.exceptions.marketplace_request_rejected_exception import MarketplaceRequestRejectedException
from app.packaging.domain.ports.marketplace_agreement_service import MarketplaceAgreementService
from app.packaging.domain.ports.marketplace_offer_discovery_service import MarketplaceOfferDiscoveryService
from app.packaging.domain.ports.marketplace_procurement_service import MarketplaceProcurementService
from app.packaging.domain.read_models import agreement_request
from app.shared.adapters.message_bus import message_bus
from app.shared.instrumentation import metrics


def _guard_no_duplicate_active_agreement(
    offer_id: str,
    agreement_svc: MarketplaceAgreementService,
) -> None:
    """Reject the request if the account already has an ACTIVE agreement
    for this offer.

    AWS Marketplace's ``CreateAgreementRequest`` rejects duplicate
    subscriptions with a generic ``ValidationException: This action is
    not supported.`` — the same string it uses for AWS-managed AMIs,
    which is a completely different case. That makes the error deeply
    misleading to users.

    We pre-check by listing active agreements (server-side, cheap) and
    surface a clean, actionable message instead of letting the AWS
    error bubble up. If the account still hits the AWS-side rejection
    after this check (race condition, unusual account state), the
    generic AWS message still comes through unchanged.
    """
    try:
        active = agreement_svc.list_active_agreements()
    except Exception:
        # Graceful degradation: if we can't list agreements (permissions,
        # transient error), skip the pre-check and let AWS have the final
        # say. Better a slightly worse error message than blocking a
        # legitimate subscribe attempt on our own bug.
        return
    for a in active:
        if a.offerId == offer_id:
            raise domain_exception.DomainException(
                f"You already have an active subscription to this offer "
                f"(agreement {a.agreementId}). Cancel it first if you want to re-subscribe, "
                f"or use Import AMI to launch the AMI you're already entitled to."
            )


def _guard_ami_only(
    offer_id: str,
    offer_discovery_svc: MarketplaceOfferDiscoveryService,
) -> str:
    """Enforce the AMI-only, single-product invariant and return the
    offer's agreement proposal identifier.

    Mirrors the pattern set by the ``ImportImageCommand`` handler,
    which re-validates the AMI's product code against AWS rather than
    trusting the caller. Here we resolve the offer and every product it
    references, and reject the request unless each product's fulfillment
    options include ``AMAZON_MACHINE_IMAGE``.

    Rejects early on:

    * offers with no associated products (malformed AWS response)
    * offers that are part of a multi-product offer set (bundles are out
      of scope)
    * offers that reference more than one product (single-product AMI
      offers only)
    * offers whose associated product is not AMI-type per its fulfillment
      option summary
    """
    offer = offer_discovery_svc.get_offer(offer_id)
    if not offer.associatedProducts:
        raise domain_exception.DomainException(
            f"Marketplace offer {offer_id} has no associated products; refusing to create agreement request."
        )
    if any(p.partOfOfferSet for p in offer.associatedProducts):
        raise domain_exception.DomainException(
            f"Marketplace offer {offer_id} is part of a multi-product offer set; " "bundle offers are not supported."
        )
    if len(offer.associatedProducts) > 1:
        raise domain_exception.DomainException(
            f"Marketplace offer {offer_id} references {len(offer.associatedProducts)} products; "
            "Only single-product AMI offers are supported."
        )
    for association in offer.associatedProducts:
        product = offer_discovery_svc.get_product(association.productId)
        if not product.is_ami_product():
            raise domain_exception.DomainException(
                f"Marketplace product {association.productId} (referenced by offer "
                f"{offer_id}) is not an AMI product "
                f"(fulfillment options: {product.fulfillmentOptionTypes}); "
                "Only AMI products are supported."
            )
    return offer.agreementProposalId


def _derive_client_token(
    project_id: str,
    offer_id: str,
    agreement_proposal_id: str,
    requested_terms: list[dict[str, Any]],
) -> str:
    """Derive the idempotency key used when the caller supplies none.

    ``clientToken`` is an AWS idempotency token (so marked in the
    ``marketplace-agreement`` service model): repeated calls carrying the
    same token, proposal identifier and requested terms return the same
    ``agreementRequestId`` instead of creating a second request.

    The frontend sends its own token, generated per wizard attempt and per
    pricing configuration, and that token always wins. This derived token
    is the fallback for callers that send none, so that a retry of the same
    request is still idempotent rather than creating a new agreement
    request on every call.

    The seed is the content that defines the purchase, which is AWS's own
    equality condition for the token. ``requestedTerms`` is serialised with
    ``sort_keys=True`` and the term list is sorted by ``id``, because AWS
    raises ``ConflictException`` when a token is reused with a payload that
    differs *including in list order*, and callers assemble that list by
    filtering the offer's terms in no guaranteed order. Sorting makes the
    derived token depend on the set of terms rather than their order, while
    a different term set still yields a different token.

    The same approach is used for License Manager grants in
    ``aws_license_manager_service.create_grant``.
    """
    canonical_terms = json.dumps(
        sorted(requested_terms, key=lambda term: str(term.get("id", ""))),
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    seed = f"{project_id}|{offer_id}|{agreement_proposal_id}|{canonical_terms}"
    return hashlib.sha256(seed.encode()).hexdigest()


def handle(
    command: create_agreement_request_command.CreateAgreementRequestCommand,
    offer_discovery_svc: MarketplaceOfferDiscoveryService,
    procurement_svc: MarketplaceProcurementService,
    agreement_svc: MarketplaceAgreementService,
    msg_bus: message_bus.MessageBus,
    logger: logging.Logger,
    metrics_client: metrics.Metrics | None = None,
) -> agreement_request.AgreementRequestQuote:
    """Execute :class:`CreateAgreementRequestCommand` and return the quote.

    Returns the whole :class:`AgreementRequestQuote`, not just the
    ``agreementRequestId``. The estimated-charge summary AWS returns
    alongside the id is the quote the buyer is being asked to approve; the
    API returns it so a paid CONTRACT total reaches the UI.
    """
    if not command.requestedTerms:
        raise domain_exception.DomainException(
            "At least one requested term is required to create an agreement request."
        )

    _guard_no_duplicate_active_agreement(command.offerId.value, agreement_svc)
    agreement_proposal_id = _guard_ami_only(command.offerId.value, offer_discovery_svc)

    client_token = command.clientToken or _derive_client_token(
        project_id=command.projectId.value,
        offer_id=command.offerId.value,
        agreement_proposal_id=agreement_proposal_id,
        requested_terms=command.requestedTerms,
    )
    try:
        quote = procurement_svc.create_agreement_request(
            client_token=client_token,
            agreement_proposal_identifier=agreement_proposal_id,
            requested_terms=command.requestedTerms,
        )
    except (MarketplaceRequestRejectedException, MarketplaceConflictException) as e:
        # AWS refused the request itself (for example an invalid term configuration, or a
        # reused clientToken with another payload). That is the caller's problem, so it is a
        # 400 with AWS's reason. Throttling, access denied and outages stay AdapterException
        # and reach the caller as a 500.
        raise domain_exception.DomainException(
            f"AWS Marketplace rejected the agreement request for offer {command.offerId.value}: {e}"
        ) from e

    charge = quote.chargeSummary
    # Best-effort: the agreement request exists in AWS at this point, so a
    # publication failure must not be reported to the user as a failure.
    # See ``event_publication`` for the at-most-once contract.
    event_publication.publish_best_effort(
        msg_bus,
        agreement_request_created.AgreementRequestCreated(
            projectId=command.projectId.value,
            agreementRequestId=quote.agreementRequestId,
            offerId=command.offerId.value,
            agreementProposalId=agreement_proposal_id,
            estimatedAgreementValue=charge.newAgreementValue if charge else None,
            estimatedAgreementValueAfterTax=charge.newAgreementValueAfterTax if charge else None,
            estimatedCurrencyCode=charge.currencyCode if charge else None,
            createdAt=datetime.now(timezone.utc).isoformat(),
        ),
        logger=logger,
        metrics_client=metrics_client,
        agreementRequestId=quote.agreementRequestId,
        offerId=command.offerId.value,
    )

    return quote
