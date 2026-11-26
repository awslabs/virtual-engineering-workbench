from app.packaging.domain.value_objects.marketplace import agreement_id_value_object
from app.shared.adapters.message_bus import command_bus


class CancelAgreementCommand(command_bus.Command):
    """Cancel an active Marketplace agreement (rollback / manage).

    Wraps the Agreements API ``CancelAgreement`` operation, which is not
    idempotent: AWS rejects cancelling an already-cancelled agreement with
    a conflict. The handler treats that conflict as success when the
    agreement's status is ``CANCELLED``, and fails otherwise.
    """

    agreementId: agreement_id_value_object.AgreementIdValueObject
