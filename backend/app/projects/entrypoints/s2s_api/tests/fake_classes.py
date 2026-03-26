import datetime
import random
import uuid
from typing import Any, List, Optional, Tuple

from app.projects.adapters.query_services import dynamodb_query_service
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
from app.projects.domain.value_objects.account_type_value_object import AccountTypeEnum
from app.shared.adapters.boto import paging_utils


class FakeProjectsQueryService(projects_query_service.ProjectsQueryService):
    def __init__(self):
        self.projects: list[project.Project] = self._gen_projects()
        pass

    def list_projects_by_user(
        self, user_id: str, page_size: int, next_token: Any
    ) -> Tuple[List[project.Project], Any, List[project_assignment.Assignment]]:
        projects, token = self.list_projects(page_size=page_size, next_token=next_token)
        return (
            projects,
            token,
            [
                project_assignment.Assignment(
                    userId="TID", projectId="PID", roles=[project_assignment.Role.PLATFORM_USER]
                )
            ],
        )

    def list_projects(
        self, page_size: int, next_token: Any, user_id: Optional[str] = None
    ) -> Tuple[List[project.Project], Any, List[project_assignment.Assignment]]:
        projects = self.projects
        if user_id:
            assignments = [
                project_assignment.Assignment(
                    userId=user_id,
                    projectId=projects[0].project_id,
                    roles=[project_assignment.Role.PLATFORM_USER],
                )
            ]
        else:
            assignments = []

        return projects, {"PK": str(uuid.uuid4()), "SK": str(uuid.uuid4())}, assignments

    def list_project_accounts(
        self,
        project_id: str,
        account_type: Optional[str] = None,
        stage: Optional[str] = None,
        technology_id: Optional[str] = None,
    ) -> List[project_account.ProjectAccount]:
        current_time = datetime.datetime.now(datetime.timezone.utc).isoformat()

        user_dev_account = project_account.ProjectAccount(
            awsAccountId="123456789012",
            accountType=dynamodb_query_service.AccountType.USER.value,
            accountName="User account",
            accountDescription="User account description",
            createDate=current_time,
            lastUpdateDate=current_time,
            accountStatus=project_account.ProjectAccountStatusEnum.Active,
            stage=project_account.ProjectAccountStageEnum.DEV,
            technologyId="techn-id",
            region="us-east-1",
        )

        toolchain_qa_account = project_account.ProjectAccount(
            awsAccountId="123456789012",
            accountType=dynamodb_query_service.AccountType.TOOLCHAIN.value,
            accountName="Toolchain account",
            accountDescription="Toolchain account description",
            createDate=current_time,
            lastUpdateDate=current_time,
            accountStatus=project_account.ProjectAccountStatusEnum.Active,
            stage=project_account.ProjectAccountStageEnum.QA,
            technologyId="techn-id",
            region=None,
        )

        project_accounts = [user_dev_account, toolchain_qa_account]

        if account_type and stage:
            return [p for p in project_accounts if p.accountType == account_type and p.stage == stage]
        if account_type:
            return [p for p in project_accounts if p.accountType == account_type]
        if stage:
            return [p for p in project_accounts if p.stage == stage]

        return project_accounts

    def list_project_accounts_by_aws_account(self, aws_account_id: str) -> List[project_account.ProjectAccount]:
        current_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return [
            project_account.ProjectAccount(
                awsAccountId=aws_account_id,
                accountType=dynamodb_query_service.AccountType.TOOLCHAIN.value,
                accountName="Toolchain account",
                accountDescription="Toolchain account description",
                createDate=current_time,
                lastUpdateDate=current_time,
                accountStatus="Active",
                stage="qa",
                region="us-east-1",
                technologyId="123",
            )
        ]

    def get_project_account_by_id(self, project_id: str, account_id: str) -> project_account.ProjectAccount | None:
        return None

    def get_project_by_id(self, id: str) -> Optional[project.Project]:
        projects = self.projects
        return next(filter(lambda p: p.projectId, projects))

    def list_users_by_project(self, project_id: str) -> List[project_assignment.Assignment]:
        return [
            project_assignment.Assignment(
                projectId="project-id", userId="T0000AA", roles=[project_assignment.Role.PLATFORM_USER]
            )
        ]

    def list_users_by_project_paged(
        self, project_id: str, page: paging_utils.PageInfo
    ) -> paging_utils.PagedResponse[project_assignment.Assignment]:
        return paging_utils.PagedResponse[project_assignment.Assignment](
            items=self.list_users_by_project(project_id=project_id)
        )

    def list_all_accounts(
        self,
        page_size: int,
        next_token: Any,
        account_type: Optional[str] = None,
        stage: Optional[str] = None,
        technology_id: Optional[str] = None,
    ) -> Tuple[List[project_account.ProjectAccount], Any]:
        accounts = []
        account_type_values = [
            AccountTypeEnum.TOOLCHAIN,
            AccountTypeEnum.USER,
        ]
        for i in range(5):
            k = random.randint(0, 1)
            current_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
            if account_type:
                new_account = project_account.ProjectAccount(
                    awsAccountId=f"112233445{i}",
                    accountType=AccountTypeEnum.USER,
                    accountName="Toolchain account",
                    accountDescription="Toolchain account description",
                    createDate=current_time,
                    lastUpdateDate=current_time,
                    accountStatus=project_account.ProjectAccountStatusEnum.Active,
                    stage=project_account.ProjectAccountStageEnum.DEV,
                    technologyId="techn-id",
                    region="us-east-1",
                )
            else:
                new_account = project_account.ProjectAccount(
                    awsAccountId=f"112233445{i}",
                    accountType=account_type_values[k],
                    accountName="Toolchain account",
                    accountDescription="Toolchain account description",
                    createDate=current_time,
                    lastUpdateDate=current_time,
                    accountStatus=project_account.ProjectAccountStatusEnum.Active,
                    stage=project_account.ProjectAccountStageEnum.DEV,
                    technologyId="techn-id",
                    region="us-east-1",
                )
            accounts.append(new_account)
        accounts = [project_account.ProjectAccount.parse_obj(item) for item in accounts]
        return accounts, {"PK": str(uuid.uuid4()), "SK": str(uuid.uuid4())}

    def get_user_assignment(self, project_id: str, user_id: str) -> project_assignment.Assignment:
        new_assignment = project_assignment.Assignment(
            projectId="123",
            userId="U0",
            roles=[project_assignment.Role.ADMIN.value, project_assignment.Role.PLATFORM_USER.value],
        )
        return new_assignment

    def _gen_projects(self) -> list[project.Project]:
        projects = []
        for i in range(5):
            current_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
            new_project = project.Project(
                projectId=f"P{i}",
                projectName="test-name",
                projectDescription="test-description",
                isActive=True,
                createDate=current_time,
                lastUpdateDate=current_time,
            )
            projects.append(new_project)
        return [project.Project.parse_obj(item) for item in projects]

    def get_accounts(self, account_id: str) -> List[project_account.ProjectAccount]:
        return []

    def get_user(self, user_id: str) -> Optional[user.User]:
        return user.User(
            userId="user-0",
            activeDirectoryGroups=[],
            activeDirectoryGroupStatus=user.UserADStatus.PENDING,
            userEmail="user-0@email.com",
        )

    def get_all_users(
        self,
        page_size: int,
        next_token: Any,
    ) -> Tuple[List[user.User], Any]:
        users = []
        for i in range(5):
            new_user = user.User(
                userId=f"user-{i}",
                activeDirectoryGroups=[],
                activeDirectoryGroupStatus=user.UserADStatus.PENDING,
                userEmail=f"user-{i}@email.com",
            )
            users.append(new_user)
        users = [user.User.parse_obj(item) for item in users]
        return users, {"PK": str(uuid.uuid4()), "SK": str(uuid.uuid4())}


