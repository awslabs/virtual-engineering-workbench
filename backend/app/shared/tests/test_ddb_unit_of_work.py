import decimal
import logging
from unittest import mock

import assertpy
import pydantic
import pytest
from pydantic import ConfigDict

from app.shared.adapters.unit_of_work_v2 import (
    dynamodb_repo_config,
    dynamodb_repository,
    dynamodb_unit_of_work,
    repository_exception,
    unit_of_work,
)


class CarId(unit_of_work.PrimaryKey):
    id: str = pydantic.Field(...)


class Car(unit_of_work.Entity):
    id: str = pydantic.Field(...)
    name: str = pydantic.Field(...)
    nullable_attribute: str | None = pydantic.Field(None)


class GarageId(unit_of_work.PrimaryKey):
    id_1: str = pydantic.Field(...)
    id_2: str = pydantic.Field(...)


class GarageDoor(pydantic.BaseModel):
    side: str = pydantic.Field(...)


class EngineId(unit_of_work.PrimaryKey):
    id: str = pydantic.Field(...)


class Garage(unit_of_work.Entity):
    id_1: str = pydantic.Field(...)
    id_2: str = pydantic.Field(...)
    name: str = pydantic.Field(...)
    status: str = pydantic.Field(...)
    doors: list[GarageDoor] | None = pydantic.Field(None)


class Engine(unit_of_work.Entity):
    id: str = pydantic.Field(...)
    name: str = pydantic.Field(...)


class ServiceId(unit_of_work.PrimaryKey):
    id_1: str = pydantic.Field(...)
    id_2: str = pydantic.Field(...)


class Service(unit_of_work.Entity):
    id_1: str = pydantic.Field(...)
    id_2: str = pydantic.Field(...)
    service_label: str = pydantic.Field(..., alias="serviceLabel")
    service_type: str = pydantic.Field(..., alias="serviceType")
    state: str = pydantic.Field(...)
    model_config = ConfigDict(populate_by_name=True)


class EntityConfigurator(dynamodb_repository.DynamoDBEntityConfiguratorBase):
    def __init__(self, table_name: str) -> None:
        super().__init__(table_name)
        self.register_cfg(CarId, Car, self.car_entity_config)
        self.register_cfg(GarageId, Garage, self.garage_entity_config)
        self.register_cfg(EngineId, Engine, self.engine_entity_config)
        self.register_cfg(ServiceId, Service, self.service_entity_config)

    def car_entity_config(self, cfg: dynamodb_repo_config.GenericDynamoDBRepositoryConfig[CarId, Car]):
        entity_name = "ENTITY1"

        cfg.partition_key(
            name="PK",
            value_template=lambda id: f"{entity_name}#{id}",
            values_from_entity=lambda ent: ent.id,
            values_from_primary_key=lambda pk: pk.id,
        )

        cfg.sort_key(
            name="SK",
            value_template=lambda id: f"{entity_name}#{id}",
            values_from_entity=lambda ent: ent.id,
            values_from_primary_key=lambda pk: pk.id,
        )

        cfg.enable_query_all(entity_name)

    def garage_entity_config(self, cfg: dynamodb_repo_config.GenericDynamoDBRepositoryConfig[GarageId, Garage]):
        entity_name = "ENTITY2"

        cfg.partition_key(
            name="PK",
            value_template=lambda id: f"{entity_name}#{id}",
            values_from_entity=lambda ent: ent.id_1,
            values_from_primary_key=lambda pk: pk.id_1,
        )

        cfg.sort_key(
            name="SK",
            value_template=lambda id: f"ID2#{id}",
            values_from_entity=lambda ent: ent.id_2,
            values_from_primary_key=lambda pk: pk.id_2,
        )

        cfg.allow_upsert()

        cfg.enable_query_pattern(
            gsi_pk_name="QSK_PK",
            gsi_pk_value_template=lambda id: f"ID2#{id}",
            gsi_pk_values_from_entity=lambda ent: ent.id_2,
            gsi_sk_name="QSK_SK",
            gsi_sk_value_template=lambda id, status: f"{entity_name}#{status}#{id}",
            gsi_sk_values_from_entity=lambda ent: [ent.id_1, ent.status],
        )

        cfg.exclude_none()

    def engine_entity_config(self, cfg: dynamodb_repo_config.GenericDynamoDBRepositoryConfig[EngineId, Engine]):
        cfg.partition_key(
            name="PK",
            value_template=lambda id: f"ENGINE#{id}",
            values_from_entity=lambda ent: ent.id,
            values_from_primary_key=lambda pk: pk.id,
        )
        cfg.sort_key(
            name="SK",
            value_template=lambda id: f"ENGINE#{id}",
            values_from_entity=lambda ent: ent.id,
            values_from_primary_key=lambda pk: pk.id,
        )

        cfg.enable_optimistic_concurrency_control()

    def service_entity_config(self, cfg: dynamodb_repo_config.GenericDynamoDBRepositoryConfig[ServiceId, Service]):
        entity_name = "SERVICE"

        cfg.partition_key(
            name="PK",
            value_template=lambda id: f"{entity_name}#{id}",
            values_from_entity=lambda ent: ent.id_1,
            values_from_primary_key=lambda pk: pk.id_1,
        )

        cfg.sort_key(
            name="SK",
            value_template=lambda id: f"{entity_name}#{id}",
            values_from_entity=lambda ent: ent.id_2,
            values_from_primary_key=lambda pk: pk.id_2,
        )

        cfg.enable_query_pattern(
            gsi_pk_name="QSK_PK",
            gsi_pk_value_template=lambda service_label, service_type: f"{service_label}#{service_type}",
            gsi_pk_values_from_entity=lambda ent: [ent.service_label, ent.service_type],
        )

        cfg.enable_query_pattern(
            gsi_pk_name="QSK_SK",
            gsi_pk_value_template=lambda service_type, state: f"{service_type}#{state}",
            gsi_pk_values_from_entity=lambda ent: [ent.service_type, ent.state],
        )


