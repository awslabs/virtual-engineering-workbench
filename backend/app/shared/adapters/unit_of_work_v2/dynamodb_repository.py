import decimal
import logging
import typing
from abc import ABC

from botocore.exceptions import ClientError
from mypy_boto3_dynamodb import client

from app.shared.adapters.unit_of_work_v2 import (
    dynamodb_repo_config,
    repository_exception,
    unit_of_work,
)


class DynamoDBContext:
    """Transactional context manager for DynamoDB."""

    def __init__(self, dynamodb_client: client.DynamoDBClient, logger: logging.Logger):
        self._db_items = []
        self._dynamodb_client = dynamodb_client
        self._logger = logger

    def commit(self) -> None:
        """Commits up to 100 changes to the DynamoDB table in a single transaction."""
        try:
            items = list(self._db_items)
            for i in range(0, len(items), 100):
                self._dynamodb_client.transact_write_items(TransactItems=items[i : i + 100])
            self._db_items = []
        except ClientError as e:
            if e.response["Error"]["Code"] == "TransactionCanceledException":
                cancellation_reasons = e.response.get("CancellationReasons", [])
                self._logger.error("Transaction failed due to cancellation reasons:")
                for idx, reason in enumerate(cancellation_reasons):
                    self._logger.error(f"Item {idx + 1}: {reason.get('Code')} - {reason.get('Message')}")
            else:
                self._logger.exception("An error occurred during the transaction.")
            raise repository_exception.RepositoryException("Failed to commit a transaction to DynamoDB.") from e
        except Exception as e:
            self._logger.exception("Failed to commit a transaction to DynamoDB.")
            raise repository_exception.RepositoryException("Failed to commit a transaction to DynamoDB.") from e

    def add_to_transaction(self, item) -> None:
        """Adds DynamoDB modifying instructions to a pending list."""
        self._db_items.append(item)

    def get_generic_item(self, request: dict) -> typing.Any:
        """
        Gets a generic item from DynamoDB by primary key.
        """
        item = self._dynamodb_client.get_item(**request)

        return item["Item"] if "Item" in item else None


class DynamoDBRepository:
    """Generic DynamoDB repository."""

    def __init__(
        self,
        cfg: dynamodb_repo_config.GenericDynamoDBRepositoryConfig[unit_of_work.TPrimaryKey, unit_of_work.T],
        context: DynamoDBContext,
    ):
        self._cfg = cfg
        self._context = context

    def add_generic_item(self, item: dict) -> None:
        """Converts item to a DynamoDB put item instruction and adds to the pending transactions list."""
        put_request = {
            "Put": {
                "TableName": self._cfg.table_name,
                "Item": item,
            }
        }
        if not self._cfg.upsert_allowed:
            conditions = " AND ".join([f"attribute_not_exists({attr})" for attr in self._cfg.primary_key_attributes])
            put_request["Put"]["ConditionExpression"] = f"({conditions})"

        self._context.add_to_transaction(item=put_request)

    def update_generic_item(self, expression: dict, key: dict) -> None:
        """Converts item to a DynamoDB update instruction and adds to the pending transactions list."""
        update_request = {"Update": {"TableName": self._cfg.table_name, "Key": key, **expression}}
        self._context.add_to_transaction(item=update_request)

    def delete_generic_item(self, key: dict) -> None:
        """Converts item to a DynamoDB delete instruction and adds to the pending transactions list."""
        delete_request = {"Delete": {"TableName": self._cfg.table_name, "Key": key}}
        self._context.add_to_transaction(item=delete_request)

    def create_get_request(self, key: dict) -> dict:
        return {"TableName": self._cfg.table_name, "Key": {**key}}

    @property
    def cfg(self):
        return self._cfg

    @property
    def context(self):
        return self._context


