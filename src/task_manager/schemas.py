"""Pydantic request/response schemas for the REST API."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from task_manager.enums import Priority, TaskStatus


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=255)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    priority: Priority = Priority.MEDIUM
    status: TaskStatus = TaskStatus.TODO
    assigned_to: int | None = Field(default=None, ge=1)
    deadline: date | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    priority: Priority | None = None
    status: TaskStatus | None = None
    assigned_to: int | None = Field(default=None, ge=1)
    deadline: date | None = None


class TaskReplace(BaseModel):
    """Complete replacement payload for PUT /tasks/{id}."""

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    priority: Priority = Priority.MEDIUM
    status: TaskStatus = TaskStatus.TODO
    assigned_to: int | None = Field(default=None, ge=1)
    deadline: date | None = None


class TaskRead(BaseModel):
    id: int
    title: str
    description: str
    priority: Priority
    status: TaskStatus
    assigned_to: int | None
    deadline: date | None
    created_at: datetime
    overdue: bool