class UpsertWithOptimisticConcurrencyControlConfigurator(dynamodb_repository.DynamoDBEntityConfiguratorBase):
    def __init__(self, table_name: str) -> None:
        super().__init__(table_name)
        self.register_cfg(EngineId, Engine, self.engine_entity_config)

    def engine_entity_config(self, cfg: dynamodb_repo_config.GenericDynamoDBRepositoryConfig[EngineId, Engine]):
        cfg.partition_key(
            name="PK",
            value_template=lambda id: f"ENGINE#{id}",
            values_from_entity=lambda ent: ent.id,
            values_from_primary_key=lambda pk: pk.id,
        )
        cfg.sort_key(
            name="SK",
            value_template=lambda id: f"ENGINE#{id}",
            values_from_entity=lambda ent: ent.id,
            values_from_primary_key=lambda pk: pk.id,
        )

        cfg.enable_optimistic_concurrency_control()
        cfg.allow_upsert()


def test_repository_add_when_has_modifiers_should_apply_before_add(
    mock_dynamodb, backend_app_dynamodb_table, test_table_name
):
    # ARRANGE
    uow = dynamodb_unit_of_work.DynamoDBUnitOfWork(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        repo_factories=EntityConfigurator(table_name=test_table_name).repo_factories(),
        logger=mock.create_autospec(spec=logging.Logger),
    )
    # ACT
    with uow:
        uow.get_repository(CarId, Car).add(Car(id="123", name="Name"))

        uow.commit()

    # ASSERT
    item = backend_app_dynamodb_table.get_item(Key={"PK": "ENTITY1#123", "SK": "ENTITY1#123"})
    assertpy.assert_that(item.get("Item")).is_equal_to(
        {
            "PK": "ENTITY1#123",
            "SK": "ENTITY1#123",
            "id": "123",
            "name": "Name",
            "entity": "ENTITY1",
            "nullable_attribute": None,
        }
    )


def test_repository_add_when_configured_exclude_none_should_omit_none(
    mock_dynamodb, backend_app_dynamodb_table, test_table_name
):
    # ARRANGE
    uow = dynamodb_unit_of_work.DynamoDBUnitOfWork(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        repo_factories=EntityConfigurator(table_name=test_table_name).repo_factories(),
        logger=mock.create_autospec(spec=logging.Logger),
    )
    # ACT
    with uow:
        uow.get_repository(GarageId, Garage).add(Garage(id_1="123", id_2="321", name="Name", status="Status"))

        uow.commit()

    # ASSERT
    item = backend_app_dynamodb_table.get_item(Key={"PK": "ENTITY2#123", "SK": "ID2#321"})
    assertpy.assert_that(item.get("Item")).is_equal_to(
        {
            "PK": "ENTITY2#123",
            "SK": "ID2#321",
            "id_1": "123",
            "id_2": "321",
            "name": "Name",
            "QSK_PK": "ID2#321",
            "QSK_SK": "ENTITY2#Status#123",
            "status": "Status",
        }
    )


