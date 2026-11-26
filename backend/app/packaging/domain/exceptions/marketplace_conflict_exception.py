from typing import Optional


class MarketplaceConflictException(Exception):
    """AWS Marketplace refused a write because of the current state of a
    resource (AWS ``ConflictException``).

    Domain-owned so command handlers can tell a state conflict apart from
    every other failure without importing adapter code. A conflict can be
    the outcome of a replay (cancelling an agreement AWS already
    cancelled), so a handler may check the current AWS state before
    deciding whether it is a failure.

    ``resource_type`` and ``resource_id`` are AWS's own identification of
    the conflicting resource (``ConflictException.resourceType`` /
    ``resourceId``), ``None`` when AWS omits them.
    """

    def __init__(self, message: str, resource_type: Optional[str] = None, resource_id: Optional[str] = None):
        super().__init__(message)
        self.resource_type = resource_type
        self.resource_id = resource_id
