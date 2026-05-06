from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ProjectPaths:
    root: Path
    config_dir: Path
    config_file: Path
    legacy_root_config_file: Path
    data_dir: Path
    database_file: Path
    legacy_database_file: Path
    pesticide_data_dir: Path
    history_rates_file: Path
    legacy_history_rates_file: Path
    logs_dir: Path
    runtime_dir: Path

    @classmethod
    def for_root(cls, root: Path) -> "ProjectPaths":
        root = root.resolve()
        config_dir = root / "config"
        data_dir = root / "data"
        pesticide_data_dir = data_dir / "pesticide"
        logs_dir = root / "logs"
        runtime_dir = root / ".runtime"
        return cls(
            root=root,
            config_dir=config_dir,
            config_file=config_dir / "app.json",
            legacy_root_config_file=root / "config.json",
            data_dir=data_dir,
            database_file=data_dir / "app.db",
            legacy_database_file=root / "app" / "data" / "app.db",
            pesticide_data_dir=pesticide_data_dir,
            history_rates_file=pesticide_data_dir / "history_rates.json",
            legacy_history_rates_file=root / "history_rates.json",
            logs_dir=logs_dir,
            runtime_dir=runtime_dir,
        )

    def ensure_logs_dir(self) -> Path:
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        return self.logs_dir

    def log_file(self, name: str) -> Path:
        return self.ensure_logs_dir() / name


_PROJECT_PATHS = ProjectPaths.for_root(Path(__file__).resolve().parent.parent)


def get_project_paths() -> ProjectPaths:
    return _PROJECT_PATHS
