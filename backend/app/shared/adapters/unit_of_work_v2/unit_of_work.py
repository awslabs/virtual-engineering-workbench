from abc import ABC, abstractmethod
from typing import Any, Generic, Optional, Type, TypeVar

import pydantic

ATTRIBUTE_NAME_SEQUENCE_NO = "sequenceNo"


class PrimaryKey(pydantic.BaseModel):
    """
    Base class for entity primary keys.
    """

    ...


class Entity(pydantic.BaseModel):
    """
    Base class for entities.
    """

    _original_value: dict = pydantic.PrivateAttr()
    _sequence_no: int | None = pydantic.PrivateAttr()

    def __init__(self, **data):
        super().__init__(**data)
        # this could also be done with default_factory
        self._original_value = self.model_dump()
        self._sequence_no = data.get(ATTRIBUTE_NAME_SEQUENCE_NO, None)

    def __eq__(self, other: object) -> bool:
        """Compare entities by public fields only, excluding private attributes.
        Pydantic v2 includes PrivateAttr in __eq__ by default, which breaks
        equality for mutated entities (e.g. _original_value differs)."""
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.model_dump() == other.model_dump()

    def __hash__(self) -> int:
        return id(self)

    @property
    def has_changes(self) -> bool:
        """
        Returns True if the entity has been modified.
        """
        return self._original_value != self.model_dump()

    def refresh_changes(self) -> None:
        """
        Refreshes the entity changes.
        """
        self._original_value = self.model_dump()


T = TypeVar("T", bound=Entity)
TPrimaryKey = TypeVar("TPrimaryKey", bound=PrimaryKey)


class GenericRepository(ABC, Generic[TPrimaryKey, T]):
    @abstractmethod
    def add(self, item: T) -> None:
        """
        Adds an entity to a database.
        """
        ...

    @abstractmethod
    def get(self, pk: TPrimaryKey) -> Optional[T]:
        """
        Gets a single entity from the database.
        """
        ...

    @abstractmethod
    def remove(self, pk: TPrimaryKey) -> None:
        """
        Removes an entity from the database.
        """
        ...

    @abstractmethod
    def update_attributes(self, pk: TPrimaryKey, **kwargs) -> None:
        """
        Updated arbitrary entity attributes in the database.
        """
        ...

    @abstractmethod
    def update_entity(self, pk: TPrimaryKey, entity: T) -> None:
        """
        Updates arbitrary entity attributes in the database in a type safe manner.
        """
        ...


class UnitOfWork(ABC):
    """
    Generic unit of work interface.
    Provides entity repositories and enables modifications on
    multiple entities in a single transaction.
    """

    @abstractmethod
    def get_repository(self, repo_key: Type[TPrimaryKey], repo_type: Type[T]) -> GenericRepository[TPrimaryKey, T]:
        """
        Returns an entity repository for a provided primary key and entity types.
        """
        ...

    @abstractmethod
    def commit(self) -> None:
        """
        Commits a transaction to the database.
        """
        ...

    @abstractmethod
    def __enter__(self) -> Any: ...

    @abstractmethod
    def __exit__(self, *args) -> None: ...
