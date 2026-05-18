import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class ExportService:
    """Export detection reports to PDF via LibreOffice headless or just copy DOCX."""

    LIBREOFFICE_PATHS = [
        "soffice",
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]

    def docx_to_pdf(self, docx_path: Path) -> Path | None:
        if not docx_path.exists():
            logger.warning(f"DOCX not found: {docx_path}")
            return None

        output_dir = docx_path.parent

        for lo_path in self.LIBREOFFICE_PATHS:
            try:
                result = subprocess.run(
                    [
                        lo_path,
                        "--headless",
                        "--convert-to",
                        "pdf",
                        "--outdir",
                        str(output_dir),
                        str(docx_path),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if result.returncode == 0:
                    pdf_path = output_dir / f"{docx_path.stem}.pdf"
                    if pdf_path.exists():
                        return pdf_path
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
            except Exception as e:
                logger.warning(f"LibreOffice convert failed with {lo_path}: {e}")

        logger.warning("LibreOffice not available, PDF conversion skipped")
        return None

    def export_detection_report(
        self, target_date: str, docx_paths: list[str], output_dir: str, format: str = "both"
    ) -> dict:
        result = {"docx_files": [], "pdf_files": [], "date": target_date}

        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        for docx_str in docx_paths:
            src = Path(docx_str)
            if not src.exists():
                continue
            dst = out / src.name
            shutil.copy2(src, dst)
            result["docx_files"].append(str(dst))

            if format in ("pdf", "both"):
                pdf = self.docx_to_pdf(dst)
                if pdf:
                    result["pdf_files"].append(str(pdf))

        return result