def test_repository_add_when_upsert_not_allowed_should_raise(
    mock_dynamodb, backend_app_dynamodb_table, test_table_name
):
    # ARRANGE
    uow = dynamodb_unit_of_work.DynamoDBUnitOfWork(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        repo_factories=EntityConfigurator(table_name=test_table_name).repo_factories(),
        logger=mock.create_autospec(spec=logging.Logger),
    )
    with uow:
        uow.get_repository(CarId, Car).add(Car(id="123", name="Name"))

        uow.commit()

    # ACT
    with pytest.raises(Exception):
        with uow:
            uow.get_repository(CarId, Car).add(Car(id="123", name="Name"))

            uow.commit()


def test_repository_add_when_upsert_allowed_should_not_raise(
    mock_dynamodb, backend_app_dynamodb_table, test_table_name
):
    # ARRANGE
    uow = dynamodb_unit_of_work.DynamoDBUnitOfWork(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        repo_factories=EntityConfigurator(table_name=test_table_name).repo_factories(),
        logger=mock.create_autospec(spec=logging.Logger),
    )
    with uow:
        uow.get_repository(GarageId, Garage).add(Garage(id_1="123", id_2="321", name="Name", status="Active"))

        uow.commit()

    # ACT
    with uow:
        uow.get_repository(GarageId, Garage).add(Garage(id_1="123", id_2="321", name="Name2", status="Inactive"))

        uow.commit()

    # ASSERT
    item = backend_app_dynamodb_table.get_item(Key={"PK": "ENTITY2#123", "SK": "ID2#321"})
    assertpy.assert_that(item.get("Item")).is_equal_to(
        {
            "id_1": "123",
            "id_2": "321",
            "name": "Name2",
            "status": "Inactive",
            "PK": "ENTITY2#123",
            "SK": "ID2#321",
            "QSK_PK": "ID2#321",
            "QSK_SK": "ENTITY2#Inactive#123",
        }
    )


def test_repository_update_attributes_when_has_update_modifiers_should_apply_before_update(
    mock_dynamodb, backend_app_dynamodb_table, test_table_name
):
    # ARRANGE
    uow = dynamodb_unit_of_work.DynamoDBUnitOfWork(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        repo_factories=EntityConfigurator(table_name=test_table_name).repo_factories(),
        logger=mock.create_autospec(spec=logging.Logger),
    )
    with uow:
        uow.get_repository(GarageId, Garage).add(
            Garage(id_1="123", id_2="321", name="Name", status="Active", doors=[GarageDoor(side="left")])
        )

        uow.commit()

    # ACT
    with uow:
        uow.get_repository(GarageId, Garage).update_attributes(
            GarageId(id_1="123", id_2="321"),
            status="Inactive",
            id_1="123",
            id_2="321",
        )

        uow.commit()

    # ASSERT
    item = backend_app_dynamodb_table.get_item(Key={"PK": "ENTITY2#123", "SK": "ID2#321"})
    assertpy.assert_that(item.get("Item")).is_equal_to(
        {
            "PK": "ENTITY2#123",
            "QSK_PK": "ID2#321",
            "QSK_SK": "ENTITY2#Inactive#123",
            "SK": "ID2#321",
            "id_1": "123",
            "id_2": "321",
            "name": "Name",
            "status": "Inactive",
            "doors": [{"side": "left"}],
        }
    )


