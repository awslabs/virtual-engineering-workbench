import enum
import hashlib

from app.provisioning.domain.model import (
    maintenance_window,
    product_status,
    provisioned_product,
    user_profile,
)
from app.provisioning.domain.read_models import product, version
from app.shared.adapters.unit_of_work_v2 import (
    dynamodb_repo_config,
    dynamodb_repository,
)

REPLICATION_FACTOR = 3


def generate_replication_id(source: str) -> int:
    return int(hashlib.sha256(str.encode(source)).hexdigest(), base=16) % REPLICATION_FACTOR


class DBPrefix(enum.StrEnum):
    PROJECT = "PROJECT"
    PRODUCT = "PRODUCT"
    VERSION = "VERSION"
    AWS_ACCOUNT = "AWS_ACCOUNT"
    PROVISIONED_PRODUCT = "PROVISIONED_PRODUCT"
    SC_PROVISIONED_PRODUCT = "SC_PROVISIONED_PRODUCT"
    SC_PROVISIONING_ARTIFACT = "SC_PROVISIONING_ARTIFACT"
    USER = "USER"
    USER_PROFILE = "USER_PROFILE"
    MAINTENANCE_WINDOW = "MAINTENANCE_WINDOW"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

    def __str__(self):
        return str(self.value)


class PagingParams(enum.StrEnum):
    PAGE_SIZE = "Limit"
    REQUEST_PAGING = "ExclusiveStartKey"
    RESPONSE_PAGING = "LastEvaluatedKey"

    def __str__(self):
        return str(self.value)


