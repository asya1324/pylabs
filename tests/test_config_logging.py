from __future__ import annotations

from pathlib import Path

import pytest

from task_manager.config import load_task_validation_config
from task_manager.exceptions import ConfigurationError
from task_manager.logging_config import configure_logging


def test_invalid_yaml_configuration_is_reported(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("allowed_priorities: [high\n", encoding="utf-8")
    with pytest.raises(ConfigurationError):
        load_task_validation_config(bad)


def test_invalid_allowed_values_are_rejected(tmp_path: Path) -> None:
    bad = tmp_path / "bad-values.yaml"
    bad.write_text(
        "allowed_priorities: [urgent]\nallowed_statuses: [todo]\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigurationError):
        load_task_validation_config(bad)


def test_logging_configuration_creates_log_file(tmp_path: Path) -> None:
    target = tmp_path / "logs" / "application.log"
    configure_logging("DEBUG", target)
    assert target.exists()
