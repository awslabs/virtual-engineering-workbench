import enum
import logging
import typing
from datetime import datetime, timezone

import pydantic
from mypy_boto3_dynamodb import service_resource

from app.shared.adapters.unit_of_work_v2 import (
    dynamodb_repo_config,
    dynamodb_repository,
    dynamodb_unit_of_work,
    unit_of_work,
)

MigrationScript: typing.TypeAlias = typing.Callable[[service_resource.Table], None]

MIGRATION_ENTITY_NAME = "MIGRATION"


class MigrationsScriptState(enum.StrEnum):
    Running = "RUNNING"
    Completed = "COMPLETED"
    Failed = "FAILED"


class DynamoDBMigrationPrimaryKey(unit_of_work.PrimaryKey):
    pass


class DynamoDBMigrationScript(pydantic.BaseModel):
    name: str = pydantic.Field(..., title="name")
    sequence: int = pydantic.Field(..., title="sequence")
    state: MigrationsScriptState = pydantic.Field(..., title="state")
    createDate: str = pydantic.Field(..., title="createDate")


class DynamoDBMigration(unit_of_work.Entity):
    migrationScripts: list[DynamoDBMigrationScript] = pydantic.Field(..., title="migrationScripts")


class MigrationsEntityConfigurator(dynamodb_repository.DynamoDBEntityConfiguratorBase):

    def __init__(self, table_name: str) -> None:
        """DynamoDB Entity configuration for DDB Migrations BC.

        DynamoDB table must have the following partition and sort keys
        | Name                                   | Partition Key attr. | Sort Key attr. |
        |  -                                     | PK                  | SK             |
        """

        super().__init__(table_name)
        self.register_cfg(
            DynamoDBMigrationPrimaryKey,
            DynamoDBMigration,
            self.dynamo_db_migration_config,
        )

    def dynamo_db_migration_config(
        self,
        cfg: dynamodb_repo_config.GenericDynamoDBRepositoryConfig[DynamoDBMigrationPrimaryKey, DynamoDBMigration],
    ):
        cfg.partition_key(
            name="PK",
            value_template=lambda: MIGRATION_ENTITY_NAME,
            values_from_entity=lambda _: [],
            values_from_primary_key=lambda _: [],
        )

        cfg.sort_key(
            name="SK",
            value_template=lambda: MIGRATION_ENTITY_NAME,
            values_from_entity=lambda _: [],
            values_from_primary_key=lambda _: [],
        )

        cfg.enable_optimistic_concurrency_control()


