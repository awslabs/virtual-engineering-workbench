from app.packaging.domain.exceptions.domain_exception import DomainException


class MarketplaceRequestRejectedException(DomainException):
    """AWS Marketplace refused a write as invalid or not supported
    (AWS ``ValidationException``).

    It is a domain exception, so the API answers with HTTP 400 and the
    message reaches the buyer, instead of a 500 that hides the reason. AWS
    uses ``ValidationException`` with the text "This action is not
    supported." for requests it cannot honour, such as cancelling an
    agreement in the first minutes after it was accepted.
    """
