class RepositoryException(Exception):
    pass


class ConditionalCheckFailedException(RepositoryException):
    """A write's condition did not hold (e.g. the entity changed since it was read)."""

    pass
