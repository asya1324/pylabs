"""FastAPI application exposing the task-management REST API."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from task_manager.config import AppSettings
from task_manager.database import create_tables, get_session
from task_manager.domain import Task
from task_manager.enums import Priority, TaskStatus
from task_manager.exceptions import (
    InvalidStatusTransitionError,
    TaskNotFoundError,
    TaskValidationError,
    UserNotFoundError,
)
from task_manager.external_api import HttpxTaskSource
from task_manager.repositories import SQLAlchemyTaskRepository, SQLAlchemyUserRepository
from task_manager.schemas import TaskCreate, TaskRead, TaskReplace, TaskUpdate, UserCreate, UserRead
from task_manager.services import AsyncTaskWorkflowService, TaskService

logger = logging.getLogger(__name__)
settings = AppSettings.from_env()


def get_task_service(session: Annotated[Session, Depends(get_session)]) -> TaskService:
    task_repository = SQLAlchemyTaskRepository(session)
    user_repository = SQLAlchemyUserRepository(session)
    return TaskService(task_repository, user_repository)


def _task_read(task: Task) -> TaskRead:
    return TaskRead(
        id=task.id or 0,
        title=task.title,
        description=task.description,
        priority=task.priority,
        status=task.status,
        assigned_to=task.assigned_to,
        deadline=task.deadline,
        created_at=task.created_at,
        overdue=task.is_overdue,
    )


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(_application: FastAPI) -> AsyncIterator[None]:
        if settings.database_auto_create:
            create_tables()
        yield

    application = FastAPI(
        title="Task Manager API",
        version="1.0.0",
        description="REST API for task creation, assignment, filtering and analytics (variant 14).",
        lifespan=lifespan,
    )

    @application.exception_handler(TaskNotFoundError)
    async def task_not_found_handler(_request: object, exc: TaskNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @application.exception_handler(UserNotFoundError)
    async def user_not_found_handler(_request: object, exc: UserNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @application.exception_handler(InvalidStatusTransitionError)
    async def invalid_transition_handler(_request: object, exc: InvalidStatusTransitionError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @application.exception_handler(TaskValidationError)
    async def validation_handler(_request: object, exc: TaskValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @application.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "task-manager"}

    @application.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED, tags=["users"])
    def create_user(
        payload: UserCreate,
        service: Annotated[TaskService, Depends(get_task_service)],
    ) -> UserRead:
        user = service.create_user(payload.name, payload.email)
        return UserRead(id=user.id or 0, name=user.name, email=user.email)

    @application.get("/users", response_model=list[UserRead], tags=["users"])
    def list_users(session: Annotated[Session, Depends(get_session)]) -> list[UserRead]:
        users = SQLAlchemyUserRepository(session).list_users()
        return [UserRead(id=user.id or 0, name=user.name, email=user.email) for user in users]

    @application.get("/users/{user_id}/tasks", response_model=list[TaskRead], tags=["users"])
    def tasks_for_user(
        user_id: int,
        service: Annotated[TaskService, Depends(get_task_service)],
    ) -> list[TaskRead]:
        if service.user_repository.get(user_id) is None:
            raise UserNotFoundError(f"User {user_id} was not found")
        return [_task_read(task) for task in service.list_tasks(user_id=user_id)]

    @application.post("/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED, tags=["tasks"])
    def create_task(
        payload: TaskCreate,
        service: Annotated[TaskService, Depends(get_task_service)],
    ) -> TaskRead:
        task = service.create_task(**payload.model_dump())
        return _task_read(task)

    @application.get("/tasks/overdue", response_model=list[TaskRead], tags=["tasks"])
    def overdue_tasks(
        service: Annotated[TaskService, Depends(get_task_service)],
    ) -> list[TaskRead]:
        return [_task_read(task) for task in service.overdue_tasks()]

    @application.get("/tasks/statistics", tags=["statistics"])
    @application.get("/statistics", tags=["statistics"])
    def statistics(
        service: Annotated[TaskService, Depends(get_task_service)],
    ) -> dict[str, object]:
        return service.dashboard_statistics()

    @application.get("/tasks", response_model=list[TaskRead], tags=["tasks"])
    def list_tasks(
        service: Annotated[TaskService, Depends(get_task_service)],
        status_filter: Annotated[TaskStatus | None, Query(alias="status")] = None,
        priority_filter: Annotated[Priority | None, Query(alias="priority")] = None,
        user_id: int | None = Query(default=None, ge=1),
        q: str | None = Query(default=None, max_length=200),
    ) -> list[TaskRead]:
        tasks = service.list_tasks(
            status=status_filter,
            priority=priority_filter,
            user_id=user_id,
            search=q,
        )
        return [_task_read(task) for task in tasks]

    @application.get("/tasks/{task_id}", response_model=TaskRead, tags=["tasks"])
    def get_task(
        task_id: int,
        service: Annotated[TaskService, Depends(get_task_service)],
    ) -> TaskRead:
        return _task_read(service.get_task(task_id))

    @application.put("/tasks/{task_id}", response_model=TaskRead, tags=["tasks"])
    def replace_task(
        task_id: int,
        payload: TaskReplace,
        service: Annotated[TaskService, Depends(get_task_service)],
    ) -> TaskRead:
        task = service.update_task(task_id, **payload.model_dump())
        return _task_read(task)

    @application.patch("/tasks/{task_id}", response_model=TaskRead, tags=["tasks"])
    def update_task(
        task_id: int,
        payload: TaskUpdate,
        service: Annotated[TaskService, Depends(get_task_service)],
    ) -> TaskRead:
        task = service.update_task(task_id, **payload.model_dump(exclude_unset=True))
        return _task_read(task)

    @application.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["tasks"])
    def delete_task(
        task_id: int,
        service: Annotated[TaskService, Depends(get_task_service)],
    ) -> Response:
        service.delete_task(task_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @application.get("/integrations/remote-users/tasks", tags=["integrations"])
    async def load_remote_user_tasks(
        user_ids: Annotated[list[int], Query(min_length=1)],
    ) -> dict[int, list[dict[str, object]]]:
        if not settings.tasks_source_url:
            raise HTTPException(status_code=503, detail="TASKS_SOURCE_URL is not configured")
        workflow = AsyncTaskWorkflowService(HttpxTaskSource(settings.tasks_source_url))
        return await workflow.collect_for_users(user_ids)

    return application


app = create_app()
