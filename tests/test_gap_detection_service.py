import tempfile
from datetime import date
from pathlib import Path
from backend.services.gap_detection_service import GapDetectionService


def test_detect_gaps():
    with tempfile.TemporaryDirectory() as tmpdir:
        Path(tmpdir, "2026", "05", "18", "big").mkdir(parents=True)
        (Path(tmpdir) / "2026" / "05" / "18" / "big" / "test.docx").touch()

        svc = GapDetectionService(output_root=tmpdir)
        gaps = svc.detect_gaps(date(2026, 5, 15), date(2026, 5, 20))

        # 05-18 has report, others are missing
        assert date(2026, 5, 18) not in gaps
        assert date(2026, 5, 15) in gaps


def test_no_gaps():
    with tempfile.TemporaryDirectory() as tmpdir:
        svc = GapDetectionService(output_root=tmpdir)
        gaps = svc.detect_gaps(date(2026, 5, 15), date(2026, 5, 20))
        assert len(gaps) == 6
