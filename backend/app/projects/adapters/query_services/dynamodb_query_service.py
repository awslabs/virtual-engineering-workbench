import enum
from typing import Any, List, Optional, Tuple

from boto3.dynamodb.conditions import Attr, ConditionBase, Key
from mypy_boto3_dynamodb import client

from app.projects.adapters.repository import dynamo_entity_config
from app.projects.domain.exceptions import repository_exception
from app.projects.domain.model import (
    enrolment,
    project,
    project_account,
    project_assignment,
    technology,
    user,
)
from app.projects.domain.ports import (
    enrolment_query_service,
    projects_query_service,
    technologies_query_service,
)
from app.shared.adapters.boto import paging_utils
from app.shared.adapters.unit_of_work_v2 import dynamodb_repo_config


class AccountType(enum.Enum):
    USER = "USER"
    TOOLCHAIN = "TOOLCHAIN"

    def __str__(self):
        return str(self.value)


DDB_RESPONSE_PAGING_PARAM = "LastEvaluatedKey"
DDB_REQUEST_PAGING_PARAM = "ExclusiveStartKey"
DDB_PAGE_SIZE_PARAM = "Limit"


class DynamoDBProjectsQueryService(projects_query_service.ProjectsQueryService):
    """Projects DynamoDB query service."""

    def __init__(
        self,
        table_name: str,
        dynamodb_client: client.DynamoDBClient,
        gsi_inverted_primary_key: str,
        gsi_aws_accounts: str,
        gsi_entities: str,
        default_page_size: int | None = None,
    ):
        self._table_name = table_name
        self._dynamodb_client = dynamodb_client
        self._gsi_inverted_primary_key = gsi_inverted_primary_key
        self._gsi_aws_accounts = gsi_aws_accounts
        self._gsi_entities = gsi_entities
        self._default_page_size = default_page_size

    def list_projects_by_user(
        self, user_id: str, page_size: int, next_token: Any
    ) -> Tuple[List[project.Project], Any, List[project_assignment.Assignment]]:
        """Returns a list of all projects in repository with paging after 1 MB for a given user"""
        if next_token:
            result = self._dynamodb_client.query(
                TableName=self._table_name,
                KeyConditionExpression=Key("PK").eq(f"{dynamo_entity_config.DBPrefix.USER.value}#{user_id}")
                & Key("SK").begins_with(f"{dynamo_entity_config.DBPrefix.PROJECT.value}#"),
                Limit=page_size,
                ExclusiveStartKey=next_token,
            )
        else:
            result = self._dynamodb_client.query(
                TableName=self._table_name,
                KeyConditionExpression=Key("PK").eq(f"{dynamo_entity_config.DBPrefix.USER.value}#{user_id}")
                & Key("SK").begins_with(f"{dynamo_entity_config.DBPrefix.PROJECT.value}#"),
                Limit=page_size,
            )

        assignments = [project_assignment.Assignment.model_validate(item) for item in result["Items"]]

        if not assignments:
            return [], None, []

        # TODO: handle cases were a user have more than 100 different projects. Restriction coming from batch_get_item
        raw_projects = self._dynamodb_client.batch_get_item(
            RequestItems={
                self._table_name: {
                    "Keys": [
                        {
                            "PK": f"{dynamo_entity_config.DBPrefix.PROJECT.value}#{assignment.projectId}",
                            "SK": f"{dynamo_entity_config.DBPrefix.PROJECT.value}#{assignment.projectId}",
                        }
                        for assignment in assignments
                    ]
                },
            }
        )

        if "UnprocessedKeys" in raw_projects and raw_projects["UnprocessedKeys"]:
            raise repository_exception.RepositoryException("failed to fetch all projects details for user")
            # retry batch_get_item with exponential backup up to 3 times.
            # throw Exception in case 3rd retry fails or contains unprocessed keys

        projects = [project.Project.model_validate(item) for item in raw_projects["Responses"][self._table_name]]
        if "LastEvaluatedKey" in result:
            return projects, result["LastEvaluatedKey"], assignments
        else:
            return projects, None, assignments

    def list_projects(
        self, page_size: int, next_token: Any, user_id: Optional[str] = None
    ) -> Tuple[List[project.Project], Any, List[project_assignment.Assignment]]:
        """Returns a list of all projects in repository with paging after 1 MB."""

        assignments_result = []

        if user_id:
            assignments_result = self._dynamodb_client.query(
                TableName=self._table_name,
                Limit=page_size,
                KeyConditionExpression=Key("PK").eq(f"{dynamo_entity_config.DBPrefix.USER.value}#{user_id}")
                & Key("SK").begins_with(f"{dynamo_entity_config.DBPrefix.PROJECT.value}#"),
            )

        if next_token:
            projects_result = self._dynamodb_client.query(
                TableName=self._table_name,
                Limit=page_size,
                KeyConditionExpression=Key(dynamodb_repo_config.ATTRIBUTE_NAME_ENTITY).eq(
                    dynamo_entity_config.DBPrefix.PROJECT.value
                ),
                ExclusiveStartKey=next_token,
                IndexName=self._gsi_entities,
            )
        else:
            projects_result = self._dynamodb_client.query(
                TableName=self._table_name,
                Limit=page_size,
                KeyConditionExpression=Key(dynamodb_repo_config.ATTRIBUTE_NAME_ENTITY).eq(
                    dynamo_entity_config.DBPrefix.PROJECT.value
                ),
                IndexName=self._gsi_entities,
            )

        projects = [project.Project.model_validate(item) for item in projects_result["Items"]]

        if assignments_result:
            assignments = [project_assignment.Assignment.model_validate(item) for item in assignments_result["Items"]]
        else:
            assignments = []

        if "LastEvaluatedKey" in projects_result:
            return projects, projects_result["LastEvaluatedKey"], assignments
        else:
            return projects, None, assignments

    def list_project_accounts(
        self,
        project_id: str,
        account_type: Optional[str] = None,
        stage: Optional[str] = None,
        technology_id: Optional[str] = None,
    ) -> List[project_account.ProjectAccount]:
        """Returns a list of all accounts in a project."""

        filter_expression = self._build_filter_expression(account_type, stage, technology_id)

        query_params = {
            "TableName": self._table_name,
            "KeyConditionExpression": Key("PK").eq(f"{dynamo_entity_config.DBPrefix.PROJECT.value}#{project_id}")
            & Key("SK").begins_with(f"{dynamo_entity_config.DBPrefix.ACCOUNT.value}#"),
        }

        if filter_expression:
            query_params["FilterExpression"] = filter_expression

        if self._default_page_size:
            query_params[DDB_PAGE_SIZE_PARAM] = self._default_page_size

        project_accounts: list[project_account.ProjectAccount] = []

        while DDB_RESPONSE_PAGING_PARAM in (result := self._dynamodb_client.query(**query_params)):
            query_params[DDB_REQUEST_PAGING_PARAM] = result.get(DDB_RESPONSE_PAGING_PARAM)
            project_accounts.extend([project_account.ProjectAccount.model_validate(item) for item in result["Items"]])

        project_accounts.extend([project_account.ProjectAccount.model_validate(item) for item in result["Items"]])
        return project_accounts

    def list_project_accounts_by_aws_account(self, aws_account_id: str) -> List[project_account.ProjectAccount]:
        result = self._dynamodb_client.query(
            TableName=self._table_name,
            KeyConditionExpression=Key("awsAccountId").eq(aws_account_id),
            IndexName=self._gsi_aws_accounts,
        )

        pas = [project_account.ProjectAccount.model_validate(item) for item in result["Items"]]
        return pas

    def get_project_account_by_id(self, project_id: str, account_id: str) -> project_account.ProjectAccount | None:
        result = self._dynamodb_client.get_item(
            TableName=self._table_name,
            Key={
                "PK": f"{dynamo_entity_config.DBPrefix.PROJECT.value}#{project_id}",
                "SK": f"{dynamo_entity_config.DBPrefix.ACCOUNT.value}#{account_id}",
            },
        )

        return project_account.ProjectAccount.model_validate(result["Item"]) if "Item" in result else None

    def get_project_by_id(self, id: str) -> Optional[project.Project]:
        result = self._dynamodb_client.get_item(
            TableName=self._table_name,
            Key={
                "PK": f"{dynamo_entity_config.DBPrefix.PROJECT.value}#{id}",
                "SK": f"{dynamo_entity_config.DBPrefix.PROJECT.value}#{id}",
            },
        )

        if "Item" in result:
            return project.Project.model_validate(result["Item"])

        return None

    def list_users_by_project(self, project_id: str) -> List[project_assignment.Assignment]:
        """Returns a list of all user assignments in a project."""
        assignments: List[project_assignment.Assignment] = []

        paginator = self._dynamodb_client.get_paginator("query")

        pages = paginator.paginate(
            TableName=self._table_name,
            KeyConditionExpression=Key("SK").eq(f"{dynamo_entity_config.DBPrefix.PROJECT.value}#{project_id}")
            & Key("PK").begins_with(f"{dynamo_entity_config.DBPrefix.USER.value}#"),
            IndexName=self._gsi_inverted_primary_key,
        )

        for page in pages:
            assignments.extend([project_assignment.Assignment.model_validate(item) for item in page.get("Items", [])])

        return assignments

    def list_users_by_project_paged(
        self, project_id: str, page: paging_utils.PageInfo
    ) -> paging_utils.PagedResponse[project_assignment.Assignment]:

        query_kwargs = {
            "TableName": self._table_name,
            "KeyConditionExpression": Key("SK").eq(f"{dynamo_entity_config.DBPrefix.PROJECT.value}#{project_id}")
            & Key("PK").begins_with(f"{dynamo_entity_config.DBPrefix.USER.value}#"),
            "IndexName": self._gsi_inverted_primary_key,
        }

        if page.page_size:
            query_kwargs["Limit"] = page.page_size

        if page.page_token:
            query_kwargs["ExclusiveStartKey"] = page.page_token

        result = self._dynamodb_client.query(**query_kwargs)

        return paging_utils.PagedResponse[project_assignment.Assignment](
            items=[project_assignment.Assignment.model_validate(item) for item in result["Items"]],
            page_token=result.get("LastEvaluatedKey", None),
        )

    def get_user_assignment(self, project_id: str, user_id: str) -> Optional[project_assignment.Assignment]:
        result = self._dynamodb_client.get_item(
            TableName=self._table_name,
            Key={
                "PK": f"{dynamo_entity_config.DBPrefix.USER.value}#{user_id}",
                "SK": f"{dynamo_entity_config.DBPrefix.PROJECT.value}#{project_id}",
            },
        )

        if "Item" in result:
            return project_assignment.Assignment.model_validate(result["Item"])

        return None

    def list_all_accounts(
        self,
        page_size: int,
        next_token: Any,
        account_type: Optional[str] = None,
        stage: Optional[str] = None,
        technology_id: Optional[str] = None,
    ) -> Tuple[List[project_account.ProjectAccount], Any]:
        """Returns a list of all projects in all projects with paging after 1 MB."""

        filter_expression = Key("SK").begins_with(f"{dynamo_entity_config.DBPrefix.ACCOUNT}#")
        param_filter_expr = self._build_filter_expression(account_type, stage, technology_id)

        if param_filter_expr:
            filter_expression = filter_expression & param_filter_expr

        if next_token:
            result = self._dynamodb_client.scan(
                TableName=self._table_name,
                Limit=page_size,
                ExclusiveStartKey=next_token,
                FilterExpression=filter_expression,  # type: ignore
            )
        else:
            result = self._dynamodb_client.scan(
                TableName=self._table_name,
                Limit=page_size,
                FilterExpression=filter_expression,  # type: ignore
            )
        project_accounts = [project_account.ProjectAccount.model_validate(item) for item in result["Items"]]

        if "LastEvaluatedKey" in result:
            return project_accounts, result["LastEvaluatedKey"]
        else:
            return project_accounts, None

    def get_user(self, user_id: str) -> Optional[user.User]:
        query_result = self._dynamodb_client.get_item(
            TableName=self._table_name,
            Key={
                "PK": f"{dynamo_entity_config.DBPrefix.USER.value}#{user_id}",
                "SK": f"{dynamo_entity_config.DBPrefix.USER.value}#{user_id}",
            },
        )

        result = user.User.model_validate(query_result["Item"])

        return result if result else None

    def get_all_users(
        self,
        page_size: int,
        next_token: Any,
    ) -> Tuple[List[user.User], Any]:
        """Returns a list of all users with paging after 1 MB."""

        if next_token:
            result = self._dynamodb_client.query(
                TableName=self._table_name,
                Limit=page_size,
                KeyConditionExpression=Key(dynamodb_repo_config.ATTRIBUTE_NAME_ENTITY).eq(
                    dynamo_entity_config.DBPrefix.USER.value
                ),
                ExclusiveStartKey=next_token,
                IndexName=self._gsi_entities,
            )
        else:
            result = self._dynamodb_client.query(
                TableName=self._table_name,
                Limit=page_size,
                KeyConditionExpression=Key(dynamodb_repo_config.ATTRIBUTE_NAME_ENTITY).eq(
                    dynamo_entity_config.DBPrefix.USER.value
                ),
                IndexName=self._gsi_entities,
            )

        users = [user.User.model_validate(item) for item in result["Items"]]

        if "LastEvaluatedKey" in result:
            return users, result["LastEvaluatedKey"]
        else:
            return users, None

    @staticmethod
    def _build_filter_expression(
        account_type: Optional[str], stage: Optional[str], technology_id: Optional[str] = None
    ) -> Optional[ConditionBase]:
        condition_expression: Optional[ConditionBase] = None

        if account_type:
            acct_type_condition = Attr("accountType").eq(account_type)
            condition_expression = (
                condition_expression & acct_type_condition if condition_expression else acct_type_condition
            )

        if stage:
            stage_condition = Attr("stage").eq(stage)
            condition_expression = condition_expression & stage_condition if condition_expression else stage_condition

        if technology_id:
            tech_id_condition = Attr("technologyId").eq(technology_id)
            condition_expression = (
                condition_expression & tech_id_condition if condition_expression else tech_id_condition
            )

        return condition_expression


