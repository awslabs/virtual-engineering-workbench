class AccountErrorMessageValueObject:
    def __init__(self, error: str, cause: str) -> None:
        self.__error = error
        self.__cause = cause

    @property
    def error(self) -> str:
        return self.__error

    @property
    def cause(self) -> str:
        return self.__cause


def from_str(error: str | None = None, cause: str | None = None) -> AccountErrorMessageValueObject:
    return AccountErrorMessageValueObject(
        error=error if error else "Unknown error",
        cause=cause if cause else "Unknown cause",
    )
