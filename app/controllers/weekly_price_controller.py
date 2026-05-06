import logging
import os

from PySide6.QtWidgets import QFileDialog

from app.models.config_model import load_config, save_config
from app.utils.weekly_price_update import update_weekly_prices


def _default_output_path(source_path: str) -> str:
    source_path = (source_path or "").strip()
    if not source_path:
        return ""
    directory = os.path.dirname(source_path)
    stem, _ = os.path.splitext(os.path.basename(source_path))
    return os.path.join(directory, f"{stem}_weekly_updated.xlsx")


class WeeklyPriceController:
    def __init__(self, view):
        self.view = view
        self.config = load_config()
        self._connect()
        self._restore_paths()

    def _connect(self):
        self.view.set_controller(self)

    def _restore_paths(self):
        self.view.set_update_path(self.config.get("weekly_price_update_path", ""))
        self.view.set_reference_path(self.config.get("weekly_price_reference_path", ""))
        self.view.set_output_path(self.config.get("weekly_price_output_path", ""))

    def _save_config(self):
        save_config(self.config)

    def pick_update_file(self):
        path = self._pick_file("选择待更新报价表")
        if path:
            previous_output = self.view.get_output_path()
            previous_source = self.view.get_update_path()
            self.view.set_update_path(path)
            self.config["weekly_price_update_path"] = path
            if not previous_output or previous_output == _default_output_path(previous_source):
                suggested_output = _default_output_path(path)
                self.view.set_output_path(suggested_output)
                self.config["weekly_price_output_path"] = suggested_output
            self._save_config()
            logging.info("待更新报价表已设置: %s", path)

    def pick_reference_file(self):
        path = self._pick_file("选择参考报价表")
        if path:
            self.view.set_reference_path(path)
            self.config["weekly_price_reference_path"] = path
            self._save_config()
            logging.info("参考报价表已设置: %s", path)

    def pick_output_file(self):
        initial_path = self.view.get_output_path() or _default_output_path(self.view.get_update_path())
        path, _ = QFileDialog.getSaveFileName(
            self.view,
            "选择输出文件",
            initial_path,
            "Excel files (*.xlsx *.xls *.xlsm);;All files (*.*)",
        )
        if path:
            self.view.set_output_path(path)
            self.config["weekly_price_output_path"] = path
            self._save_config()
            logging.info("输出路径已设置: %s", path)

    def _pick_file(self, title: str) -> str:
        dialog = QFileDialog(self.view, title)
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setNameFilter("Excel files (*.xlsx *.xls *.xlsm);;All files (*.*)")
        if dialog.exec():
            return dialog.selectedFiles()[0]
        return ""

    def run_update(self):
        update_path = self.view.get_update_path()
        ref_path = self.view.get_reference_path()
        output_path = self.view.get_output_path()

        if not update_path or not os.path.exists(update_path):
            self.view.update_status("待更新报价表路径无效或不存在")
            return

        if not ref_path or not os.path.exists(ref_path):
            self.view.update_status("参考报价表路径无效或不存在")
            return

        if not output_path:
            self.view.update_status("请先指定输出路径")
            return

        output_dir = os.path.dirname(os.path.abspath(output_path))
        if output_dir and not os.path.isdir(output_dir):
            self.view.update_status(f"输出路径所在目录不存在: {output_dir}")
            return

        self.config["weekly_price_output_path"] = output_path
        self._save_config()

        self.view.update_status("开始执行周报价更新...")
        try:
            summary = update_weekly_prices(update_path, ref_path, output_path=output_path)
            self.view.update_status(
                f"更新完成: 更新 {summary.get('updated_count', 0)} 条, "
                f"匹配 {summary.get('matched_count', 0)} 条"
            )
            if summary.get("warning"):
                self.view.update_status(summary["warning"])
            if summary.get("output_path"):
                self.view.update_status(f"输出文件: {summary['output_path']}")
            if summary.get("not_matched"):
                self.view.update_status(
                    f"未匹配的菜名: {', '.join(summary['not_matched'])}"
                )
        except Exception as exc:
            logging.error("周报价更新失败: %s", exc, exc_info=True)
            self.view.update_status(f"更新失败: {exc}")
