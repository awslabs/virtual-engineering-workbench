import enum

from app.publishing.adapters.services import dynamo_db_repositories as legacy_ddb_uow
from app.publishing.domain.model import portfolio, product, shared_ami, version
from app.publishing.domain.read_models import ami
from app.shared.adapters.unit_of_work_v2 import (
    dynamodb_repo_config,
    dynamodb_repository,
)


class DBPrefix(enum.StrEnum):
    Ami = "AMI"
    SharedAmi = "SHARED_AMI"
    AwsAccount = "AWS_ACCOUNT"
    Product = "PRODUCT"
    Project = "PROJECT"
    Version = "VERSION"
    Technology = "TECHNOLOGY"

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
        super().__init__(table_name)
        self.register_cfg(
            shared_ami.SharedAmiPrimaryKey,
            shared_ami.SharedAmi,
            self.shared_ami_entity_config,
        )
        self.register_cfg(version.VersionPrimaryKey, version.Version, self.version_entity_config)
        self.register_cfg(product.ProductPrimaryKey, product.Product, self.product_entity_config)
        self.register_cfg(
            portfolio.PortfolioPrimaryKey,
            portfolio.Portfolio,
            self.portfolio_entity_config,
        )
        self.register_cfg(ami.AmiPrimaryKey, ami.Ami, self.ami_entity_config)

    def shared_ami_entity_config(
        self,
        cfg: dynamodb_repo_config.GenericDynamoDBRepositoryConfig[shared_ami.SharedAmiPrimaryKey, shared_ami.SharedAmi],
    ):
        # ex. AMI#ami-1234
        cfg.partition_key(
            name="PK",
            value_template=lambda image_ami_id: f"{DBPrefix.Ami}#{image_ami_id}",
            values_from_entity=lambda ent: ent.originalAmiId,
            values_from_primary_key=lambda pk: pk.originalAmiId,
        )

        # ex. AWS_ACCOUNT#12345678912
        cfg.sort_key(
            name="SK",
            value_template=lambda account_id: f"{DBPrefix.AwsAccount}#{account_id}",
            values_from_entity=lambda ent: ent.awsAccountId,
            values_from_primary_key=lambda pk: pk.awsAccountId,
        )

        cfg.enable_query_all(gsi_partition_key_attribute_name=legacy_ddb_uow.DBPrefix.SHARED_AMI)

    def version_entity_config(
        self,
        cfg: dynamodb_repo_config.GenericDynamoDBRepositoryConfig[shared_ami.SharedAmiPrimaryKey, shared_ami.SharedAmi],
    ):
        # ex. PRODUCT#prod-12345
        cfg.partition_key(
            name="PK",
            value_template=lambda product_id: f"{DBPrefix.Product}#{product_id}",
            values_from_entity=lambda ent: ent.productId,
            values_from_primary_key=lambda pk: pk.productId,
        )

        # ex. VERSION#vers-12345#AWS_ACCOUNT#12345678912
        cfg.sort_key(
            name="SK",
            value_template=lambda version_id, aws_account_id: f"{DBPrefix.Version}#{version_id}#{DBPrefix.AwsAccount}#{aws_account_id}",
            values_from_entity=lambda ent: [ent.versionId, ent.awsAccountId],
            values_from_primary_key=lambda pk: [pk.versionId, pk.awsAccountId],
        )

        cfg.enable_query_all(gsi_partition_key_attribute_name=legacy_ddb_uow.DBPrefix.VERSION)

    def product_entity_config(
        self,
        cfg: dynamodb_repo_config.GenericDynamoDBRepositoryConfig[product.ProductPrimaryKey, product.Product],
    ):
        # ex. PROJECT#proj-123
        cfg.partition_key(
            name="PK",
            value_template=lambda project_id: f"{DBPrefix.Project}#{project_id}",
            values_from_entity=lambda ent: ent.projectId,
            values_from_primary_key=lambda pk: pk.projectId,
        )

        # ex. PRODUCT#prod-123
        cfg.sort_key(
            name="SK",
            value_template=lambda product_id: f"{DBPrefix.Product}#{product_id}",
            values_from_entity=lambda ent: ent.productId,
            values_from_primary_key=lambda pk: pk.productId,
        )

        cfg.enable_query_all(gsi_partition_key_attribute_name=legacy_ddb_uow.DBPrefix.PRODUCT)

    def portfolio_entity_config(
        self,
        cfg: dynamodb_repo_config.GenericDynamoDBRepositoryConfig[portfolio.PortfolioPrimaryKey, portfolio.Portfolio],
    ):
        # ex. TECHNOLOGY#tech-123
        cfg.partition_key(
            name="PK",
            value_template=lambda technology_id: f"{DBPrefix.Technology}#{technology_id}",
            values_from_entity=lambda ent: ent.technologyId,
            values_from_primary_key=lambda pk: pk.technologyId,
        )

        # ex. AWS_ACCOUNT#0000000000
        cfg.sort_key(
            name="SK",
            value_template=lambda aws_account_id: f"{DBPrefix.AwsAccount}#{aws_account_id}",
            values_from_entity=lambda ent: ent.awsAccountId,
            values_from_primary_key=lambda pk: pk.awsAccountId,
        )

        cfg.enable_query_all(gsi_partition_key_attribute_name=legacy_ddb_uow.DBPrefix.PORTFOLIO)

    def ami_entity_config(
        self,
        cfg: dynamodb_repo_config.GenericDynamoDBRepositoryConfig[ami.AmiPrimaryKey, ami.Ami],
    ):
        # ex. AMI#ami-1234
        cfg.partition_key(
            name="PK",
            value_template=lambda ami_id: f"{DBPrefix.Ami}#{ami_id}",
            values_from_entity=lambda ent: ent.amiId,
            values_from_primary_key=lambda pk: pk.amiId,
        )

        # ex. AWS_ACCOUNT#00000000
        cfg.sort_key(
            name="SK",
            value_template=lambda ami_id: f"{DBPrefix.Ami}#{ami_id}",
            values_from_entity=lambda ent: ent.amiId,
            values_from_primary_key=lambda pk: pk.amiId,
        )

        cfg.enable_query_all(gsi_partition_key_attribute_name=legacy_ddb_uow.DBPrefix.AMI)
