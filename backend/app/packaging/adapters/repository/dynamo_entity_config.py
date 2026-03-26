import enum

from app.packaging.domain.model.component import (
    component,
    component_project_association,
    component_version,
    component_version_test_execution,
    mandatory_components_list,
)
from app.packaging.domain.model.image import image
from app.packaging.domain.model.pipeline import pipeline
from app.packaging.domain.model.recipe import recipe, recipe_version, recipe_version_test_execution
from app.shared.adapters.unit_of_work_v2 import dynamodb_repo_config, dynamodb_repository

ATTRIBUTE_NAME_ENTITY = "entity"


class DBPrefix(enum.StrEnum):
    Arch = "ARCH"
    Arn = "ARN"
    Component = "COMPONENT"
    Execution = "EXECUTION"
    Image = "IMAGE"
    Instance = "INSTANCE"
    Os = "OS"
    Pipeline = "PIPELINE"
    Platform = "PLATFORM"
    Project = "PROJECT"
    Recipe = "RECIPE"
    Version = "VERSION"

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
            component.ComponentPrimaryKey,
            component.Component,
            self.component_entity_config,
        )
        self.register_cfg(
            component_project_association.ComponentProjectAssociationPrimaryKey,
            component_project_association.ComponentProjectAssociation,
            self.component_project_association_entity_config,
        )
        self.register_cfg(
            component_version.ComponentVersionPrimaryKey,
            component_version.ComponentVersion,
            self.component_version_entity_config,
        )
        self.register_cfg(
            component_version_test_execution.ComponentVersionTestExecutionPrimaryKey,
            component_version_test_execution.ComponentVersionTestExecution,
            self.component_version_test_execution_entity_config,
        )
        self.register_cfg(
            recipe.RecipePrimaryKey,
            recipe.Recipe,
            self.recipe_entity_config,
        )
        self.register_cfg(
            recipe_version.RecipeVersionPrimaryKey,
            recipe_version.RecipeVersion,
            self.recipe_version_entity_config,
        )
        self.register_cfg(
            image.ImagePrimaryKey,
            image.Image,
            self.image_entity_config,
        )
        self.register_cfg(
            recipe_version_test_execution.RecipeVersionTestExecutionPrimaryKey,
            recipe_version_test_execution.RecipeVersionTestExecution,
            self.recipe_version_test_execution_entity_config,
        )
        self.register_cfg(
            mandatory_components_list.MandatoryComponentsListPrimaryKey,
            mandatory_components_list.MandatoryComponentsList,
            self.mandatory_components_list_entity_config,
        )
        self.register_cfg(
            pipeline.PipelinePrimaryKey,
            pipeline.Pipeline,
            self.pipeline_entity_config,
        )

    def component_entity_config(
        self,
        cfg: dynamodb_repo_config.GenericDynamoDBRepositoryConfig[component.ComponentPrimaryKey, component.Component],
    ):
        entity_name = DBPrefix.Component

        cfg.partition_key(
            name="PK",
            value_template=lambda component_id: f"{entity_name}#{component_id}",
            values_from_entity=lambda ent: ent.componentId,
            values_from_primary_key=lambda pk: pk.componentId,
        )
        cfg.sort_key(
            name="SK",
            value_template=lambda component_id: f"{entity_name}#{component_id}",
            values_from_entity=lambda ent: ent.componentId,
            values_from_primary_key=lambda pk: pk.componentId,
        )
        cfg.enable_query_all(gsi_partition_key_attribute_name=entity_name)

    def component_project_association_entity_config(
        self,
        cfg: dynamodb_repo_config.GenericDynamoDBRepositoryConfig[
            component_project_association.ComponentProjectAssociationPrimaryKey,
            component_project_association.ComponentProjectAssociation,
        ],
    ):
        cfg.partition_key(
            name="PK",
            value_template=lambda component_id: f"{DBPrefix.Component}#{component_id}",
            values_from_entity=lambda ent: ent.componentId,
            values_from_primary_key=lambda pk: pk.componentId,
        )
        cfg.sort_key(
            name="SK",
            value_template=lambda project_id: f"{DBPrefix.Project}#{project_id}",
            values_from_entity=lambda ent: ent.projectId,
            values_from_primary_key=lambda pk: pk.projectId,
        )

    def component_version_entity_config(
        self,
        cfg: dynamodb_repo_config.GenericDynamoDBRepositoryConfig[
            component_version.ComponentVersionPrimaryKey, component_version.ComponentVersion
        ],
    ):
        cfg.partition_key(
            name="PK",
            value_template=lambda component_id: f"{DBPrefix.Component}#{component_id}",
            values_from_entity=lambda ent: ent.componentId,
            values_from_primary_key=lambda pk: pk.componentId,
        )
        cfg.sort_key(
            name="SK",
            value_template=lambda component_version_id: f"{DBPrefix.Version}#{component_version_id}",
            values_from_entity=lambda ent: ent.componentVersionId,
            values_from_primary_key=lambda pk: pk.componentVersionId,
        )
        cfg.enable_query_pattern(
            gsi_pk_name="GSI_PK",
            gsi_pk_value_template=lambda status: f"{DBPrefix.Version}#{status}",
            gsi_pk_values_from_entity=lambda ent: ent.status,
            gsi_sk_name="GSI_SK",
            gsi_sk_value_template=lambda component_version_id: f"{DBPrefix.Component}#{component_version_id}",
            gsi_sk_values_from_entity=lambda ent: ent.componentVersionId,
        )

    def component_version_test_execution_entity_config(
        self,
        cfg: dynamodb_repo_config.GenericDynamoDBRepositoryConfig[
            component_version_test_execution.ComponentVersionTestExecutionPrimaryKey,
            component_version_test_execution.ComponentVersionTestExecution,
        ],
    ):
        cfg.partition_key(
            name="PK",
            value_template=lambda component_version_id: f"{DBPrefix.Version}#{component_version_id}",
            values_from_entity=lambda ent: ent.componentVersionId,
            values_from_primary_key=lambda pk: pk.componentVersionId,
        )
        cfg.sort_key(
            name="SK",
            value_template=lambda test_execution_id, instance_id: "#".join(
                [
                    DBPrefix.Execution,
                    test_execution_id,
                    DBPrefix.Instance,
                    instance_id,
                ]
            ),
            values_from_entity=lambda ent: [ent.testExecutionId, ent.instanceId],
            values_from_primary_key=lambda pk: [pk.testExecutionId, pk.instanceId],
        )

    def recipe_entity_config(
        self,
        cfg: dynamodb_repo_config.GenericDynamoDBRepositoryConfig[recipe.RecipePrimaryKey, recipe.Recipe],
    ):
        cfg.partition_key(
            name="PK",
            value_template=lambda project_id: f"{DBPrefix.Project}#{project_id}",
            values_from_entity=lambda ent: ent.projectId,
            values_from_primary_key=lambda pk: pk.projectId,
        )
        cfg.sort_key(
            name="SK",
            value_template=lambda recipe_id: f"{DBPrefix.Recipe}#{recipe_id}",
            values_from_entity=lambda ent: ent.recipeId,
            values_from_primary_key=lambda pk: pk.recipeId,
        )

    def recipe_version_entity_config(
        self,
        cfg: dynamodb_repo_config.GenericDynamoDBRepositoryConfig[
            recipe_version.RecipeVersionPrimaryKey, recipe_version.RecipeVersion
        ],
    ):
        cfg.partition_key(
            name="PK",
            value_template=lambda recipe_id: f"{DBPrefix.Recipe}#{recipe_id}",
            values_from_entity=lambda ent: ent.recipeId,
            values_from_primary_key=lambda pk: pk.recipeId,
        )
        cfg.sort_key(
            name="SK",
            value_template=lambda recipe_version_id: f"{DBPrefix.Version}#{recipe_version_id}",
            values_from_entity=lambda ent: ent.recipeVersionId,
            values_from_primary_key=lambda pk: pk.recipeVersionId,
        )
        cfg.enable_query_pattern(
            gsi_pk_name="GSI_PK",
            gsi_pk_value_template=lambda status: f"{DBPrefix.Version}#{status}",
            gsi_pk_values_from_entity=lambda ent: ent.status,
            gsi_sk_name="GSI_SK",
            gsi_sk_value_template=lambda recipe_version_id: f"{DBPrefix.Recipe}#{recipe_version_id}",
            gsi_sk_values_from_entity=lambda ent: ent.recipeVersionId,
        )

    def image_entity_config(
        self,
        cfg: dynamodb_repo_config.GenericDynamoDBRepositoryConfig[image.ImagePrimaryKey, image.Image],
    ):
        cfg.partition_key(
            name="PK",
            value_template=lambda project_id: f"{DBPrefix.Project}#{project_id}",
            values_from_entity=lambda ent: ent.projectId,
            values_from_primary_key=lambda pk: pk.projectId,
        )
        cfg.sort_key(
            name="SK",
            value_template=lambda image_id: f"{DBPrefix.Image}#{image_id}",
            values_from_entity=lambda ent: ent.imageId,
            values_from_primary_key=lambda pk: pk.imageId,
        )
        cfg.enable_query_pattern(
            gsi_pk_name="QPK_ARN",
            gsi_pk_value_template=lambda image_build_version_arn: f"{DBPrefix.Arn}#{image_build_version_arn}",
            gsi_pk_values_from_entity=lambda ent: ent.imageBuildVersionArn,
        )
        cfg.enable_query_pattern(
            gsi_pk_name="QPK_RECIPE",
            gsi_pk_value_template=lambda recipe_id: f"{DBPrefix.Recipe}#{recipe_id}",
            gsi_pk_values_from_entity=lambda ent: ent.recipeId,
            gsi_sk_name="QSK_VERSION",
            gsi_sk_value_template=lambda recipe_version_name: f"{DBPrefix.Version}#{recipe_version_name}",
            gsi_sk_values_from_entity=lambda ent: ent.recipeVersionName,
        )
        cfg.enable_query_all(gsi_partition_key_attribute_name=DBPrefix.Image)
        cfg.exclude_none()

    def recipe_version_test_execution_entity_config(
        self,
        cfg: dynamodb_repo_config.GenericDynamoDBRepositoryConfig[
            recipe_version_test_execution.RecipeVersionTestExecutionPrimaryKey,
            recipe_version_test_execution.RecipeVersionTestExecution,
        ],
    ):
        cfg.partition_key(
            name="PK",
            value_template=lambda recipe_version_id: f"{DBPrefix.Version}#{recipe_version_id}",
            values_from_entity=lambda ent: ent.recipeVersionId,
            values_from_primary_key=lambda pk: pk.recipeVersionId,
        )
        cfg.sort_key(
            name="SK",
            value_template=lambda test_execution_id: f"{DBPrefix.Execution}#{test_execution_id}",
            values_from_entity=lambda ent: [ent.testExecutionId],
            values_from_primary_key=lambda pk: [pk.testExecutionId],
        )

    def mandatory_components_list_entity_config(
        self,
        cfg: dynamodb_repo_config.GenericDynamoDBRepositoryConfig[
            mandatory_components_list.MandatoryComponentsList,
            mandatory_components_list.MandatoryComponentsListPrimaryKey,
        ],
    ):
        cfg.partition_key(
            name="PK",
            value_template=lambda platform: f"{DBPrefix.Platform}#{platform}",
            values_from_entity=lambda ent: ent.mandatoryComponentsListPlatform,
            values_from_primary_key=lambda pk: pk.mandatoryComponentsListPlatform,
        )
        cfg.sort_key(
            name="SK",
            value_template=lambda os, architecture: "#".join(
                [
                    DBPrefix.Os,
                    os,
                    DBPrefix.Arch,
                    architecture,
                ]
            ),
            values_from_entity=lambda ent: [
                ent.mandatoryComponentsListOsVersion,
                ent.mandatoryComponentsListArchitecture,
            ],
            values_from_primary_key=lambda pk: [
                pk.mandatoryComponentsListOsVersion,
                pk.mandatoryComponentsListArchitecture,
            ],
        )

    def pipeline_entity_config(
        self,
        cfg: dynamodb_repo_config.GenericDynamoDBRepositoryConfig[pipeline.PipelinePrimaryKey, pipeline.Pipeline],
    ):
        cfg.partition_key(
            name="PK",
            value_template=lambda project_id: f"{DBPrefix.Project}#{project_id}",
            values_from_entity=lambda ent: ent.projectId,
            values_from_primary_key=lambda pk: pk.projectId,
        )
        cfg.sort_key(
            name="SK",
            value_template=lambda pipeline_id: f"{DBPrefix.Pipeline}#{pipeline_id}",
            values_from_entity=lambda ent: ent.pipelineId,
            values_from_primary_key=lambda pk: pk.pipelineId,
        )
