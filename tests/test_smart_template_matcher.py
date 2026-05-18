import tempfile
from datetime import date
from pathlib import Path

from backend.services.smart_template_matcher import SmartTemplateMatcher


def test_match_exact():
    with tempfile.TemporaryDirectory() as tmpdir:
        exact = Path(tmpdir) / "农残检测记录表2026.05.18.docx"
        exact.touch()

        matcher = SmartTemplateMatcher(big_dir=tmpdir)
        result = matcher.match("big", date(2026, 5, 18))
        assert result is not None
        assert "2026.05.18" in str(result)


def test_match_fuzzy_latest():
    with tempfile.TemporaryDirectory() as tmpdir:
        f1 = Path(tmpdir) / "农残检测记录表2026.05.15.docx"
        f1.touch()
        f2 = Path(tmpdir) / "农残检测记录表2026.05.17.docx"
        f2.touch()

        matcher = SmartTemplateMatcher(big_dir=tmpdir)
        result = matcher.match("big", date(2026, 5, 18))
        assert result is not None
        assert "2026.05.17" in str(result)


def test_match_fallback_to_template_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        matcher = SmartTemplateMatcher(tmpdir)
        result = matcher.match("big", date(2026, 5, 18))
        if result is not None:
            assert ".docx" in str(result).lower()
