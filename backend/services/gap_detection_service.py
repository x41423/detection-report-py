import logging
from datetime import date, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class GapDetectionService:
    """Detect missing pesticide detection reports and support batch backfill."""

    def __init__(self, output_root: str = ""):
        self.output_root = Path(output_root) if output_root else None

    def detect_gaps(self, from_date: date, to_date: date) -> list[date]:
        """Return list of dates between from_date and to_date that lack big table reports."""
        if not self.output_root or not self.output_root.exists():
            return []

        missing = []
        current = from_date
        while current <= to_date:
            big_dir = self._report_dir(current, "big")
            if not big_dir.is_dir() or not list(big_dir.glob("*.docx")):
                missing.append(current)
            current = self._next_day(current)
        return missing

    def detect_recent_gaps(self, days: int = 7) -> list[date]:
        """Check recent N days for gaps."""
        end = date.today()
        start = end - timedelta(days=days)
        return self.detect_gaps(start, end)

    def _report_dir(self, target: date, kind: str) -> Path:
        return (self.output_root / str(target.year) /
                f"{target.month:02d}" / f"{target.day:02d}" / kind)

    def _next_day(self, d: date) -> date:
        return d + timedelta(days=1)
