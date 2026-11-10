from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

from task_manager.protocols import AsyncTaskSource
from task_manager.services import AsyncTaskWorkflowService


def test_async_task_repository_mock_workflow() -> None:
    async def run() -> None:
        source = AsyncMock(spec=AsyncTaskSource)
        source.fetch_for_users.return_value = {
            1: [{"id": 10, "title": "First"}],
            2: [{"id": 20, "title": "Second"}],
        }
        workflow = AsyncTaskWorkflowService(source)
        result = await workflow.collect_for_users([1, 2])
        assert result[1][0]["title"] == "First"
        source.fetch_for_users.assert_awaited_once_with([1, 2])

    asyncio.run(run())


def test_async_task_workflow_propagates_failure() -> None:
    async def run() -> None:
        source = AsyncMock(spec=AsyncTaskSource)
        source.fetch_for_users.side_effect = TimeoutError("remote timeout")
        workflow = AsyncTaskWorkflowService(source)
        try:
            await workflow.collect_for_users([1])
        except TimeoutError as exc:
            assert "timeout" in str(exc)
        else:
            raise AssertionError("Expected TimeoutError")

    asyncio.run(run())


def test_httpx_task_source_uses_async_concurrency_and_retries() -> None:
    import httpx
    from task_manager.external_api import HttpxTaskSource

    attempts: dict[int, int] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        user_id = int(request.url.path.split("/")[-2])
        attempts[user_id] = attempts.get(user_id, 0) + 1
        if user_id == 2 and attempts[user_id] == 1:
            return httpx.Response(503, json={"detail": "temporary"})
        return httpx.Response(200, json=[{"id": user_id * 10, "title": f"Task {user_id}"}])

    async def run() -> None:
        transport = httpx.MockTransport(handler)
        source = HttpxTaskSource(
            "https://tasks.example.test",
            concurrency=2,
            timeout_seconds=1,
            retries=1,
            transport=transport,
        )
        result = await source.fetch_for_users([1, 2, 3])
        assert result[1][0]["id"] == 10
        assert result[2][0]["id"] == 20
        assert attempts[2] == 2

    asyncio.run(run())


def test_httpx_task_source_rejects_invalid_concurrency() -> None:
    import pytest
    from task_manager.external_api import HttpxTaskSource

    with pytest.raises(ValueError):
        HttpxTaskSource("https://tasks.example.test", concurrency=0)
