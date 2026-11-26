from typing import Literal

from pydantic import ConfigDict, Field

from app.shared.adapters.message_bus import message_bus


class AgreementCancelled(message_bus.Message):
    """Emitted when a ``CancelAgreementCommand`` completes
    successfully. Downstream consumers (e.g. the discovery cache
    invalidation) key off this event to drop the retired subscription.
    """

    event_name: Literal["AgreementCancelled"] = Field("AgreementCancelled", alias="eventName")
    agreementId: str = Field(..., title="agreementId")
    cancelledAt: str = Field(..., title="cancelledAt")
    model_config = ConfigDict(populate_by_name=True)
