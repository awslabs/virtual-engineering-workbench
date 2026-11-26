from typing import Any, Optional

from pydantic import Field

from app.packaging.domain.value_objects.marketplace import offer_id_value_object
from app.packaging.domain.value_objects.shared import project_id_value_object
from app.shared.adapters.message_bus import command_bus


class CreateAgreementRequestCommand(command_bus.Command):
    """Submit a proposed Marketplace purchase (step 1: the "quote").

    Wraps the Agreements API ``CreateAgreementRequest`` operation. The
    handler enforces two invariants before touching AWS: (1) the offer is
    single-product, and (2) every product associated with the offer is an
    AMI-type Marketplace product (fulfillment option
    ``AMAZON_MACHINE_IMAGE``). Non-AMI or bundle offers raise
    :class:`DomainException`.
    """

    projectId: project_id_value_object.ProjectIdValueObject
    offerId: offer_id_value_object.OfferIdValueObject
    # requestedTerms mirrors the AWS payload shape; per-entry
    # ``configuration`` is optional and forwarded verbatim.
    requestedTerms: list[dict[str, Any]] = Field(default_factory=list)
    # Client-supplied idempotency token (1-64 of [a-zA-Z0-9-], validated at
    # the API). Optional: without one the handler derives a token from the
    # project, offer, proposal and requested terms.
    clientToken: Optional[str] = Field(default=None)
