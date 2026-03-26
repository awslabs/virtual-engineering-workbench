import logging
from typing import Any, Callable, Optional, Type

from mypy_boto3_dynamodb import client

from app.shared.adapters.unit_of_work_v2 import dynamodb_repository, repository_exception, unit_of_work


class DynamoDBUnitOfWork(unit_of_work.UnitOfWork):
    """Repository provider and unit of work for DynamoDB."""

    _repo_factories: dict[Type, Callable[[dynamodb_repository.DynamoDBContext], Any]]
    _repo_instances: dict[Type, unit_of_work.GenericRepository[Any, Any]]

    def __init__(
        self,
        table_name: str,
        dynamodb_client: client.DynamoDBClient,
        repo_factories: dict[Type, Callable[[dynamodb_repository.DynamoDBContext], Any]],
        logger: logging.Logger,
    ):
        self._dynamodb_client = dynamodb_client
        self._table_name = table_name
        self._context: Optional[dynamodb_repository.DynamoDBContext] = None
        self._repo_factories = repo_factories
        self._repo_instances = {}
        self._logger = logger

    def get_repository(
        self, repo_key: Type, repo_type: Type
    ) -> unit_of_work.GenericRepository[unit_of_work.TPrimaryKey, unit_of_work.T]:
        """
        Returns a repository for a specified entity type.
        Primary key time is there only to ensure that static type checker works.
        """
        if repo_type in self._repo_instances:
            return self._repo_instances[repo_type]

        raise repository_exception.RepositoryException(
            f"Repository {repo_type} is not registered with the unit of work."
        )

    def commit(self) -> None:
        """Commits up to 25 changes to the DynamoDB table in a single transaction."""
        if self._context:
            self._context.commit()

    def __enter__(self) -> Any:
        self._context = dynamodb_repository.DynamoDBContext(dynamodb_client=self._dynamodb_client, logger=self._logger)

        for entity_type, repo_factory in self._repo_factories.items():
            repo = repo_factory(self._context)
            self._repo_instances[entity_type] = repo

        return self

    def __exit__(self, *args) -> None:
        self._context = None
        self._repo_instances = {}