class FakeTechnologiesQueryService(technologies_query_service.TechnologiesQueryService):
    def __init__(self):
        pass

    def list_technologies(self, project_id: str, page_size: int) -> List[technology.Technology]:
        techs = []
        for i in range(page_size):
            current_time = datetime.datetime.fromisoformat("2022-12-01T00:12:00+00:00")
            current_time_iso = current_time.isoformat()
            new_tech = technology.Technology(
                id=str(i),
                name="test-name",
                description="test-description",
                createDate=current_time_iso,
                lastUpdateDate=current_time_iso,
            )
            techs.append(new_tech)
        return techs


class FakeEnrolmentsQueryService(enrolment_query_service.EnrolmentQueryService):
    def __init__(self, enrolments: list[enrolment.Enrolment] = []):
        self.enrolments = enrolments

    def get_enrolment_for_user(self, user_id: str, project_id: str) -> Optional[enrolment.Enrolment]:
        enrolments = [*self.enrolments]
        return next(filter(lambda e: e.userId.upper() == user_id.upper(), enrolments), None)

    def get_enrolment_by_id(self, enrolment_id: str, project_id: str) -> Optional[enrolment.Enrolment]:
        enrolments = [*self.enrolments]
        return next(filter(lambda e: e.id == enrolment_id, enrolments), None)

    def list_enrolments_by_project(
        self, project_id: str, page_size: int, next_token: Any, status: Optional[str] = None
    ) -> Tuple[List[enrolment.Enrolment], Any]:
        enrolments = [*self.enrolments]
        return list(filter(lambda e: e.projectId == project_id, enrolments)), None

    def list_enrolments_by_user(
        self,
        user_id: str,
        page_size: int,
        next_token: Any,
        status: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Tuple[List[enrolment.Enrolment], Any]:
        enrolments = [*self.enrolments]
        return list(filter(lambda e: e.userId.upper() == user_id.upper(), enrolments)), None

    def update_enrolments_by_project(self, project_id: str, items_to_update: List[dict]) -> List[enrolment.Enrolment]:
        approved_enrolment = enrolment.Enrolment(projectId="P1", userId="U1", status="Approved")
        rejected_enrolment = enrolment.Enrolment(projectId="P1", userId="U1", status="Rejected")
        return [approved_enrolment, rejected_enrolment]
