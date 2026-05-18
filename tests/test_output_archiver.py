import os
import tempfile
from datetime import date
from pathlib import Path
from backend.services.output_archiver import OutputArchiver


def test_archive_single_day():
    with tempfile.TemporaryDirectory() as output_root:
        big_dir = Path(output_root) / "_workspace"
        big_dir.mkdir(exist_ok=True)
        big_file = big_dir / "农残检测记录表2026.05.18.docx"
        big_file.write_text("fake docx")

        archiver = OutputArchiver(output_root)
        result = archiver.archive(big_dir, date(2026, 5, 18))

        expected_dir = Path(output_root) / "2026" / "05" / "18" / "big"
        assert expected_dir.exists()
        assert (expected_dir / "农残检测记录表2026.05.18.docx").exists()
        assert result["archived_count"] >= 1


def test_archive_structure():
    with tempfile.TemporaryDirectory() as output_root:
        archiver = OutputArchiver(output_root)
        d = date(2026, 5, 18)
        archiver.archive(output_root, d)
        assert (Path(output_root) / "2026" / "05" / "18").exists()
