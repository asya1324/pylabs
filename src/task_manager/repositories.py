"""SQLAlchemy repositories implementing the domain persistence contracts."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from task_manager.db_models import TaskRecord, UserRecord
from task_manager.domain import Task, User
from task_manager.enums import Priority, TaskStatus
from task_manager.exceptions import TaskNotFoundError, TaskValidationError, UserNotFoundError

EntityT = TypeVar("EntityT")


class InMemoryIndex(Generic[EntityT]):
    """Small generic dictionary-backed index with expected O(1) lookup."""

    def __init__(self) -> None:
        self._items: dict[int, EntityT] = {}

    def add(self, key: int, value: EntityT) -> None:
        self._items[key] = value

    def get(self, key: int) -> EntityT | None:
        return self._items.get(key)


class SQLAlchemyTaskRepository:
    """Task CRUD, filtering, aggregates and transactional bulk operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _to_domain(record: TaskRecord) -> Task:
        created_at = record.created_at
        if created_at.tzinfo is None:
            from datetime import timezone

            created_at = created_at.replace(tzinfo=timezone.utc)
        return Task(
            id=record.id,
            title=record.title,
            description=record.description,
            priority=Priority(record.priority),
            status=TaskStatus(record.status),
            assigned_to=record.assigned_to,
            deadline=record.deadline,
            created_at=created_at,
        )

    @staticmethod
    def _apply(record: TaskRecord, task: Task) -> None:
        record.title = task.title
        record.description = task.description
        record.priority = task.priority.value
        record.status = task.status.value
        record.assigned_to = task.assigned_to
        record.deadline = task.deadline

    def create(self, task: Task) -> Task:
        record = TaskRecord(
            title=task.title,
            description=task.description,
            priority=task.priority.value,
            status=task.status.value,
            assigned_to=task.assigned_to,
            deadline=task.deadline,
            created_at=task.created_at,
        )
        self.session.add(record)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise TaskValidationError("Task references an unknown user") from exc
        self.session.refresh(record)
        return self._to_domain(record)

    def get(self, task_id: int) -> Task | None:
        record = self.session.get(TaskRecord, task_id)
        return self._to_domain(record) if record else None

    def list_tasks(
        self,
        *,
        status: TaskStatus | None = None,
        priority: str | None = None,
        user_id: int | None = None,
        search: str | None = None,
    ) -> list[Task]:
        statement = select(TaskRecord)
        if status is not None:
            statement = statement.where(TaskRecord.status == status.value)
        if priority is not None:
            statement = statement.where(TaskRecord.priority == priority)
        if user_id is not None:
            statement = statement.where(TaskRecord.assigned_to == user_id)
        if search:
            needle = f"%{search.strip()}%"
            statement = statement.where(TaskRecord.title.ilike(needle) | TaskRecord.description.ilike(needle))
        statement = statement.order_by(TaskRecord.id)
        return [self._to_domain(record) for record in self.session.scalars(statement).all()]

    def update(self, task: Task) -> Task:
        if task.id is None:
            raise TaskValidationError("Cannot update a task without an ID")
        record = self.session.get(TaskRecord, task.id)
        if record is None:
            raise TaskNotFoundError(f"Task {task.id} was not found")
        self._apply(record, task)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise TaskValidationError("Task references an unknown user") from exc
        self.session.refresh(record)
        return self._to_domain(record)

    def delete(self, task_id: int) -> bool:
        record = self.session.get(TaskRecord, task_id)
        if record is None:
            return False
        self.session.delete(record)
        self.session.commit()
        return True

    def overdue(self, on_date: date | None = None) -> list[Task]:
        today = on_date or date.today()
        statement = (
            select(TaskRecord)
            .where(TaskRecord.deadline < today)
            .where(TaskRecord.status.not_in([TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value]))
            .order_by(TaskRecord.deadline)
        )
        return [self._to_domain(record) for record in self.session.scalars(statement).all()]

    def bulk_update_statuses(self, changes: Iterable[tuple[int, TaskStatus]]) -> int:
        """Apply all status changes atomically; rollback the whole batch on failure."""
        try:
            changed = 0
            for task_id, status in changes:
                record = self.session.get(TaskRecord, task_id)
                if record is None:
                    raise TaskNotFoundError(f"Task {task_id} was not found")
                record.status = status.value
                changed += 1
            self.session.commit()
            return changed
        except Exception:
            self.session.rollback()
            raise

    def bulk_reassign(self, assignments: Iterable[tuple[int, int | None]]) -> int:
        """Reassign multiple tasks atomically."""
        try:
            changed = 0
            for task_id, user_id in assignments:
                record = self.session.get(TaskRecord, task_id)
                if record is None:
                    raise TaskNotFoundError(f"Task {task_id} was not found")
                if user_id is not None and self.session.get(UserRecord, user_id) is None:
                    raise UserNotFoundError(f"User {user_id} was not found")
                record.assigned_to = user_id
                changed += 1
            self.session.commit()
            return changed
        except Exception:
            self.session.rollback()
            raise

    def status_counts(self) -> dict[str, int]:
        tasks = self.list_tasks()
        return {status.value: sum(task.status is status for task in tasks) for status in TaskStatus}


class SQLAlchemyUserRepository:
    """User CRUD and task-assignee access."""

    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _to_domain(record: UserRecord) -> User:
        return User(id=record.id, name=record.name, email=record.email)

    def create(self, user: User) -> User:
        record = UserRecord(name=user.name, email=user.email)
        self.session.add(record)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise TaskValidationError("A user with this email already exists") from exc
        self.session.refresh(record)
        return self._to_domain(record)

    def get(self, user_id: int) -> User | None:
        record = self.session.get(UserRecord, user_id)
        return self._to_domain(record) if record else None

    def list_users(self) -> list[User]:
        records = self.session.scalars(select(UserRecord).order_by(UserRecord.id)).all()
        return [self._to_domain(record) for record in records]

    def tasks_for_user(self, user_id: int, task_repository: SQLAlchemyTaskRepository) -> list[Task]:
        if self.get(user_id) is None:
            raise UserNotFoundError(f"User {user_id} was not found")
        return task_repository.list_tasks(user_id=user_id)