class EntityConfigurator(dynamodb_repository.DynamoDBEntityConfiguratorBase):
    def __init__(self, table_name: str) -> None:
        """DynamoDB Entity configuration for Provisioning BC.

        Provisioning BC DynamoDB table has the following Global Secondary Indexes:
        | Name                                   | Partition Key attr. | Sort Key attr. |
        |  -                                     | PK                  | SK             |
        | gsi_inverted_primary_key               | SK                  | PK             |
        | gsi_custom_query_by_alternative_key    | QPK_1               | SK             |
        | gsi_custom_query_by_alternative_key_2  | QPK_2               | SK             |
        | gsi_custom_query_by_user_key           | GSI_PK              | GSI_SK         |
        | gsi_custom_query_by_alternative_keys_3 | QPK_3               | QSK_3          |
        | gsi_custom_query_by_alternative_keys_4 | QPK_4               | SK             |

        These indexes can be reused across different entities.
        """

        super().__init__(table_name)
        self.register_cfg(
            product.ProductPrimaryKey,
            product.Product,
            self.product_entity_config,
        )
        self.register_cfg(
            version.VersionPrimaryKey,
            version.Version,
            self.version_entity_config,
        )
        self.register_cfg(
            provisioned_product.ProvisionedProductPrimaryKey,
            provisioned_product.ProvisionedProduct,
            self.provisioned_product_entity_config,
        )
        self.register_cfg(
            user_profile.UserProfilePrimaryKey,
            user_profile.UserProfile,
            self.user_profile_entity_config,
        )
        self.register_cfg(
            maintenance_window.MaintenanceWindowPrimaryKey,
            maintenance_window.MaintenanceWindow,
            self.maintenance_window_entity_config,
        )

    def product_entity_config(
        self,
        cfg: dynamodb_repo_config.GenericDynamoDBRepositoryConfig[product.ProductPrimaryKey, product.Product],
    ):
        entity_name = DBPrefix.PRODUCT

        cfg.partition_key(
            name="PK",
            value_template=lambda project_id: f"{DBPrefix.PROJECT}#{project_id}",
            values_from_entity=lambda ent: ent.projectId,
            values_from_primary_key=lambda pk: pk.projectId,
        )

        cfg.sort_key(
            name="SK",
            value_template=lambda product_id: f"{entity_name}#{product_id}",
            values_from_entity=lambda ent: ent.productId,
            values_from_primary_key=lambda pk: pk.productId,
        )
        cfg.allow_upsert()

    def version_entity_config(
        self,
        cfg: dynamodb_repo_config.GenericDynamoDBRepositoryConfig[version.VersionPrimaryKey, version.Version],
    ):
        entity_name = DBPrefix.VERSION

        cfg.partition_key(
            name="PK",
            value_template=lambda product_id: f"{DBPrefix.PRODUCT}#{product_id}",
            values_from_entity=lambda ent: ent.productId,
            values_from_primary_key=lambda pk: pk.productId,
        )

        cfg.sort_key(
            name="SK",
            value_template=lambda version_id, aws_account_id: f"{entity_name}#{version_id}#{DBPrefix.AWS_ACCOUNT}#{aws_account_id}",
            values_from_entity=lambda ent: [ent.versionId, ent.awsAccountId],
            values_from_primary_key=lambda pk: [pk.versionId, pk.awsAccountId],
        )

        """
        Enables querying by Service Catalog Provisioning Artifact ID using gsi_custom_query_by_alternative_key GSI.

        Examples:
        QPK_1: "SC_PROVISIONING_ARTIFACT_ID#pa-1234"
        SK: "VERSION#vers-123#AWS_ACCOUNT#001234567890"
        """
        cfg.enable_query_pattern(
            gsi_pk_name="QPK_1",
            gsi_pk_value_template=lambda sc_pa_id: f"{DBPrefix.SC_PROVISIONING_ARTIFACT}#{sc_pa_id}",
            gsi_pk_values_from_entity=lambda ent: ent.scProvisioningArtifactId,
        )
        cfg.allow_upsert()

    def provisioned_product_entity_config(
        self,
        cfg: dynamodb_repo_config.GenericDynamoDBRepositoryConfig[
            provisioned_product.ProvisionedProductPrimaryKey,
            provisioned_product.ProvisionedProduct,
        ],
    ):
        entity_name = DBPrefix.PROVISIONED_PRODUCT

        cfg.enable_optimistic_concurrency_control()

        cfg.partition_key(
            name="PK",
            value_template=lambda project_id: f"{DBPrefix.PROJECT}#{project_id}",
            values_from_entity=lambda ent: ent.projectId,
            values_from_primary_key=lambda pk: pk.projectId,
        )

        cfg.sort_key(
            name="SK",
            value_template=lambda provisioned_product_id: f"{entity_name}#{provisioned_product_id}",
            values_from_entity=lambda ent: ent.provisionedProductId,
            values_from_primary_key=lambda pk: pk.provisionedProductId,
        )

        """
        Enables querying by Service Catalog Provisioned Product ID using gsi_custom_query_by_alternative_key GSI.

        Examples:
        QPK_1: "SC_PROVISIONED_PRODUCT#pp-12345"
        SK: "PROVISIONED_PRODUCT#pp-1234"
        """
        cfg.enable_query_pattern(
            gsi_pk_name="QPK_1",
            gsi_pk_value_template=lambda sc_pp_id: f"{DBPrefix.SC_PROVISIONED_PRODUCT}#{sc_pp_id}",
            gsi_pk_values_from_entity=lambda ent: ent.scProvisionedProductId,
        )

        """
        Enables querying for Provisioned Products by User ID using gsi_custom_query_by_user_key GSI.
        GSI_SK attribute can be used to further filter by project ID and status.

        Examples:
        GSI_PK: "USER#T0011AA"
        GSI_SK: "PROVISIONED_PRODUCT#proj-123#RUNNING#pp-1234"
        """
        cfg.enable_query_pattern(
            gsi_pk_name="GSI_PK",
            gsi_pk_value_template=lambda user_id: f"{DBPrefix.USER}#{user_id}",
            gsi_pk_values_from_entity=lambda ent: ent.userId,
            gsi_sk_name="GSI_SK",
            gsi_sk_value_template=lambda project_id, status, provisioned_product_id: f"{DBPrefix.PROVISIONED_PRODUCT}#{project_id}#{status}#{provisioned_product_id}",
            gsi_sk_values_from_entity=lambda ent: [
                ent.projectId,
                ent.status,
                ent.provisionedProductId,
            ],
        )

        """
        Enables querying for all provisioned products by using gsi_custom_query_by_alternative_key_2 GSI.
        Also uses pre-defined replication factor to spread out the data for better data distribution.

        Examples:
        QPK_2: "PROVISIONED_PRODUCT#PART#2"
        SK: "PROVISIONED_PRODUCT#pp-1234"
        """
        cfg.enable_query_pattern(
            gsi_pk_name="QPK_2",
            gsi_pk_value_template=lambda provisioned_product_id: f"{DBPrefix.PROVISIONED_PRODUCT}#PART#{generate_replication_id(provisioned_product_id)}",
            gsi_pk_values_from_entity=lambda ent: ent.provisionedProductId,
        )

        """
        Enables querying for all active (non-terminated) provisioned products by product ID
        using gsi_custom_query_by_alternative_keys_3 GSI.

        Examples:
        QPK_3: "PRODUCT#prod-1234"
        QSK_3: "PROVISIONED_PRODUCT#ACTIVE#DEV#us-east-1#pp-1234"
        """
        active_pp_states = product_status.ProductStatus.active_statuses()
        cfg.enable_query_pattern(
            gsi_pk_name="QPK_3",
            gsi_pk_value_template=lambda product_id: f"{DBPrefix.PRODUCT}#{product_id}",
            gsi_pk_values_from_entity=lambda ent: ent.productId,
            gsi_sk_name="QSK_3",
            gsi_sk_value_template=lambda status, stage, region, provisioned_product_id: f"{DBPrefix.PROVISIONED_PRODUCT}#{DBPrefix.ACTIVE if status in active_pp_states else DBPrefix.INACTIVE}#{stage}#{region}#{provisioned_product_id}",
            gsi_sk_values_from_entity=lambda ent: [
                ent.status,
                ent.stage,
                ent.region,
                ent.provisionedProductId,
            ],
        )

        """
        Enables querying for all provisioned products by their status efficiently
        using gsi_custom_query_by_alternative_keys_4 GSI.

        Examples:
        QPK_4: "PROVISIONED_PRODUCT#RUNNING"
        SK: "PROVISIONED_PRODUCT#pp-123"
        """
        cfg.enable_query_pattern(
            gsi_pk_name="QPK_4",
            gsi_pk_value_template=lambda status: f"{DBPrefix.PROVISIONED_PRODUCT}#{status}",
            gsi_pk_values_from_entity=lambda ent: ent.status,
        )

        """
        Enables querying for all active (non-terminated) provisioned products by project ID
        using gsi_custom_query_by_alternative_keys_4 GSI.

        Examples:
        PK: "PROJECT#proj-1234"
        QSK_3: "PROVISIONED_PRODUCT#ACTIVE#DEV#us-east-1#pp-1234"
        """
        # No need to set any value since PK and QSK_3 are already set

    def user_profile_entity_config(
        self,
        cfg: dynamodb_repo_config.GenericDynamoDBRepositoryConfig[
            user_profile.UserProfilePrimaryKey, user_profile.UserProfile
        ],
    ):
        entity_name = DBPrefix.USER_PROFILE

        cfg.partition_key(
            name="PK",
            value_template=lambda user_id: f"{entity_name}#{user_id}",
            values_from_entity=lambda ent: ent.userId,
            values_from_primary_key=lambda pk: pk.userId,
        )

        cfg.sort_key(
            name="SK",
            value_template=lambda user_id: f"{entity_name}#{user_id}",
            values_from_entity=lambda ent: ent.userId,
            values_from_primary_key=lambda pk: pk.userId,
        )

    def maintenance_window_entity_config(
        self,
        cfg: dynamodb_repo_config.GenericDynamoDBRepositoryConfig[
            maintenance_window.MaintenanceWindowPrimaryKey,
            maintenance_window.MaintenanceWindow,
        ],
    ):
        entity_name = DBPrefix.MAINTENANCE_WINDOW

        cfg.partition_key(
            name="PK",
            value_template=lambda day, nearest_start_hour: f"{entity_name}#{day}#{nearest_start_hour}",
            values_from_entity=lambda ent: [ent.day, ent.nearestStartHour],
            values_from_primary_key=lambda pk: [pk.day, pk.nearestStartHour],
        )

        cfg.sort_key(
            name="SK",
            value_template=lambda user_id: f"{DBPrefix.USER}#{user_id}",
            values_from_entity=lambda ent: ent.userId,
            values_from_primary_key=lambda pk: pk.userId,
        )
