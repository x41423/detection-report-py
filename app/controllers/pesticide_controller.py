import os
import logging
from PySide6.QtWidgets import QFileDialog, QMessageBox

from app.models.config_model import load_config, save_config
from app.utils.data_generator import (
    format_json_data,
    gen_inhibition_rates,
    parse_json_data,
    parse_vegetable_list,
    remove_duplicate_varieties,
    set_risk_lists,
    set_rate_ranges,
)
from app.utils.doc_handler import process_documents


class PesticideController:
    def __init__(self, view):
        self.view = view
        self.config = load_config()
        self._initialize_data_generator()
        self._connect_signals()

    def _initialize_data_generator(self):
        """初始化数据生成器配置"""
        set_risk_lists(self.config.get("high_risk", []), self.config.get("low_risk", []))
        set_rate_ranges(self.config.get("rate_ranges", {}))

    def _connect_signals(self):
        """连接视图信号到控制器方法"""
        self.view.set_controller_connections(self)

    def reload_config(self):
        """重新加载配置"""
        self.config = load_config()
        self._initialize_data_generator()
        self.view.reload_config()

    # 路径选择
    def pick_big_dir(self):
        dialog = QFileDialog(self.view, "选择大表文件夹")
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly, True)
        dialog.setDirectory(self.config.get("big_path", os.getcwd()))
        if dialog.exec():
            p = dialog.selectedFiles()[0]
            self.config["big_path"] = p
            save_config(self.config)
            self.view._refresh_paths_ui()
            logging.info(f"大表路径设置为: {p}")

    def pick_small_dir(self):
        dialog = QFileDialog(self.view, "选择小表文件夹")
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly, True)
        dialog.setDirectory(self.config.get("small_path", os.getcwd()))
        if dialog.exec():
            p = dialog.selectedFiles()[0]
            self.config["small_path"] = p
            save_config(self.config)
            self.view._refresh_paths_ui()
            logging.info(f"小表路径设置为: {p}")

    def pick_output_dir(self):
        dialog = QFileDialog(self.view, "选择输出文件夹")
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly, True)
        dialog.setDirectory(self.config.get("output_dir", os.getcwd()))
        if dialog.exec():
            p = dialog.selectedFiles()[0]
            self.config["output_dir"] = p
            save_config(self.config)
            self.view._refresh_paths_ui()
            logging.info(f"输出路径设置为: {p}")

    # 日期验证
    def validate_date(self):
        self.view._refresh_day_options()
        if self.view._is_date_valid():
            self.view.update_veg_status("日期有效")
        else:
            self.view.update_veg_status("日期无效，请重新选择")

    # 数据输入验证
    def validate_veg(self):
        raw = self.view.get_veg_text().strip()
        if not raw:
            self.view.update_veg_status("")
            return
        try:
            vegs = parse_vegetable_list(raw)
            self.view.update_veg_status(f"有效：{len(vegs)} 个品种")
        except Exception as e:
            self.view.update_veg_status(f"无效：{e}")

    def validate_json(self):
        raw = self.view.get_json_text().strip()
        if not raw:
            self.view.update_json_status("")
            self.view.update_count_label(0)
            return
        try:
            data = parse_json_data(raw)
            self.view.update_json_status(f"有效：{len(data)} 条记录")
            self.view.update_count_label(len(data))
        except Exception as e:
            self.view.update_json_status(f"无效：{e}")

    # 数据操作
    def generate_rates(self):
        try:
            if not self.view._is_date_valid():
                self.view.show_message("日期无效", "请选择有效日期后再生成抑制率。", QMessageBox.Warning)
                return
            raw = self.view.get_veg_text().strip()
            if not raw:
                self.view.show_message("输入有误", "请输入蔬菜品种后再生成抑制率。", QMessageBox.Warning)
                return

            vegs = parse_vegetable_list(raw)
            res = gen_inhibition_rates(vegs)
            self.view.set_json_text(format_json_data(res))
            self.view.update_count_label(len(res))
            logging.info(f"生成抑制率成功: {len(res)} 个品种")
        except Exception as e:
            logging.error(f"生成抑制率失败: {e}", exc_info=True)
            self.view.show_message("错误", f"生成抑制率失败：{e}", QMessageBox.Critical)

    def check_duplicates(self):
        try:
            data = parse_json_data(self.view.get_json_text())
            unique_data, removed = remove_duplicate_varieties(data)
            self.view.set_json_text(format_json_data(unique_data))
            self.view.update_count_label(len(unique_data))
            logging.info(f"查重完成: 删除了 {removed} 个重复品种")
            QMessageBox.information(self.view, "查重完成", f"删除了 {removed} 个重复品种。")
        except Exception as e:
            logging.error(f"查重失败: {e}", exc_info=True)
            self.view.show_message("错误", f"查重失败：{e}", QMessageBox.Critical)

    def clear_inputs(self):
        self.view.set_veg_text("")
        self.view.set_json_text("")
        self.view.update_count_label(0)
        self.view.update_veg_status("")
        self.view.update_json_status("")

    def import_from_file(self):
        dialog = QFileDialog(self.view, "导入品种文件")
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setNameFilter("Text files (*.txt);;All files (*.*)")
        dialog.setDirectory(os.getcwd())
        if not dialog.exec():
            return
        file_path = dialog.selectedFiles()[0]
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            self.view.set_veg_text(content)
            logging.info(f"从文件导入: {file_path}")
        except Exception as e:
            logging.error(f"导入失败: {e}")
            self.view.show_message("错误", f"导入失败：{e}", QMessageBox.Critical)

    def format_json(self):
        try:
            data = parse_json_data(self.view.get_json_text())
            self.view.set_json_text(format_json_data(data))
        except Exception as e:
            self.view.show_message("输入有误", str(e), QMessageBox.Warning)

    def reset_form(self):
        self.clear_inputs()
        self.view._set_today()

    # 主任务
    def run_task(self):
        if not self._ensure_paths_ok():
            return

        big, small = self._get_target_files()
        if not os.path.exists(big) or not os.path.exists(small):
            self.view.show_message(
                "缺失",
                f"文件不存在，请检查路径和日期是否匹配！\n\n大表: {big}\n小表: {small}",
                QMessageBox.Critical,
            )
            logging.error(f"文件不存在: 大表={big}, 小表={small}")
            return

        try:
            data = parse_json_data(self.view.get_json_text())
            if not data:
                self.view.show_message("错误", "JSON 数据为空，请先生成或粘贴数据。", QMessageBox.Critical)
                return

            y, m, d = self.view.get_date_components()
            date_label = self.config.get("date_format", "{y}年{m}月{d}日").format(y=y, m=int(m), d=int(d))
            inspector_name = self.view.get_inspector_name() or self.config.get("inspector_name", "朱林初")

            process_documents(big, small, data, date_label, self.config["output_dir"], inspector_name)

            # 保存核验员为上次使用值
            if inspector_name != self.config.get("inspector_name"):
                self.config["inspector_name"] = inspector_name
                save_config(self.config)

            logging.info("任务成功完成")

            dialog = QMessageBox(self.view)
            dialog.setWindowTitle("成功")
            dialog.setText("任务完成！日期和主检人已修改，排版保护已生效。\n\n是否打开输出目录？")
            dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            dialog.button(QMessageBox.Yes).setText("打开输出目录")
            dialog.button(QMessageBox.No).setText("关闭")
            if dialog.exec() == QMessageBox.Yes:
                self._open_output_dir()
        except PermissionError:
            self.view.show_message("错误", "输出文件被占用或没有权限，请关闭已打开的文档后重试。", QMessageBox.Critical)
        except Exception as e:
            logging.error(f"任务失败: {e}", exc_info=True)
            self.view.show_message("错误", f"发生错误：{e}", QMessageBox.Critical)

    def _ensure_paths_ok(self) -> bool:
        if not self.view._is_date_valid():
            self.view.show_message("日期无效", "请选择有效日期后再执行。", QMessageBox.Warning)
            return False

        big_path = self.config.get("big_path", "")
        small_path = self.config.get("small_path", "")
        output_path = self.config.get("output_dir", "")

        if not big_path or not small_path or not output_path:
            self.view.show_message("缺失", "请先设置大表、小表和输出文件夹路径。", QMessageBox.Critical)
            return False

        if not os.path.isdir(big_path) or not os.path.isdir(small_path):
            self.view.show_message("缺失", "大表或小表路径无效，请重新选择。", QMessageBox.Critical)
            return False

        if not os.path.isdir(output_path):
            self.view.show_message("缺失", "输出路径无效，请重新选择。", QMessageBox.Critical)
            return False

        return True

    def _get_target_files(self):
        y, m, d = self.view.get_date_components()
        d_int = int(d)
        big = os.path.join(self.config["big_path"], f"农残检测记录表{y}.{m}.{d}.docx")
        small = os.path.join(self.config["small_path"], f"单位农残记录表{m}.{d_int}.docx")
        return big, small

    def _open_output_dir(self):
        output_dir = self.config.get("output_dir", "")
        if not output_dir or not os.path.isdir(output_dir):
            return
        try:
            os.startfile(output_dir)
        except Exception as e:
            logging.warning(f"打开输出目录失败: {e}")