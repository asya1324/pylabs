"""Environment and YAML configuration loading."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from task_manager.enums import Priority, TaskStatus
from task_manager.exceptions import ConfigurationError


@dataclass(frozen=True, slots=True)
class AppSettings:
    """Application settings with safe development defaults."""

    database_url: str = "sqlite:///./data/task_manager.db"
    app_env: str = "development"
    log_level: str = "INFO"
    tasks_source_url: str | None = None
    database_auto_create: bool = True
    config_path: Path | None = None

    @classmethod
    def from_env(cls) -> "AppSettings":
        """Create settings from environment variables."""
        return cls(
            database_url=os.getenv("DATABASE_URL", "sqlite:///./data/task_manager.db"),
            app_env=os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            tasks_source_url=os.getenv("TASKS_SOURCE_URL") or None,
            database_auto_create=os.getenv("DATABASE_AUTO_CREATE", "true").lower() in {"1", "true", "yes"},
            config_path=Path(os.getenv("TASK_MANAGER_CONFIG", "config.yaml")),
        )


@dataclass(frozen=True, slots=True)
class TaskValidationConfig:
    """Allowed task values used by strict/tolerant CSV import."""

    allowed_priorities: frozenset[str]
    allowed_statuses: frozenset[str]

    def validate(self) -> None:
        if not self.allowed_priorities or not self.allowed_statuses:
            raise ConfigurationError("Allowed priorities and statuses must not be empty")
        if not self.allowed_priorities.issubset({item.label for item in Priority}):
            raise ConfigurationError("Configuration contains unsupported priorities")
        if not self.allowed_statuses.issubset({item.value for item in TaskStatus}):
            raise ConfigurationError("Configuration contains unsupported statuses")


def load_task_validation_config(path: Path | str | None = None) -> TaskValidationConfig:
    """Load allowed priorities/statuses from YAML."""
    config_path = Path(path) if path else Path(__file__).with_name("config.yaml")
    try:
        with config_path.open("r", encoding="utf-8") as stream:
            raw: Any = yaml.safe_load(stream) or {}
    except OSError as exc:
        raise ConfigurationError(f"Cannot read configuration: {config_path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigurationError("Invalid YAML configuration") from exc

    if not isinstance(raw, dict):
        raise ConfigurationError("Configuration root must be a mapping")

    priorities = raw.get("allowed_priorities", [])
    statuses = raw.get("allowed_statuses", [])
    if not isinstance(priorities, list) or not isinstance(statuses, list):
        raise ConfigurationError("allowed_priorities and allowed_statuses must be lists")

    config = TaskValidationConfig(
        allowed_priorities=frozenset(str(value).strip().lower() for value in priorities),
        allowed_statuses=frozenset(str(value).strip().lower() for value in statuses),
    )
    config.validate()
    return config