class GenericDynamoDBRepository(unit_of_work.GenericRepository[unit_of_work.TPrimaryKey, unit_of_work.T]):
    """Generic DynamoDB repository."""

    def __init__(
        self,
        dynamodb_repository: DynamoDBRepository,
    ):
        self._dynamodb_repository = dynamodb_repository

    def add(self, entity: unit_of_work.T) -> None:
        """Adds an entity to the DynamoDB table."""

        item = {}
        for modifier in self._dynamodb_repository.cfg.modifiers:
            item = {**item, **modifier(entity)}

        self._dynamodb_repository.add_generic_item(item)

        if self._dynamodb_repository.cfg.optimistic_concurrency_control:
            entity._sequence_no = 0

    def get(self, pk: unit_of_work.TPrimaryKey) -> typing.Optional[unit_of_work.T]:
        """Gets an entity from the DynamoDB table."""

        key = self._dynamodb_repository.cfg.primary_key_to_dict(pk)
        request = self._dynamodb_repository.create_get_request(key)
        item_dict = self._dynamodb_repository.context.get_generic_item(request)
        return self._dynamodb_repository.cfg.entity_type.model_validate(item_dict) if item_dict is not None else None

    def remove(self, pk: unit_of_work.TPrimaryKey) -> None:
        """Removes an entity from the DynamoDB table."""
        key = self._dynamodb_repository.cfg.primary_key_to_dict(pk)
        return self._dynamodb_repository.delete_generic_item(key=key)

    def update_attributes(self, pk: unit_of_work.TPrimaryKey, **kwargs) -> None:
        """Updates arbitrary attributes of the entity in DynamoDB table."""

        if not kwargs:
            return

        update_expression_setters = []
        update_values = {}
        conditions = [
            "attribute_exists(PK)",
            "attribute_exists(SK)",
        ]

        if self._dynamodb_repository.cfg.optimistic_concurrency_control:
            seq_no = kwargs.pop(unit_of_work.ATTRIBUTE_NAME_SEQUENCE_NO, None)
            if seq_no is None or not isinstance(seq_no, (int, decimal.Decimal)):
                raise repository_exception.RepositoryException(
                    f"Entity has optimistic concurrency control enabled but no {unit_of_work.ATTRIBUTE_NAME_SEQUENCE_NO} attribute"
                )
            update_expression_setters.append(
                f"{unit_of_work.ATTRIBUTE_NAME_SEQUENCE_NO} = if_not_exists({unit_of_work.ATTRIBUTE_NAME_SEQUENCE_NO}, :defaultval) + :incrval"
            )
            update_values |= {":defaultval": 0, ":incrval": 1, ":sequenceNo": seq_no}
            conditions.append(f"{unit_of_work.ATTRIBUTE_NAME_SEQUENCE_NO} = :sequenceNo")

        entity_attributes = kwargs
        entity_arguments = {**kwargs, **pk.model_dump()}

        for modifier in self._dynamodb_repository.cfg.update_modifiers:
            entity_attributes = {**entity_attributes, **modifier(entity_arguments)}

        update_attribute_names = {f"#{key}": key for (key, _) in entity_attributes.items()}
        update_expression_removers = []
        if self._dynamodb_repository.cfg.none_values_excluded:
            update_expression_removers = [f"#{key}" for key, value in entity_attributes.items() if value is None]
            entity_attributes = {k: v for k, v in entity_attributes.items() if v is not None}

        update_expression_setters.extend([f"#{key}=:p{idx}" for idx, (key, _) in enumerate(entity_attributes.items())])
        update_values |= {f":p{idx}": value for idx, (_, value) in enumerate(entity_attributes.items())}

        conditions_str = " AND ".join(conditions)

        update_expression = [
            (f"SET {', '.join(update_expression_setters)}" if update_expression_setters else None),
            (f"REMOVE {', '.join(update_expression_removers)}" if update_expression_removers else None),
        ]

        expr = {
            "UpdateExpression": " ".join([e for e in update_expression if e]),
            "ExpressionAttributeValues": update_values,
            "ConditionExpression": f"({conditions_str})",
        }
        if update_attribute_names:
            expr["ExpressionAttributeNames"] = update_attribute_names

        self._dynamodb_repository.update_generic_item(
            expression=expr,
            key=self._dynamodb_repository.cfg.primary_key_to_dict(pk),
        )

    def update_entity(self, pk: unit_of_work.TPrimaryKey, entity: unit_of_work.T) -> None:
        """
        Updates arbitrary entity attributes in the database in a type safe manner.
        """

        updated_attrs = {}
        new_dict = entity.model_dump()
        for key, value in new_dict.items():
            if value != entity._original_value.get(key):
                updated_attrs[key] = value

                # DFS across all dynamic attribute dependencies.
                deps_stack = [
                    d for d in self._dynamodb_repository.cfg.get_attribute_dependencies(key) if d not in updated_attrs
                ]
                while deps_stack:
                    dep = deps_stack.pop()
                    if dep not in updated_attrs:
                        updated_attrs[dep] = new_dict[dep]
                    deps_stack.extend(
                        [
                            d
                            for d in self._dynamodb_repository.cfg.get_attribute_dependencies(dep)
                            if d not in updated_attrs and d not in deps_stack
                        ]
                    )

        if self._dynamodb_repository.cfg.optimistic_concurrency_control:
            updated_attrs[unit_of_work.ATTRIBUTE_NAME_SEQUENCE_NO] = entity._sequence_no

        self.update_attributes(pk, **updated_attrs)
        entity.refresh_changes()

    @staticmethod
    def create_factory(
        pk_type: typing.Type[unit_of_work.TPrimaryKey],
        repo_type: typing.Type[unit_of_work.T],
        cfg: dynamodb_repo_config.GenericDynamoDBRepositoryConfig[unit_of_work.TPrimaryKey, unit_of_work.T],
    ) -> lambda ctx: GenericDynamoDBRepository[unit_of_work.TPrimaryKey, unit_of_work.T]:
        """Returns a factory method for the GenericDynamoDBRepository to be used by the unit of work."""

        return lambda ctx: GenericDynamoDBRepository[pk_type, repo_type](
            dynamodb_repository=DynamoDBRepository(cfg, ctx)
        )


class DynamoDBEntityConfiguratorBase(ABC):
    """Helper class to move DynamoDB related entity configuration to the adapters."""

    def __init__(self, table_name: str) -> None:
        self._configs = {}
        self._entity_keys = {}
        self._table_name = table_name

    def register_cfg(
        self,
        tpk: typing.Type[unit_of_work.TPrimaryKey],
        t: typing.Type[unit_of_work.T],
        configurator: typing.Callable[
            [dynamodb_repo_config.GenericDynamoDBRepositoryConfig[unit_of_work.TPrimaryKey, unit_of_work.T]],
            None,
        ],
    ):
        cfg = dynamodb_repo_config.GenericDynamoDBRepositoryConfig[tpk, t](tpk, t)
        cfg.set_table_name(self._table_name)
        configurator(cfg)
        self._configs[t] = cfg
        self._entity_keys[t] = tpk

    def repo_factories(self):
        return {
            type: GenericDynamoDBRepository.create_factory(self._entity_keys.get(type), type, cfg)
            for type, cfg in self._configs.items()
        }

    def get_config_for(
        self,
        tpk: typing.Type[unit_of_work.TPrimaryKey],
        t: typing.Type[unit_of_work.T],
    ) -> dynamodb_repo_config.GenericDynamoDBRepositoryConfig[unit_of_work.TPrimaryKey, unit_of_work.T]:
        return self._configs[t]
