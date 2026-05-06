import json
import os
import shutil
from backend.services.data_gen_service import (
    DataGeneratorService,
    parse_vegetable_list,
    remove_duplicate_varieties,
    parse_json_data,
    format_json_data,
)
from app.utils.doc_handler import process_documents
from backend.services.config_service import get_config, update_config


class PesticideService:
    """农残检测报告服务，状态隔离版本"""

    def __init__(self):
        cfg = get_config()
        self._gen = DataGeneratorService(
            high_risk=cfg.get("high_risk", []),
            low_risk=cfg.get("low_risk", []),
            rate_ranges=cfg.get("rate_ranges", {}),
        )

    def _refresh_generator(self):
        cfg = get_config()
        self._gen = DataGeneratorService(
            high_risk=cfg.get("high_risk", []),
            low_risk=cfg.get("low_risk", []),
            rate_ranges=cfg.get("rate_ranges", {}),
        )

    def generate_rates(self, veg_text: str) -> list[dict]:
        self._refresh_generator()
        vegs = parse_vegetable_list(veg_text)
        return self._gen.generate_rates(vegs)

    def dedup_json(self, json_text: str) -> tuple[list[dict], int]:
        data = parse_json_data(json_text)
        return remove_duplicate_varieties(data)

    def format_json(self, json_text: str) -> str:
        return format_json_data(parse_json_data(json_text))

    def execute_task(self, big_path, small_path, json_text, date_label, output_dir, inspector_name):
        if not os.path.exists(big_path):
            raise FileNotFoundError(f"大表文件不存在: {big_path}")
        if not os.path.exists(small_path):
            raise FileNotFoundError(f"小表文件不存在: {small_path}")
        if not os.path.isdir(output_dir):
            raise FileNotFoundError(f"输出目录不存在: {output_dir}")

        data = parse_json_data(json_text)
        if not data:
            raise ValueError("JSON 数据为空")

        process_documents(big_path, small_path, data, date_label, output_dir, inspector_name)

        cfg = get_config()
        if inspector_name and inspector_name != cfg.get("inspector_name"):
            update_config({"inspector_name": inspector_name})

        return {
            "success": True,
            "message": f"任务完成，共处理 {len(data)} 条数据",
            "data_count": len(data),
            "output_dir": output_dir,
        }

    def execute_monthly_task(
        self,
        entries: list[dict],
        big_template_path: str,
        small_template_path: str,
        month: str,
        output_dir: str,
        inspector_name: str = "",
    ) -> dict:
        """Run a per-day batch over ``entries`` and write a manifest.

        Each entry is ``{"date": "YYYY-MM-DD", "names": [...]}``. Per-day
        documents follow the confirmed file-name convention:

        - 大表 ``农残检测记录表{y}.{mm}.{dd}.docx`` (zero-padded month/day)
        - 小表 ``单位农残记录表{mm}.{d}.docx`` (zero-padded month, **non-padded day**)

        A failure on a single date does not abort the rest of the batch; it
        is recorded in the manifest's ``items`` list with status ``failed``.
        """
        if not os.path.exists(big_template_path):
            raise FileNotFoundError(f"大表模板不存在: {big_template_path}")
        if not os.path.exists(small_template_path):
            raise FileNotFoundError(f"小表模板不存在: {small_template_path}")
        if not os.path.isdir(output_dir):
            raise FileNotFoundError(f"输出目录不存在: {output_dir}")

        workspace = os.path.join(output_dir, ".pesticide_workspace")
        os.makedirs(workspace, exist_ok=True)

        items: list[dict] = []
        success_count = 0
        failure_count = 0

        try:
            for raw_entry in entries or []:
                entry = raw_entry or {}
                date_str = str(entry.get("date") or "").strip()
                names_raw = [str(n).strip() for n in (entry.get("names") or []) if str(n).strip()]
                names = list(dict.fromkeys(names_raw))
                try:
                    year_str, month_str, day_str = date_str.split("-")
                    y, m, d = int(year_str), int(month_str), int(day_str)
                except Exception as exc:
                    items.append(
                        {
                            "date": date_str,
                            "status": "failed",
                            "error": f"日期格式错误: {exc}",
                            "names": names,
                        }
                    )
                    failure_count += 1
                    continue

                big_filename = f"农残检测记录表{y}.{m:02d}.{d:02d}.docx"
                small_filename = f"单位农残记录表{m:02d}.{d}.docx"
                big_path = os.path.join(workspace, big_filename)
                small_path = os.path.join(workspace, small_filename)

                try:
                    shutil.copyfile(big_template_path, big_path)
                    shutil.copyfile(small_template_path, small_path)
                    data = self.generate_rates("\n".join(names))
                    date_label = f"{y}年{m}月{d}日"
                    process_documents(
                        big_path,
                        small_path,
                        data,
                        date_label,
                        output_dir,
                        inspector_name,
                    )
                    success_count += 1
                    items.append(
                        {
                            "date": date_str,
                            "status": "success",
                            "big_file": big_filename,
                            "small_file": small_filename,
                            "names": names,
                        }
                    )
                except Exception as exc:
                    failure_count += 1
                    items.append(
                        {
                            "date": date_str,
                            "status": "failed",
                            "error": str(exc),
                            "names": names,
                        }
                    )
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

        if inspector_name:
            try:
                cfg = get_config()
                if inspector_name != cfg.get("inspector_name"):
                    update_config({"inspector_name": inspector_name})
            except Exception:
                pass

        manifest = {
            "month": month,
            "inspector_name": inspector_name,
            "success_count": success_count,
            "failure_count": failure_count,
            "items": items,
        }
        manifest_path = os.path.join(output_dir, "处理结果清单.json")
        with open(manifest_path, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, ensure_ascii=False, indent=2)
        return manifest

    def find_target_files(self, big_dir, small_dir, y, m, d):
        d_int = int(d)
        big_file = os.path.join(big_dir, f"农残检测记录表{y}.{m}.{d}.docx")
        small_file = os.path.join(small_dir, f"单位农残记录表{m}.{d_int}.docx")
        return {
            "big_file": big_file,
            "small_file": small_file,
            "big_exists": os.path.exists(big_file),
            "small_exists": os.path.exists(small_file),
        }