def test_repository_update_attributes_when_has_exclude_none_should_remove_attributes_with_none_value(
    mock_dynamodb, backend_app_dynamodb_table, test_table_name
):
    # ARRANGE
    uow = dynamodb_unit_of_work.DynamoDBUnitOfWork(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        repo_factories=EntityConfigurator(table_name=test_table_name).repo_factories(),
        logger=mock.create_autospec(spec=logging.Logger),
    )
    with uow:
        uow.get_repository(GarageId, Garage).add(
            Garage(id_1="123", id_2="321", name="Name", status="Active", doors=[GarageDoor(side="left")])
        )

        uow.commit()

    # ACT
    with uow:
        uow.get_repository(GarageId, Garage).update_attributes(
            GarageId(id_1="123", id_2="321"),
            status="Inactive",
            id_1="123",
            id_2="321",
            doors=None,
        )

        uow.commit()

    # ASSERT
    item = backend_app_dynamodb_table.get_item(Key={"PK": "ENTITY2#123", "SK": "ID2#321"})
    assertpy.assert_that(item.get("Item")).is_equal_to(
        {
            "PK": "ENTITY2#123",
            "QSK_PK": "ID2#321",
            "QSK_SK": "ENTITY2#Inactive#123",
            "SK": "ID2#321",
            "id_1": "123",
            "id_2": "321",
            "name": "Name",
            "status": "Inactive",
        }
    )


def test_repository_update_attributes_when_has_exclude_none_should_remove_attributes_when_already_nonexisting(
    mock_dynamodb, backend_app_dynamodb_table, test_table_name
):
    # ARRANGE
    uow = dynamodb_unit_of_work.DynamoDBUnitOfWork(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        repo_factories=EntityConfigurator(table_name=test_table_name).repo_factories(),
        logger=mock.create_autospec(spec=logging.Logger),
    )
    with uow:
        uow.get_repository(GarageId, Garage).add(Garage(id_1="123", id_2="321", name="Name", status="Active"))

        uow.commit()

    # ACT
    with uow:
        uow.get_repository(GarageId, Garage).update_attributes(
            GarageId(id_1="123", id_2="321"),
            status="Inactive",
            id_1="123",
            id_2="321",
            doors=None,
        )

        uow.commit()

    # ASSERT
    item = backend_app_dynamodb_table.get_item(Key={"PK": "ENTITY2#123", "SK": "ID2#321"})
    assertpy.assert_that(item.get("Item")).is_equal_to(
        {
            "PK": "ENTITY2#123",
            "QSK_PK": "ID2#321",
            "QSK_SK": "ENTITY2#Inactive#123",
            "SK": "ID2#321",
            "id_1": "123",
            "id_2": "321",
            "name": "Name",
            "status": "Inactive",
        }
    )


def test_repository_update_attributes_when_does_not_have_exclude_none_should_not_remove_attributes(
    mock_dynamodb, backend_app_dynamodb_table, test_table_name
):
    # ARRANGE
    uow = dynamodb_unit_of_work.DynamoDBUnitOfWork(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        repo_factories=EntityConfigurator(table_name=test_table_name).repo_factories(),
        logger=mock.create_autospec(spec=logging.Logger),
    )
    with uow:
        uow.get_repository(CarId, Car).add(Car(id="123", name="Name"))

        uow.commit()

    # ACT
    with uow:
        uow.get_repository(CarId, Car).update_attributes(
            CarId(id="123"),
            nullable_attribute=None,
        )

        uow.commit()

    # ASSERT
    item = backend_app_dynamodb_table.get_item(Key={"PK": "ENTITY1#123", "SK": "ENTITY1#123"})
    assertpy.assert_that(item.get("Item")).is_equal_to(
        {
            "PK": "ENTITY1#123",
            "SK": "ENTITY1#123",
            "id": "123",
            "name": "Name",
            "entity": "ENTITY1",
            "nullable_attribute": None,
        }
    )


def test_repository_update_attributes_when_has_update_modifiers_but_no_params_should_not_apply_before_update(
    mock_dynamodb, backend_app_dynamodb_table, test_table_name
):
    # ARRANGE
    uow = dynamodb_unit_of_work.DynamoDBUnitOfWork(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        repo_factories=EntityConfigurator(table_name=test_table_name).repo_factories(),
        logger=mock.create_autospec(spec=logging.Logger),
    )
    with uow:
        uow.get_repository(GarageId, Garage).add(Garage(id_1="123", id_2="321", name="Name", status="Active"))

        uow.commit()

    # ACT
    with uow:
        uow.get_repository(GarageId, Garage).update_attributes(
            GarageId(id_1="123", id_2="321"),
            name="Test Name",
        )

        uow.commit()

    # ASSERT
    item = backend_app_dynamodb_table.get_item(Key={"PK": "ENTITY2#123", "SK": "ID2#321"})
    assertpy.assert_that(item.get("Item")).is_equal_to(
        {
            "PK": "ENTITY2#123",
            "QSK_PK": "ID2#321",
            "QSK_SK": "ENTITY2#Active#123",
            "SK": "ID2#321",
            "id_1": "123",
            "id_2": "321",
            "name": "Test Name",
            "status": "Active",
        }
    )


