import enum

from app.authorization.domain.read_models import project_assignment
from app.shared.adapters.unit_of_work_v2 import (
    dynamodb_repo_config,
    dynamodb_repository,
)


class DBPrefix(enum.StrEnum):
    PROJECT = "PROJECT"
    USER = "USER"


class EntityConfigurator(dynamodb_repository.DynamoDBEntityConfiguratorBase):
    def __init__(self, table_name: str) -> None:
        """DynamoDB Entity configuration for Authorization BC.

        Authorization BC DynamoDB table has the following Global Secondary Indexes:
        | Name                                   | Partition Key attr. | Sort Key attr. |
        |  -                                     | PK                  | SK             |
        """

        super().__init__(table_name)
        self.register_cfg(
            project_assignment.AssignmentPrimaryKey,
            project_assignment.Assignment,
            self.project_assignment_entity_config,
        )

    def project_assignment_entity_config(
        self,
        cfg: dynamodb_repo_config.GenericDynamoDBRepositoryConfig[
            project_assignment.AssignmentPrimaryKey, project_assignment.Assignment
        ],
    ):
        cfg.partition_key(
            name="PK",
            value_template=lambda user_id: f"{DBPrefix.USER}#{user_id}",
            values_from_entity=lambda ent: ent.userId,
            values_from_primary_key=lambda pk: pk.userId,
        )

        cfg.sort_key(
            name="SK",
            value_template=lambda project_id: f"{DBPrefix.PROJECT}#{project_id}",
            values_from_entity=lambda ent: ent.projectId,
            values_from_primary_key=lambda pk: pk.projectId,
        )

        cfg.enable_optimistic_concurrency_control()
