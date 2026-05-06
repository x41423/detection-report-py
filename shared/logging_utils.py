from __future__ import annotations

import logging
from pathlib import Path

from shared.project_paths import ProjectPaths, get_project_paths


LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"


def configure_application_logging(
    log_name: str,
    *,
    include_stream: bool = False,
    level: int = logging.INFO,
    force: bool = True,
    paths: ProjectPaths | None = None,
) -> Path:
    project_paths = paths or get_project_paths()
    log_path = project_paths.log_file(log_name)
    handlers: list[logging.Handler] = []
    if include_stream:
        handlers.append(logging.StreamHandler())
    handlers.append(logging.FileHandler(log_path, encoding="utf-8"))
    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        handlers=handlers,
        force=force,
    )
    return log_path