class DynamoDBMigrator:

    def __init__(self, ddb_resource: service_resource.DynamoDBServiceResource, table_name: str, logger: logging.Logger):
        self.__migrations = []
        self.__ddb_resource = ddb_resource
        self.__table_name = table_name
        self.__logger = logger

        self.__ddb_table = self.__ddb_resource.Table(self.__table_name)

        self.__uow = dynamodb_unit_of_work.DynamoDBUnitOfWork(
            table_name=self.__table_name,
            dynamodb_client=self.__ddb_resource.meta.client,
            repo_factories=MigrationsEntityConfigurator(table_name=self.__table_name).repo_factories(),
            logger=self.__logger,
        )

    def migrate(self):
        if not self.__migrations:
            self.__logger.debug("No DB migrations registered.")
            return

        self.__logger.info("Running DB migrations")
        self.__logger.debug(f"Table name: {self.__table_name}")

        migrations_meta = self.__get_executed_migration_scripts()

        self.__validate_migrations_state(migrations_meta=migrations_meta)

        migrations_meta = (
            self.__merge_code_migrations_with_meta(migrations_meta)
            if migrations_meta
            else self.__create_meta_from_code_migrations()
        )

        if not next((ms for ms in migrations_meta.migrationScripts if ms.state == MigrationsScriptState.Running), None):
            self.__logger.debug("No new DB migrations.")
            return

        failed = False
        for migration_script in migrations_meta.migrationScripts:

            if failed:
                migration_script.state = MigrationsScriptState.Failed
                continue

            if migration_script.state != MigrationsScriptState.Running:
                continue

            _, script = self.__migrations[migration_script.sequence]
            self.__logger.info(f"Running migration {migration_script.name}...")
            try:
                script(self.__ddb_table)
                migration_script.state = MigrationsScriptState.Completed
            except Exception:
                self.__logger.exception(f"Unable to apply {migration_script.name} migration")
                migration_script.state = MigrationsScriptState.Failed
                failed = True

        with self.__uow as uow:
            uow.get_repository(DynamoDBMigrationPrimaryKey, DynamoDBMigration).update_entity(
                DynamoDBMigrationPrimaryKey(), migrations_meta
            )
            uow.commit()

    def register_migration(self, name: str, script: MigrationScript) -> typing.Self:
        self.__logger.debug(f"Registering DB migration {name} for {self.__table_name}")
        self.__migrations.append((name, script))
        return self

    def register_migrations(self, migrations: list[tuple[str, MigrationScript]]) -> typing.Self:
        for name, script in migrations:
            self.register_migration(name, script)
        return self

    def __validate_migrations_state(self, migrations_meta: DynamoDBMigration):
        if migrations_meta and next(
            (ms for ms in migrations_meta.migrationScripts if ms.state == MigrationsScriptState.Running), None
        ):
            raise Exception("There is already a migration in progress.")

        if migrations_meta and len(migrations_meta.migrationScripts) > len(self.__migrations):
            raise Exception("There are more migrations in the DB than in the code. Migration code cannot be removed.")

    def __get_executed_migration_scripts(self) -> DynamoDBMigration | None:
        migration_info = self.__ddb_table.get_item(Key={"PK": MIGRATION_ENTITY_NAME, "SK": MIGRATION_ENTITY_NAME})

        migration_entity = DynamoDBMigration.parse_obj(migration_info["Item"]) if "Item" in migration_info else None

        self.__logger.debug(f"Migrations state: {migration_entity.dict() if migration_entity else None}")

        return migration_entity

    def __merge_code_migrations_with_meta(self, migrations_meta: DynamoDBMigration) -> DynamoDBMigration:
        new_migrations = False
        create_date = datetime.now(timezone.utc).isoformat()
        for idx, (name, _) in enumerate(self.__migrations):
            if idx < len(migrations_meta.migrationScripts):
                if migrations_meta.migrationScripts[idx].name != name:
                    raise Exception(
                        f"Migration {name} is not in the correct order. Expected {migrations_meta.migrationScripts[idx].name}"
                    )

                if migrations_meta.migrationScripts[idx].state == MigrationsScriptState.Failed:
                    migrations_meta.migrationScripts[idx].state = MigrationsScriptState.Running
                    new_migrations = True

            else:
                migrations_meta.migrationScripts.append(
                    DynamoDBMigrationScript(
                        name=name, sequence=idx, state=MigrationsScriptState.Running, createDate=create_date
                    )
                )
                new_migrations = True

        if new_migrations:
            with self.__uow as uow:
                uow.get_repository(DynamoDBMigrationPrimaryKey, DynamoDBMigration).update_entity(
                    DynamoDBMigrationPrimaryKey(), migrations_meta
                )
                uow.commit()
                migrations_meta._sequence_no += 1

        self.__logger.debug(f"Updated migrations state: {migrations_meta.dict() if migrations_meta else None}")

        return migrations_meta

    def __create_meta_from_code_migrations(self) -> DynamoDBMigration:
        migration_scripts = []
        create_date = datetime.now(timezone.utc).isoformat()
        for idx, (name, _) in enumerate(self.__migrations):
            migration_scripts.append(
                DynamoDBMigrationScript(
                    name=name, sequence=idx, state=MigrationsScriptState.Running, createDate=create_date
                )
            )

        migrations_meta = DynamoDBMigration(migrationScripts=migration_scripts)

        with self.__uow as uow:
            uow.get_repository(DynamoDBMigrationPrimaryKey, DynamoDBMigration).add(migrations_meta)
            uow.commit()

        self.__logger.debug(f"Updated migrations state: {migrations_meta.dict() if migrations_meta else None}")

        return migrations_meta
