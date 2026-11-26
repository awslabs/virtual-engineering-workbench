from app.packaging.domain.value_objects.marketplace import agreement_request_id_value_object
from app.shared.adapters.message_bus import command_bus


class AcceptAgreementRequestCommand(command_bus.Command):
    """Confirm a previously created agreement request (step 2:
    "purchase").

    Wraps the Agreements API ``AcceptAgreementRequest`` operation, which is
    not idempotent: AWS rejects a second acceptance with a conflict. The
    handler returns the existing ``agreementId`` when AWS identifies an
    active agreement for that conflict, and fails otherwise.
    """

    agreementRequestId: agreement_request_id_value_object.AgreementRequestIdValueObject