def test_repository_update_entity_when_attributes_have_changed_should_update(
    mock_dynamodb, backend_app_dynamodb_table, test_table_name
):
    # ARRANGE
    uow = dynamodb_unit_of_work.DynamoDBUnitOfWork(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        repo_factories=EntityConfigurator(table_name=test_table_name).repo_factories(),
        logger=mock.create_autospec(spec=logging.Logger),
    )

    entity = Garage(id_1="123", id_2="321", name="Name", status="Active")
    with uow:
        uow.get_repository(GarageId, Garage).add(entity)

        uow.commit()

    # ACT
    entity.status = "Inactive"
    entity.doors = [GarageDoor(side="Left"), GarageDoor(side="Right")]

    with uow:
        uow.get_repository(GarageId, Garage).update_entity(GarageId(id_1="123", id_2="321"), entity)

        uow.commit()

    # ASSERT
    item = backend_app_dynamodb_table.get_item(Key={"PK": "ENTITY2#123", "SK": "ID2#321"})
    assertpy.assert_that(item.get("Item")).is_equal_to(
        {
            "PK": "ENTITY2#123",
            "QSK_PK": "ID2#321",
            "QSK_SK": "ENTITY2#Inactive#123",
            "SK": "ID2#321",
            "id_1": "123",
            "id_2": "321",
            "name": "Name",
            "status": "Inactive",
            "doors": [{"side": "Left"}, {"side": "Right"}],
        }
    )


def test_repository_update_entity_when_attributes_have_not_changed_should_not_update(
    mock_dynamodb, backend_app_dynamodb_table, test_table_name
):
    # ARRANGE
    uow = dynamodb_unit_of_work.DynamoDBUnitOfWork(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        repo_factories=EntityConfigurator(table_name=test_table_name).repo_factories(),
        logger=mock.create_autospec(spec=logging.Logger),
    )

    entity = Service(id_1="123", id_2="321", service_label="label-123", service_type="Paddock", state="Closed")
    with uow:
        uow.get_repository(ServiceId, Service).add(entity)

        uow.commit()

    # ACT
    entity.state = "Open"

    with uow:
        uow.get_repository(ServiceId, Service).update_entity(ServiceId(id_1="123", id_2="321"), entity)

        uow.commit()

    # ASSERT
    item = backend_app_dynamodb_table.get_item(Key={"PK": "SERVICE#123", "SK": "SERVICE#321"})
    assertpy.assert_that(item.get("Item")).is_equal_to(
        {
            "PK": "SERVICE#123",
            "SK": "SERVICE#321",
            "id_1": "123",
            "id_2": "321",
            "service_label": "label-123",
            "service_type": "Paddock",
            "state": "Open",
            "QSK_PK": "label-123#Paddock",
            "QSK_SK": "Paddock#Open",
        }
    )


def test_repository_update_entity_when_has_optimistic_concurrency_should_raise(
    mock_dynamodb, backend_app_dynamodb_table, test_table_name
):
    # ARRANGE
    uow = dynamodb_unit_of_work.DynamoDBUnitOfWork(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        repo_factories=EntityConfigurator(table_name=test_table_name).repo_factories(),
        logger=mock.create_autospec(spec=logging.Logger),
    )

    entity = Engine(id="123", name="Internal Combustion")
    with uow:
        uow.get_repository(EngineId, Engine).add(entity)
        uow.commit()

        entity_0 = uow.get_repository(EngineId, Engine).get(EngineId(id="123"))

    entity_0.name = "Electric"

    entity_1 = None
    with uow:
        uow.get_repository(EngineId, Engine).update_entity(EngineId(id="123"), entity_0)
        uow.commit()

        entity_1 = uow.get_repository(EngineId, Engine).get(EngineId(id="123"))

    entity_1.name = "Diesel"

    # ACT
    with pytest.raises(Exception):
        with uow:
            uow.get_repository(EngineId, Engine).update_entity(EngineId(id="123"), entity_0)
            uow.commit()

    with uow:
        uow.get_repository(EngineId, Engine).update_entity(EngineId(id="123"), entity_1)
        uow.commit()

    # ASSERT
    item = backend_app_dynamodb_table.get_item(Key={"PK": "ENGINE#123", "SK": "ENGINE#123"})
    assertpy.assert_that(item.get("Item")).is_equal_to(
        {"PK": "ENGINE#123", "SK": "ENGINE#123", "id": "123", "name": "Diesel", "sequenceNo": decimal.Decimal("2")}
    )