class DynamoDBTechnologiesQueryService(technologies_query_service.TechnologiesQueryService):
    def __init__(self, table_name: str, dynamodb_client: client.DynamoDBClient):
        super().__init__()
        self._table_name = table_name
        self._dynamodb_client = dynamodb_client

    def list_technologies(self, project_id: str, page_size: int) -> List[technology.Technology]:
        technologies: list = []
        query_kwargs = {
            "TableName": self._table_name,
            "KeyConditionExpression": Key("PK").eq(f"{dynamo_entity_config.DBPrefix.PROJECT}#{project_id}")
            & Key("SK").begins_with(f"{dynamo_entity_config.DBPrefix.TECHNOLOGY}#"),
        }

        if page_size > 0:
            query_kwargs[DDB_PAGE_SIZE_PARAM] = page_size

        while DDB_RESPONSE_PAGING_PARAM in (result := self._dynamodb_client.query(**query_kwargs)):
            query_kwargs[DDB_REQUEST_PAGING_PARAM] = result.get(DDB_RESPONSE_PAGING_PARAM)
            technologies.extend(result.get("Items", []))

        technologies.extend(result.get("Items", []))

        results = [technology.Technology.model_validate(item) for item in technologies]

        return results


class DynamoDBEnrolmentQueryService(enrolment_query_service.EnrolmentQueryService):
    def __init__(self, table_name: str, dynamodb_client: client.DynamoDBClient, gsi_qpk: str, gsi_qsk: str) -> None:
        super().__init__()
        self._table_name = table_name
        self._dynamodb_client = dynamodb_client
        self._gsi_qpk = gsi_qpk
        self._gsi_qsk = gsi_qsk

    def get_enrolment_for_user(self, user_id: str, project_id: str) -> Optional[enrolment.Enrolment]:
        result = self._dynamodb_client.query(
            TableName=self._table_name,
            KeyConditionExpression=Key("PK").eq(f"{dynamo_entity_config.DBPrefix.PROJECT}#{project_id}")
            & Key("SK").begins_with(f"{dynamo_entity_config.DBPrefix.ENROLMENT}#"),
            FilterExpression=Attr("userId").eq(f"{user_id}"),
            Limit=1,
        )

        results = [enrolment.Enrolment.model_validate(item) for item in result["Items"]]

        return results.pop() if results else None

    def get_enrolment_by_id(self, enrolment_id: str, project_id: str) -> Optional[enrolment.Enrolment]:
        query_result = self._dynamodb_client.get_item(
            TableName=self._table_name,
            Key={
                "PK": f"{dynamo_entity_config.DBPrefix.PROJECT}#{project_id}",
                "SK": f"{dynamo_entity_config.DBPrefix.ENROLMENT}#{enrolment_id}",
            },
        )

        result = enrolment.Enrolment.model_validate(query_result["Item"])

        return result if result else None

    def list_enrolments_by_project(
        self, project_id: str, page_size: int, next_token: Any, status: Optional[str] = None
    ) -> Tuple[List[enrolment.Enrolment], Any]:
        if not status:
            return self._list_enrolments_by_project(project_id, page_size, next_token)

        return self._list_enrolments_by_project_and_status(project_id, page_size, next_token, status)

    def _list_enrolments_by_project(self, project_id: str, page_size: int, next_token: Any):
        if next_token:
            result = self._dynamodb_client.query(
                TableName=self._table_name,
                KeyConditionExpression=Key("PK").eq(f"{dynamo_entity_config.DBPrefix.PROJECT}#{project_id}")
                & Key("SK").begins_with(f"{dynamo_entity_config.DBPrefix.ENROLMENT}#"),  # type: ignore
                Limit=page_size,
                ExclusiveStartKey=next_token,
            )
        else:
            result = self._dynamodb_client.query(
                TableName=self._table_name,
                KeyConditionExpression=Key("PK").eq(f"{dynamo_entity_config.DBPrefix.PROJECT}#{project_id}")
                & Key("SK").begins_with(f"{dynamo_entity_config.DBPrefix.ENROLMENT}#"),  # type: ignore
                Limit=page_size,
            )

        results = [enrolment.Enrolment.model_validate(item) for item in result["Items"]]

        if "LastEvaluatedKey" in result:
            return results, result["LastEvaluatedKey"]
        else:
            return results, None

    def _list_enrolments_by_project_and_status(self, project_id: str, page_size: int, next_token: Any, status: str):
        if next_token:
            result = self._dynamodb_client.query(
                TableName=self._table_name,
                KeyConditionExpression=Key("PK").eq(f"{dynamo_entity_config.DBPrefix.PROJECT}#{project_id}")
                & Key("QSK").begins_with(f"{dynamo_entity_config.DBPrefix.ENROLMENT}#{status}#"),  # type: ignore
                Limit=page_size,
                ExclusiveStartKey=next_token,
                IndexName=self._gsi_qsk,
            )
        else:
            result = self._dynamodb_client.query(
                TableName=self._table_name,
                KeyConditionExpression=Key("PK").eq(f"{dynamo_entity_config.DBPrefix.PROJECT}#{project_id}")
                & Key("QSK").begins_with(f"{dynamo_entity_config.DBPrefix.ENROLMENT}#{status}#"),  # type: ignore
                Limit=page_size,
                IndexName=self._gsi_qsk,
            )

        results = [enrolment.Enrolment.model_validate(item) for item in result["Items"]]

        if "LastEvaluatedKey" in result:
            return results, result["LastEvaluatedKey"]
        else:
            return results, None

    def list_enrolments_by_user(
        self,
        user_id: str,
        page_size: int,
        next_token: Any,
        status: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Tuple[List[enrolment.Enrolment], Any]:
        filter_expression = self._build_filter_expression(status, project_id)

        if next_token:
            result = self._dynamodb_client.query(
                TableName=self._table_name,
                KeyConditionExpression=Key("QPK").eq(f"{dynamo_entity_config.DBPrefix.USER}#{user_id}")
                & Key("SK").begins_with(f"{dynamo_entity_config.DBPrefix.ENROLMENT}#"),  # type: ignore
                Limit=page_size,
                ExclusiveStartKey=next_token,
                IndexName=self._gsi_qpk,
                FilterExpression=filter_expression,
            )
        else:
            result = self._dynamodb_client.query(
                TableName=self._table_name,
                KeyConditionExpression=Key("QPK").eq(f"{dynamo_entity_config.DBPrefix.USER}#{user_id}")
                & Key("SK").begins_with(f"{dynamo_entity_config.DBPrefix.ENROLMENT}#"),  # type: ignore
                Limit=page_size,
                IndexName=self._gsi_qpk,
                FilterExpression=filter_expression,
            )

        results = [enrolment.Enrolment.model_validate(item) for item in result["Items"]]

        if "LastEvaluatedKey" in result:
            return results, result["LastEvaluatedKey"]
        else:
            return results, None

    @staticmethod
    def _build_filter_expression(status: Optional[str] = None, project_id: Optional[str] = None) -> str:
        condition_expression: Optional[ConditionBase] = None

        if status:
            status_condition = Attr("status").eq(status)
            condition_expression = condition_expression & status_condition if condition_expression else status_condition
        if project_id:
            project_id_condition = Attr("projectId").eq(project_id)
            condition_expression = (
                condition_expression & project_id_condition if condition_expression else project_id_condition
            )

        return condition_expression if condition_expression else ""  # type: ignore
