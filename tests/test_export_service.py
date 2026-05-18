import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from backend.services.export_service import ExportService


def test_export_result_structure():
    with tempfile.TemporaryDirectory() as tmpdir:
        service = ExportService()
        result = service.export_detection_report(
            target_date="2026-05-18",
            docx_paths=["/fake/a.docx"],
            output_dir=tmpdir,
            format="docx"
        )
        assert "docx_files" in result
        assert len(result["docx_files"]) == 0  # fake path doesn't exist


@patch("subprocess.run")
def test_docx_to_pdf_mock(mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    service = ExportService()
    result = service.docx_to_pdf(Path("/fake/test.docx"))
    assert result is None  # fake path doesn't exist, but subprocess wasn't actually called
