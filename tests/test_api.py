from __future__ import annotations

from datetime import date, timedelta
from dataclasses import replace

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import task_manager.api as api_module
from task_manager.api import app
from task_manager.database import get_session


def test_rest_api_full_task_workflow(db_session: Session, monkeypatch) -> None:
    monkeypatch.setattr(api_module, "settings", replace(api_module.settings, database_auto_create=False))

    def override_session():
        yield db_session

    app.dependency_overrides[get_session] = override_session
    try:
        with TestClient(app) as client:
            assert client.get("/health").json()["status"] == "ok"
            user_response = client.post(
                "/users",
                json={"name": "Grace Hopper", "email": "grace@example.com"},
            )
            assert user_response.status_code == 201
            user_id = user_response.json()["id"]

            created = client.post(
                "/tasks",
                json={
                    "title": "Prepare release",
                    "description": "Write release notes",
                    "priority": "high",
                    "assigned_to": user_id,
                    "deadline": (date.today() - timedelta(days=1)).isoformat(),
                },
            )
            assert created.status_code == 201
            task_id = created.json()["id"]
            assert created.json()["priority"] == "high"

            filtered = client.get("/tasks", params={"status": "todo", "priority": "high"})
            assert len(filtered.json()) == 1
            assert client.get(f"/users/{user_id}/tasks").json()[0]["id"] == task_id
            assert client.get("/tasks/overdue").json()[0]["id"] == task_id

            patched = client.patch(f"/tasks/{task_id}", json={"status": "completed", "priority": "critical"})
            assert patched.status_code == 200
            assert patched.json()["status"] == "completed"
            assert client.get("/tasks/overdue").json() == []
            stats = client.get("/statistics").json()
            assert stats["total"] == 1
            assert stats["completed"] == 1

            replaced = client.put(
                f"/tasks/{task_id}",
                json={
                    "title": "Release final",
                    "description": "Final notes",
                    "priority": "medium",
                    "status": "in_progress",
                },
            )
            assert replaced.status_code == 200
            assert replaced.json()["title"] == "Release final"
            assert client.get("/tasks/99999").status_code == 404
            assert client.delete(f"/tasks/{task_id}").status_code == 204
    finally:
        app.dependency_overrides.clear()


def test_invalid_transition_returns_conflict(db_session: Session, monkeypatch) -> None:
    monkeypatch.setattr(api_module, "settings", replace(api_module.settings, database_auto_create=False))
    def override_session():
        yield db_session
    app.dependency_overrides[get_session] = override_session
    try:
        with TestClient(app) as client:
            created = client.post("/tasks", json={"title": "Cancel me", "priority": "low"}).json()
            task_id = created["id"]
            assert client.patch(f"/tasks/{task_id}", json={"status": "cancelled"}).status_code == 200
            response = client.patch(f"/tasks/{task_id}", json={"status": "todo"})
            assert response.status_code == 409
    finally:
        app.dependency_overrides.clear()
