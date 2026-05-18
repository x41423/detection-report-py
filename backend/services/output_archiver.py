import json
import logging
import shutil
from datetime import date, datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class OutputArchiver:
    """Archive generated pesticide detection reports into year/month/day structure."""

    def __init__(self, output_root: str):
        self.output_root = Path(output_root)

    def archive(self, workspace_dir: Path | str, target_date: date) -> dict:
        workspace_dir = Path(workspace_dir)
        year = str(target_date.year)
        month = f"{target_date.month:02d}"
        day = f"{target_date.day:02d}"

        archive_base = self.output_root / year / month / day
        archive_big = archive_base / "big"
        archive_small = archive_base / "small"
        archive_big.mkdir(parents=True, exist_ok=True)
        archive_small.mkdir(parents=True, exist_ok=True)

        counts = {"big": 0, "small": 0}

        for f in workspace_dir.glob("*.docx"):
            name = f.name
            if "农残检测记录表" in name:
                shutil.copy2(f, archive_big / name)
                counts["big"] += 1
            elif "单位农残记录表" in name:
                shutil.copy2(f, archive_small / name)
                counts["small"] += 1

        total = counts["big"] + counts["small"]
        logger.info(f"Archived {total} files to {archive_base}")

        self._update_index()
        return {
            "archived_count": total,
            "big_count": counts["big"],
            "small_count": counts["small"],
            "archive_path": str(archive_base),
        }

    def _update_index(self):
        index_path = self.output_root / "archive.json"
        index = {}
        if index_path.exists():
            try:
                with index_path.open("r", encoding="utf-8") as f:
                    index = json.load(f)
            except Exception:
                pass
        index["last_updated"] = datetime.now().isoformat()
        try:
            with index_path.open("w", encoding="utf-8") as f:
                json.dump(index, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to update archive index: {e}")

    def find_report(self, target_date: date, kind: str = "big") -> Path | None:
        year = str(target_date.year)
        month = f"{target_date.month:02d}"
        day = f"{target_date.day:02d}"
        archive_dir = self.output_root / year / month / day / kind
        if not archive_dir.is_dir():
            return None
        docs = list(archive_dir.glob("*.docx"))
        return docs[0] if docs else None