def test_repository_add_entity_when_not_allow_upsert_and_has_optimistic_concurrency_should_raise(test_table_name):
    # ACT
    with pytest.raises(repository_exception.RepositoryException) as exc:
        UpsertWithOptimisticConcurrencyControlConfigurator(table_name=test_table_name).repo_factories()

    # ASSERT
    assertpy.assert_that(str(exc.value)).contains("Cannot have both allow upsert and optimistic concurrency control.")


def test_repository_get_should_get_entity(mock_dynamodb, backend_app_dynamodb_table, test_table_name):
    # ARRANGE
    uow = dynamodb_unit_of_work.DynamoDBUnitOfWork(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        repo_factories=EntityConfigurator(table_name=test_table_name).repo_factories(),
        logger=mock.create_autospec(spec=logging.Logger),
    )
    test_entity = Car(id="123", name="Name")

    with uow:
        uow.get_repository(CarId, Car).add(test_entity)
        uow.commit()

    # ACT
    with uow:
        ent = uow.get_repository(CarId, Car).get(CarId(id="123"))

    # ASSERT
    assertpy.assert_that(ent).is_equal_to(test_entity)


def test_repository_remove_should_delete_entity(mock_dynamodb, backend_app_dynamodb_table, test_table_name):
    # ARRANGE
    uow = dynamodb_unit_of_work.DynamoDBUnitOfWork(
        table_name=test_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        repo_factories=EntityConfigurator(table_name=test_table_name).repo_factories(),
        logger=mock.create_autospec(spec=logging.Logger),
    )
    test_entity = Car(id="123", name="Name")

    with uow:
        uow.get_repository(CarId, Car).add(test_entity)
        uow.commit()

    # ACT
    with uow:
        uow.get_repository(CarId, Car).remove(CarId(id="123"))
        uow.commit()

    # ASSERT
    item = backend_app_dynamodb_table.get_item(Key={"PK": "ENTITY1#123", "SK": "ENTITY1#123"})
    assertpy.assert_that(item.get("Item", None)).is_none()


def test_entity_when_has_changes():
    # ARRANGE
    e0 = Garage(id_1="123", id_2="321", name="Name", status="Active", doors=[GarageDoor(side="left")])
    e1 = Garage(id_1="123", id_2="321", name="Name", status="Active", doors=None)
    e2 = Garage(id_1="123", id_2="321", name="Name", status="Active", doors=None)

    # ACT
    e0.doors.append(GarageDoor(side="right"))
    e1.doors = [GarageDoor(side="left")]
    e2.status = "Inactive"

    # ASSERT
    assertpy.assert_that(e0.has_changes).is_true()
    assertpy.assert_that(e1.has_changes).is_true()
    assertpy.assert_that(e2.has_changes).is_true()


def test_entity_when_does_not_have_chanes():
    # ARRANGE
    e0 = Garage(id_1="123", id_2="321", name="Name", status="Active", doors=[GarageDoor(side="left")])
    e1 = Garage(id_1="123", id_2="321", name="Name", status="Active", doors=None)

    # ASSERT
    assertpy.assert_that(e0.has_changes).is_false()
    assertpy.assert_that(e1.has_changes).is_false()


def test_entity_when_has_changes_but_refresh():
    # ARRANGE
    e0 = Garage(id_1="123", id_2="321", name="Name", status="Active", doors=[GarageDoor(side="left")])
    e1 = Garage(id_1="123", id_2="321", name="Name", status="Active", doors=None)
    e2 = Garage(id_1="123", id_2="321", name="Name", status="Active", doors=None)

    # ACT
    e0.doors.append(GarageDoor(side="right"))
    e0.refresh_changes()
    e1.doors = [GarageDoor(side="left")]
    e1.refresh_changes()
    e2.status = "Inactive"
    e2.refresh_changes()

    # ASSERT
    assertpy.assert_that(e0.has_changes).is_false()
    assertpy.assert_that(e1.has_changes).is_false()
    assertpy.assert_that(e2.has_changes).is_false()
