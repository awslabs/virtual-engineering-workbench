import heapq
import typing

from app.projects.domain.commands.users import unassign_user_command as command
from app.projects.domain.events.users import user_unassigned
from app.projects.domain.exceptions import domain_exception
from app.projects.domain.model import enrolment, project_assignment
from app.projects.domain.ports import enrolment_query_service, projects_query_service
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work

MAX_TRANSACTION_COUNT = 100


def handle_unassign_user_command(
    cmd: command.UnAssignUserCommand,
    uow: unit_of_work.UnitOfWork,
    projects_qry_service: projects_query_service.ProjectsQueryService,
    enrolment_qry_service: enrolment_query_service.EnrolmentQueryService,
    msg_bus: message_bus.MessageBus,
):
    project = projects_qry_service.get_project_by_id(cmd.project_id.value)
    if not project:
        raise domain_exception.DomainException(
            f"Failed to load project. Project for given ID {cmd.project_id.value} does not exist."
        )

    unique_user_ids = {user_id.value for user_id in cmd.user_ids}

    user_enrolments: dict[str, enrolment.Enrolment] = {}
    user_enrolments_hp = []
    for user_id in unique_user_ids:
        user_enrolments[user_id] = __fetch_all_pending_enrolments_for_user(
            user_id, cmd.project_id.value, 100, enrolment_qry_service
        )
        user_enrolments_hp.append(
            (
                len(user_enrolments[user_id]),
                user_id,
            )
        )

    heapq.heapify(user_enrolments_hp)

    for transaction in __get_transaction_page(user_enrolments_hp, user_enrolments, cmd.project_id.value):
        with uow:
            for entity, pk in transaction:
                uow.get_repository(type(pk), entity).remove(pk)
            uow.commit()

    for user in unique_user_ids:
        msg_bus.publish(user_unassigned.UserUnAssigned(userId=user, projectId=cmd.project_id.value))


def __can_fit_new_transaction(total_enrolments: int, transaction: list):
    return total_enrolments + 1 <= MAX_TRANSACTION_COUNT - len(transaction)


def __is_transaction_empty(transaction: list) -> bool:
    return len(transaction) == 0


def __flush_transaction(total_enrolments: int, transaction: list):
    return not __can_fit_new_transaction(total_enrolments, transaction) and not __is_transaction_empty(transaction)


def __get_transaction_page(
    user_enrolments_hp: list,
    user_enrolments: dict[str, list[enrolment.Enrolment]],
    project_id: str,
) -> typing.Iterable[list[tuple[type, unit_of_work.PrimaryKey]]]:

    transaction: list[tuple[type, unit_of_work.PrimaryKey]] = []

    while user_enrolments_hp:
        total_enrolments, user_id = heapq.heappop(user_enrolments_hp)

        if __flush_transaction(total_enrolments, transaction):
            yield transaction
            transaction = []

        if not __can_fit_new_transaction(total_enrolments, transaction):
            for chunk in range(0, total_enrolments, 99):
                for e in user_enrolments[user_id][chunk : chunk + 99]:
                    transaction.append(
                        (enrolment.Enrolment, enrolment.EnrolmentPrimaryKey(id=e.id, projectId=e.projectId))
                    )
                transaction.append(
                    (
                        project_assignment.Assignment,
                        project_assignment.AssignmentPrimaryKey(userId=user_id, projectId=project_id),
                    )
                )

                yield transaction
                transaction = []
        else:
            for e in user_enrolments[user_id]:
                transaction.append((enrolment.Enrolment, enrolment.EnrolmentPrimaryKey(id=e.id, projectId=e.projectId)))
            transaction.append(
                (
                    project_assignment.Assignment,
                    project_assignment.AssignmentPrimaryKey(userId=user_id, projectId=project_id),
                )
            )

    if transaction:
        yield transaction
        transaction = []


def __fetch_all_pending_enrolments_for_user(
    user_id: str,
    project_id: str,
    page_size: int,
    enrolment_qry_service: enrolment_query_service.EnrolmentQueryService,
) -> list[enrolment.Enrolment]:
    pending_enrolments, paging_token = enrolment_qry_service.list_enrolments_by_user(
        user_id=user_id,
        page_size=page_size,
        next_token=None,
        status=enrolment.EnrolmentStatus.Pending,
        project_id=project_id,
    )
    while paging_token:
        paged_pending_enrolments, paging_token = enrolment_qry_service.list_enrolments_by_user(
            user_id=user_id,
            page_size=page_size,
            next_token=paging_token,
            status=enrolment.EnrolmentStatus.Pending,
            project_id=project_id,
        )
        pending_enrolments.extend(paged_pending_enrolments)

    return pending_enrolments
