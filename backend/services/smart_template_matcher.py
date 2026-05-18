import logging
import re
from datetime import date
from pathlib import Path

from backend.services.template_library_service import get_pesticide_template_path

logger = logging.getLogger(__name__)

BIG_PATTERN = re.compile(r"农残检测记录表(\d{4})\.(\d{2})\.(\d{2})", re.IGNORECASE)
SMALL_PATTERN = re.compile(r"单位农残记录表(\d{1,2})\.(\d{1,2})", re.IGNORECASE)


class SmartTemplateMatcher:
    """Intelligently match pesticide detection templates by date, falling back to nearest match."""

    def __init__(self, big_dir: str | None = None, small_dir: str | None = None):
        self.big_dir = Path(big_dir) if big_dir else None
        self.small_dir = Path(small_dir) if small_dir else None

    def match(self, kind: str, target_date: date) -> Path | None:
        """Match a template file for the given kind (big/small) and target date."""
        if kind == "big":
            return self._match_big(target_date)
        elif kind == "small":
            return self._match_small(target_date)
        return None

    def _match_big(self, target_date: date) -> Path | None:
        if self.big_dir and self.big_dir.is_dir():
            exact_name = f"农残检测记录表{target_date.year}.{target_date.month:02d}.{target_date.day:02d}.docx"
            exact_path = self.big_dir / exact_name
            if exact_path.exists():
                return exact_path
            best = self._find_closest(self.big_dir, BIG_PATTERN, target_date)
            if best:
                return best
        try:
            return get_pesticide_template_path("big")
        except FileNotFoundError:
            logger.warning("No big template found in library")
            return None

    def _match_small(self, target_date: date) -> Path | None:
        if self.small_dir and self.small_dir.is_dir():
            exact_name = f"单位农残记录表{target_date.month}.{target_date.day}.docx"
            exact_path = self.small_dir / exact_name
            if exact_path.exists():
                return exact_path
            best = self._find_closest(self.small_dir, SMALL_PATTERN, target_date)
            if best:
                return best
        try:
            return get_pesticide_template_path("small")
        except FileNotFoundError:
            logger.warning("No small template found in library")
            return None

    def _find_closest(self, directory: Path, pattern: re.Pattern,
                      target_date: date) -> Path | None:
        candidates = []
        for f in directory.glob("*.docx"):
            match = pattern.search(f.name)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 3:
                        y, m, d = int(groups[0]), int(groups[1]), int(groups[2])
                        file_date = date(y, m, d)
                    elif len(groups) == 2:
                        m, d = int(groups[0]), int(groups[1])
                        file_date = date(target_date.year, m, d)
                    else:
                        continue
                    diff = abs((target_date - file_date).days)
                    candidates.append((diff, f))
                except (ValueError, IndexError):
                    continue
        if candidates:
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1]
        return None
