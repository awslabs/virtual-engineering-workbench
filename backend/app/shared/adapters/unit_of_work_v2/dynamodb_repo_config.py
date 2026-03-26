import builtins
import inspect
import typing

from app.shared.adapters.unit_of_work_v2 import repository_exception, unit_of_work

AttributeValueTemplate: typing.TypeAlias = typing.Union[
    typing.Callable[[str], str],
    typing.Callable[[str, str], str],
    typing.Callable[[str, str, str], str],
    typing.Callable[[str, str, str, str], str],
]

ATTRIBUTE_NAME_ENTITY = "entity"

T = typing.TypeVar("T", bound=unit_of_work.Entity)
TPrimaryKey = typing.TypeVar("TPrimaryKey")


def get_unbound_closure_vars(func: typing.Any) -> list[str]:
    """
    Get the names of all unbound member attributes inside a lambda function.
    This code is copied from inspect.getclosurevars Python library.
    Python implementation to get unbound variables returns a set, which can be in a random order.
    For member expression to work we need it in the specified order.

    Returns a list of all member names.
    """

    if inspect.ismethod(func):
        func = func.__func__

    if not inspect.isfunction(func):
        raise TypeError("{!r} is not a Python function".format(func))

    code = func.__code__

    global_ns = func.__globals__
    builtin_ns = global_ns.get("__builtins__", builtins.__dict__)
    if inspect.ismodule(builtin_ns):
        builtin_ns = builtin_ns.__dict__
    unbound_names = []
    for name in code.co_names:
        if name in ("None", "True", "False"):
            # Because these used to be builtins instead of keywords, they
            # may still show up as name references. We ignore them.
            continue

        # the below line exludes build in names. However, some entities have
        # "id" attribute for example. The set is to explicitly allow these
        if name not in global_ns and (name not in builtin_ns or name in {"id"}):
            unbound_names.append(name)

    return unbound_names


class DynamicEntityAttribute(typing.Generic[TPrimaryKey, T]):
    """
    Stores a modifier configuration for a single entity attribute.
    All entity attributes that need to be auto-generated before storing in DynamoDB will use this class.
    For example:
        * "PK": "ENTITY_NAME#<entity_id>"
        * "SK": "ARBITRARY_PREFIX#<another_id>"
        * "GSI_SK": "ARBITRARY_PREFIX#<entity_status>#<another_id>"
    """

    def __init__(
        self,
        primary_key_type: typing.Type[unit_of_work.TPrimaryKey],
        attribute_name: str,
        attribute_value_template: AttributeValueTemplate,
        attribute_value_resolvers: typing.Callable[[unit_of_work.T], list[str] | str],
        attribute_value_resolvers_form_pk: typing.Callable[[unit_of_work.TPrimaryKey], list[str] | str] | None = None,
    ) -> None:
        self._primary_key_type = primary_key_type
        self._attribute_name = attribute_name
        self._attribute_value_template = attribute_value_template
        self._attribute_value_resolvers = attribute_value_resolvers
        self._attribute_value_resolvers_form_pk = attribute_value_resolvers_form_pk

    def resolve_from_entity(self, entity: unit_of_work.T) -> str:
        """
        Resolves attribute value to be saved in DynamoDB using entity members.
        """
        values = self._attribute_value_resolvers(entity)
        if type(values) is list:
            return self._resolve_from_values(values)

        return self._resolve_from_values([values])

    def resolve_from_dictionary(self, kwargs: dict):
        """
        Resolves attribute value to be saved in DynamoDB using dictionary items.
        Includes validation in case dictionary does not include a value for a pre-configured dynamic attribute.
        """
        member_variables = self.attributes_for_update
        required_attributes = self.required_attributes_for_update

        missing_params = required_attributes - set(kwargs.keys())
        if missing_params and len(missing_params) == len(required_attributes):
            return None

        if missing_params:
            raise Exception(
                f"Error resolving value for {self._attribute_name}: parameters {missing_params} not provided."
            )

        return self._resolve_from_values([kwargs.get(param_name) for param_name in member_variables])

    def resolve_from_primary_key(self, primary_key: unit_of_work.TPrimaryKey) -> str | None:
        """
        Resolves attribute value based on entity primary key.
        """
        values = self._attribute_value_resolvers_form_pk(primary_key)

        if type(values) is list:
            return self._resolve_from_values(values)

        return self._resolve_from_values([values])

    def _resolve_from_values(self, values: list) -> str:
        return self._attribute_value_template(*values)

    @property
    def attribute_name(self):
        return self._attribute_name

    @property
    def attributes_for_update(self):
        """Gets a list of attribute names for successfully generating a dynamic attribute"""
        return get_unbound_closure_vars(self._attribute_value_resolvers)

    @property
    def required_attributes_for_update(self) -> set[str]:
        """Gets a list of required attribute names for successfully generating a dynamic attribute"""
        non_required_attributes: list[str] = self._primary_key_type.__fields__.keys()
        return set(self.attributes_for_update) - set(non_required_attributes)


