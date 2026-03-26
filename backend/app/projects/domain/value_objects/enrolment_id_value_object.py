from app.projects.domain.exceptions import domain_exception


class EnrolmentIdValueObject:
    def __init__(self, value: str) -> None:
        if not value:
            raise domain_exception.DomainException("Enrolment id cannot be empty")
        self._value = value
        return

    @property
    def value(self) -> str:
        return self._value


def from_str(value: str) -> EnrolmentIdValueObject:
    if not value:
        raise domain_exception.DomainException("Enrolment id cannot be empty")
    return EnrolmentIdValueObject(value=value)
