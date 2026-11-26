from abc import ABC, abstractmethod
from typing import Any

from app.packaging.domain.read_models.agreement_request import AcceptedAgreement, AgreementRequestQuote


class MarketplaceProcurementService(ABC):
    """Write-side port for the AWS Marketplace Agreements API surface used
    by Marketplace procurement.

    The two-step contract mirrors the AWS API:

    1. :meth:`create_agreement_request` submits a proposed purchase and
       returns a short-lived ``agreementRequestId`` plus an estimated-
       charge summary. Nothing is billed yet — this is the "quote" step.
       Idempotent per AWS when the caller reuses the same ``clientToken``.
    2. :meth:`accept_agreement_request` confirms the previously created
       request and returns the durable ``agreementId`` under which the
       buyer's subscription now lives.

    :meth:`cancel_agreement` initiates cancellation of an active agreement
    (used by the manage-subscription UI and by rollback tests).
    """

    @abstractmethod
    def create_agreement_request(
        self,
        client_token: str,
        agreement_proposal_identifier: str,
        requested_terms: list[dict[str, Any]],
    ) -> AgreementRequestQuote:
        """Submit a ``NEW``-intent ``CreateAgreementRequest`` for an AMI
        offer.

        ``requested_terms`` is a list of term configuration dicts of the
        form ``{"id": "term-...", "configuration": {...}}`` (configuration
        is optional for simple pricing terms like
        ``UsageBasedPricingTerm``, and required for configurable ones like
        ``ConfigurableUpfrontPricingTerm``). The caller assembles this
        list from :meth:`MarketplaceOfferDiscoveryService.get_offer_terms`
        output.

        AWS treats ``clientToken`` as an idempotency key: repeated calls
        with the same token, proposal identifier, and requested terms
        return the same ``agreementRequestId``. Changing the payload
        (including term list order) while reusing a token causes AWS to
        raise ``ConflictException`` (raised here as
        :class:`MarketplaceConflictException`).

        The command handler passes the caller's token when one is supplied
        and otherwise derives one from the request content (project, offer,
        proposal, canonicalised terms), so a retry of the same request is
        idempotent either way.
        """
        ...

    @abstractmethod
    def accept_agreement_request(self, agreement_request_id: str) -> AcceptedAgreement:
        """Confirm a previously created agreement request.

        NOT idempotent per AWS: calling twice with the same
        ``agreementRequestId`` fails on the second call. AWS conflicts are
        raised as :class:`MarketplaceConflictException` carrying AWS's
        ``resourceType`` / ``resourceId``; other failures as
        ``AdapterException``.
        """
        ...

    @abstractmethod
    def cancel_agreement(self, agreement_id: str) -> None:
        """Cancel an active agreement.

        NOT idempotent per AWS: calling on an already-cancelled agreement
        fails. AWS conflicts are raised as
        :class:`MarketplaceConflictException`; the caller checks the
        agreement's status to tell "already cancelled" apart from "not
        eligible for cancellation". Other failures raise
        ``AdapterException``.
        """
        ...
