from abc import ABC, abstractmethod

from app.packaging.domain.read_models.marketplace_agreement import MarketplaceAgreement


class MarketplaceAgreementService(ABC):
    @abstractmethod
    def list_active_agreements(self) -> list[MarketplaceAgreement]: ...

    @abstractmethod
    def is_ami_agreement(self, agreement_id: str) -> bool:
        """Whether every resource on ``agreement_id`` is an AMI product.

        The buyer-side ``aws.agreement-marketplace`` event carries no
        product type -- ``detail.product`` is ``{id, title}`` only -- so
        the type cannot be established from the event payload or by an
        EventBridge pattern. ``DescribeAgreement`` is the authoritative
        source: ``proposalSummary.resources[].type``.

        Returns ``False`` for a mixed bundle containing any non-AMI
        resource, and for an agreement with no resources at all, so that
        callers default to excluding what they cannot positively identify
        as AMI-only.

        Raises ``AdapterException`` when the agreement cannot be
        described; the type is then unknown, which is not the same as
        "not an AMI", and the caller decides what to do about it.
        """
        ...

    @abstractmethod
    def get_agreement_status(self, agreement_id: str) -> str:
        """Current AWS status of ``agreement_id`` (``ACTIVE``, ``CANCELLED``,
        ``EXPIRED``, ...), read with ``DescribeAgreement``.

        Used to decide whether a ``ConflictException`` on accept or cancel
        means the write had already happened.

        Raises ``AdapterException`` when the agreement cannot be described.
        """
        ...
