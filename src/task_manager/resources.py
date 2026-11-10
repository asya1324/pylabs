"""Reusable context managers for safe filesystem resource handling."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from types import TracebackType
from typing import IO


class AtomicTextWriter:
    """Write text to a sibling temporary file and atomically replace target on success."""

    def __init__(self, destination: Path | str, encoding: str = "utf-8") -> None:
        self.destination = Path(destination)
        self.encoding = encoding
        self._temporary_path: Path | None = None
        self._stream: IO[str] | None = None

    def __enter__(self) -> IO[str]:
        self.destination.parent.mkdir(parents=True, exist_ok=True)
        handle = tempfile.NamedTemporaryFile(
            mode="w",
            encoding=self.encoding,
            dir=self.destination.parent,
            prefix=f".{self.destination.name}.",
            suffix=".tmp",
            delete=False,
        )
        self._temporary_path = Path(handle.name)
        self._stream = handle
        return handle

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        if self._stream is not None and not self._stream.closed:
            if exception_type is None:
                self._stream.flush()
                os.fsync(self._stream.fileno())
            self._stream.close()
        if self._temporary_path is not None:
            if exception_type is None:
                os.replace(self._temporary_path, self.destination)
            else:
                self._temporary_path.unlink(missing_ok=True)
        return False