class GenericDynamoDBRepositoryConfig(typing.Generic[TPrimaryKey, T]):
    """
    Instances of this class contain all needed configuration to store an anemic entity to the DynamoDB.
    It contains a list of entity modifiers that are invoked before:
        * adding a new entity
        * updating an entity
    """

    def __init__(
        self, primary_key_type: typing.Type[unit_of_work.TPrimaryKey], entity_type: typing.Type[unit_of_work.T]
    ) -> None:
        self._primary_key_type: typing.Type = primary_key_type
        self._entity_type: typing.Type = entity_type
        self._exclude_none: bool = False
        self._modifiers: list[typing.Callable[[unit_of_work.T], dict]] = [
            lambda ent: ent.dict(exclude_none=self._exclude_none)
        ]
        self._update_modifiers: list[typing.Callable[[dict], dict]] = []
        self._table_name: str | None = None
        self._partition_key_attribute: DynamicEntityAttribute | None = None
        self._sort_key_attribute: DynamicEntityAttribute | None = None
        self._allow_upsert: bool = False
        self._optimistic_concurrency_control: bool = False
        self._attribute_dependencies: dict[str, set[str]] = {}

    def set_table_name(self, table_name: str) -> typing.Self:
        """Sets the table name where entities are saved."""

        self._table_name = table_name
        return self

    def enable_query_all(self, gsi_partition_key_attribute_name: str) -> typing.Self:
        """
        Enables a query pattern to fetch all entities. This works by adding a modifier
        to generate a DynamoDB attribute "entity" with a provided entity name.
        """

        self._modifiers.append(
            lambda ent: GenericDynamoDBRepositoryConfig.create_attribute_dict_item(
                ATTRIBUTE_NAME_ENTITY, gsi_partition_key_attribute_name
            )
        )
        return self

    def partition_key(
        self,
        name: str,
        value_template: AttributeValueTemplate,
        values_from_entity: typing.Callable[[unit_of_work.T], list[str] | str],
        values_from_primary_key: typing.Callable[[unit_of_work.TPrimaryKey], list[str] | str],
    ) -> typing.Self:
        """
        Adds a modifier to generate a partition key attribute.

        Args:
            name: Name of the partition key attribute to be stored in DynamoDB.
            value_template: A function that returns an attribute value.
            values_from_entity: A list of functions to resolve values for the template using an entity.
            values_from_primary_key: A list of functions to resolve values for the template using a primary key.
        """

        return self._dynamic_attribute(
            DynamicEntityAttribute[unit_of_work.TPrimaryKey, unit_of_work.T](
                primary_key_type=self._primary_key_type,
                attribute_name=name,
                attribute_value_template=value_template,
                attribute_value_resolvers=values_from_entity,
                attribute_value_resolvers_form_pk=values_from_primary_key,
            ),
            partition_key=True,
        )

    def sort_key(
        self,
        name: str,
        value_template: AttributeValueTemplate,
        values_from_entity: typing.Callable[[unit_of_work.T], list[str] | str],
        values_from_primary_key: typing.Callable[[unit_of_work.TPrimaryKey], list[str] | str],
    ) -> typing.Self:
        """
        Adds a modifier to generate a sort key attribute.

        Args:
            name: Name of the sort key attribute to be stored in DynamoDB.
            value_template: A function that returns an attribute value.
            values_from_entity: A list of functions to resolve values for the template using an entity.
            values_from_primary_key: A list of functions to resolve values for the template using a primary key.
        """

        return self._dynamic_attribute(
            DynamicEntityAttribute[unit_of_work.TPrimaryKey, unit_of_work.T](
                primary_key_type=self._primary_key_type,
                attribute_name=name,
                attribute_value_template=value_template,
                attribute_value_resolvers=values_from_entity,
                attribute_value_resolvers_form_pk=values_from_primary_key,
            ),
            sort_key=True,
        )

    def enable_query_pattern(
        self,
        gsi_pk_name: str,
        gsi_pk_value_template: AttributeValueTemplate,
        gsi_pk_values_from_entity: typing.Callable[[unit_of_work.T], list[str] | str],
        gsi_sk_name: str | None = None,
        gsi_sk_value_template: AttributeValueTemplate | None = None,
        gsi_sk_values_from_entity: typing.Callable[[unit_of_work.T], list[str] | str] | None = None,
    ):
        """
        Enables a query pattern by adding 2 modifiers for global secondary index attributes.
        These modifiers will be invoked both when adding and updating an entity.
        For example:
            * "GSI_SK": "ARBITRARY_PREFIX#<entity_status>#<another_id>"

        Args:
            gsi_pk_name: Name of the GSI partition key attribute to be stored in DynamoDB.
            gsi_pk_value_template: A function that returns an attribute value.
            gsi_pk_values_from_entity: A list of functions to resolve values for the template using an entity.
            gsi_sk_name: Name of the GSI sort key attribute to be stored in DynamoDB.
            gsi_sk_value_template: A function that returns an attribute value.
            gsi_sk_values_from_entity: A list of functions to resolve values for the template using an entity.
        """

        self._dynamic_attribute(
            DynamicEntityAttribute[unit_of_work.TPrimaryKey, unit_of_work.T](
                primary_key_type=self._primary_key_type,
                attribute_name=gsi_pk_name,
                attribute_value_template=gsi_pk_value_template,
                attribute_value_resolvers=gsi_pk_values_from_entity,
            ),
            evaluate_on_update=True,
        )
        if gsi_sk_name:
            self._dynamic_attribute(
                DynamicEntityAttribute[unit_of_work.TPrimaryKey, unit_of_work.T](
                    primary_key_type=self._primary_key_type,
                    attribute_name=gsi_sk_name,
                    attribute_value_template=gsi_sk_value_template,
                    attribute_value_resolvers=gsi_sk_values_from_entity,
                ),
                evaluate_on_update=True,
            )
        return self

    def allow_upsert(self):
        """
        Allows the add operation to overwrite an entity if it already exists in the DynamoDB table.
        """

        self._allow_upsert = True

        self._check_invariants()

        return self

    def enable_optimistic_concurrency_control(self) -> typing.Self:
        self._optimistic_concurrency_control = True

        self._check_invariants()

        self._modifiers.append(
            lambda ent: GenericDynamoDBRepositoryConfig.create_attribute_dict_item(
                unit_of_work.ATTRIBUTE_NAME_SEQUENCE_NO, 0
            )
        )
        return self

    def exclude_none(self) -> typing.Self:
        self._exclude_none = True
        return self

    def _check_invariants(self):
        # Both optimistic concurrency control and upsert cannot be allowed.
        # Upsert using add function would override the sequence number of the entity.
        if self._optimistic_concurrency_control and self._allow_upsert:
            raise repository_exception.RepositoryException(
                "Cannot have both allow upsert and optimistic concurrency control."
            )

    def _dynamic_attribute(
        self,
        dynamic_attribute: DynamicEntityAttribute[unit_of_work.TPrimaryKey, unit_of_work.T],
        partition_key: bool = False,
        sort_key: bool = False,
        evaluate_on_update: bool = False,
    ):
        if partition_key:
            self._partition_key_attribute = dynamic_attribute

        if sort_key:
            self._sort_key_attribute = dynamic_attribute

        # Generate dynamic attribute from entity object when adding new entity via the repo
        def _resolver(ent):
            return GenericDynamoDBRepositoryConfig.create_attribute_dict_item(
                dynamic_attribute.attribute_name, dynamic_attribute.resolve_from_entity(ent)
            )

        self._modifiers.append(_resolver)
        if evaluate_on_update:

            self._update_dynamic_attribute_dependencies(dynamic_attribute=dynamic_attribute)

            # Generate dynamic attribute from dictionary when updating the entity via the repo
            def _update_resolver(dict):
                value = dynamic_attribute.resolve_from_dictionary(dict)
                if not value:
                    return {}
                return GenericDynamoDBRepositoryConfig.create_attribute_dict_item(
                    dynamic_attribute.attribute_name,
                    value,
                )

            self._update_modifiers.append(_update_resolver)

        return self

    def _update_dynamic_attribute_dependencies(
        self, dynamic_attribute: DynamicEntityAttribute[unit_of_work.TPrimaryKey, unit_of_work.T]
    ):
        for attribute_name in dynamic_attribute.required_attributes_for_update:
            deps = dynamic_attribute.required_attributes_for_update - set(attribute_name)
            if attribute_name in self._attribute_dependencies:
                self._attribute_dependencies[attribute_name] |= deps
            else:
                self._attribute_dependencies[attribute_name] = deps

    @staticmethod
    def create_attribute_dict_item(attribute_name: str, attribute_value: str | int) -> dict:
        return {attribute_name: attribute_value}

    @property
    def modifiers(self):
        return self._modifiers

    @property
    def update_modifiers(self):
        return self._update_modifiers

    @property
    def table_name(self):
        return self._table_name

    @property
    def entity_type(self):
        return self._entity_type

    @property
    def none_values_excluded(self):
        return self._exclude_none

    def entity_primary_key_to_dict(self, entity: unit_of_work.T) -> dict:
        """
        Generates entity primary key dictionary attributes based on entity members.
        """

        return self._create_primary_key_dict(
            pk_value=(
                self._partition_key_attribute.resolve_from_entity(entity) if self._partition_key_attribute else None
            ),
            sk_value=self._sort_key_attribute.resolve_from_entity(entity) if self._sort_key_attribute else None,
        )

    def primary_key_to_dict(self, primary_key: unit_of_work.TPrimaryKey) -> dict:
        """
        Generates entity primary key dictionary based on entity primary key object.
        """

        return self._create_primary_key_dict(
            pk_value=(
                self._partition_key_attribute.resolve_from_primary_key(primary_key)
                if self._partition_key_attribute
                else None
            ),
            sk_value=(
                self._sort_key_attribute.resolve_from_primary_key(primary_key) if self._sort_key_attribute else None
            ),
        )

    def _create_primary_key_dict(
        self, pk_value: typing.Optional[lambda: str], sk_value: typing.Optional[lambda: str]
    ) -> dict:
        partition_key = {}
        if self._partition_key_attribute and pk_value:
            partition_key = GenericDynamoDBRepositoryConfig.create_attribute_dict_item(
                self._partition_key_attribute.attribute_name,
                pk_value,
            )

        sort_key = {}
        if self._sort_key_attribute and sk_value:
            sort_key = GenericDynamoDBRepositoryConfig.create_attribute_dict_item(
                self._sort_key_attribute.attribute_name, sk_value
            )

        return {
            **partition_key,
            **sort_key,
        }

    @property
    def primary_key_attributes(self) -> list[str]:
        attr = [self._partition_key_attribute.attribute_name]
        if self._sort_key_attribute:
            attr.append(self._sort_key_attribute.attribute_name)
        return attr

    @property
    def upsert_allowed(self):
        return self._allow_upsert

    @property
    def optimistic_concurrency_control(self):
        return self._optimistic_concurrency_control

    def get_attribute_dependencies(self, attribute_name: str) -> set[str]:
        return self._attribute_dependencies.get(attribute_name, set())
