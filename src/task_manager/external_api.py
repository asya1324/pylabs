"""Async HTTPX client demonstrating bounded concurrent task loading (Lab 8)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence

import httpx

logger = logging.getLogger(__name__)


class HttpxTaskSource:
    """Fetch `/users/{id}/tasks` concurrently with limits, timeouts and retries."""

    def __init__(
        self,
        base_url: str,
        *,
        concurrency: int = 5,
        timeout_seconds: float = 5.0,
        retries: int = 2,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if concurrency < 1 or timeout_seconds <= 0 or retries < 0:
            raise ValueError("Invalid concurrency, timeout or retry configuration")
        self.base_url = base_url.rstrip("/")
        self.concurrency = concurrency
        self.timeout = httpx.Timeout(timeout_seconds)
        self.retries = retries
        self.transport = transport

    async def fetch_for_users(self, user_ids: Sequence[int]) -> dict[int, list[dict[str, object]]]:
        """Load all user task lists using asyncio Tasks and gather."""
        semaphore = asyncio.Semaphore(self.concurrency)
        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
            async def fetch_one(user_id: int) -> tuple[int, list[dict[str, object]]]:
                async with semaphore:
                    last_error: Exception | None = None
                    for attempt in range(self.retries + 1):
                        try:
                            response = await asyncio.wait_for(
                                client.get(f"{self.base_url}/users/{user_id}/tasks"),
                                timeout=self.timeout.read or 5.0,
                            )
                            response.raise_for_status()
                            payload = response.json()
                            if not isinstance(payload, list):
                                raise ValueError("Remote task endpoint must return a JSON list")
                            records = [item for item in payload if isinstance(item, dict)]
                            return user_id, records
                        except (httpx.HTTPError, TimeoutError, ValueError) as exc:
                            last_error = exc
                            logger.warning(
                                "Task source request for user %s failed (attempt %s/%s)",
                                user_id,
                                attempt + 1,
                                self.retries + 1,
                            )
                            if attempt < self.retries:
                                await asyncio.sleep(0.1 * (attempt + 1))
                    assert last_error is not None
                    raise RuntimeError(f"Could not load tasks for user {user_id}") from last_error

            tasks = [asyncio.create_task(fetch_one(user_id)) for user_id in user_ids]
            results = await asyncio.gather(*tasks)
        return {user_id: records for user_id, records in results}
