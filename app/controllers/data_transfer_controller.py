import os
import logging
import re
from datetime import datetime
from PySide6.QtWidgets import QFileDialog, QMessageBox

from app.models.config_model import load_config, save_config
from app.models.data_transfer_model import DataTransferModel


class DataTransferController:
    def __init__(self, view):
        self.view = view
        self.config = load_config()
        self.model = DataTransferModel()
        self.detected_tables = []  # 存储检测到的大表文件路径
        self._connect_signals()
        self._initialize_view()

    def _connect_signals(self):
        """连接视图信号到控制器方法"""
        self.view.set_controller_connections(self)

    def _initialize_view(self):
        """初始化视图状态"""
        # 设置大表文件夹路径显示（使用独立配置）
        big_folder = self.config.get("data_transfer_big_folder", "")
        self.view.set_big_folder_path(big_folder)
        
        # 自动检测大表文件
        self.auto_detect_tables()
        
        # 加载大表菜名预览
        self.load_variety_preview()

    def reload_config(self):
        """重新加载配置"""
        self.config = load_config()
        self.view.reload_config()
        # 重新检测大表文件
        self.auto_detect_tables()
        # 重新加载菜名预览
        self.load_variety_preview()

    def auto_detect_tables(self):
        """自动检测大表文件"""
        big_folder = self.config.get("data_transfer_big_folder", "")
        if not big_folder or not os.path.isdir(big_folder):
            self.view.set_detected_tables([])
            self.view.append_status("大表文件夹路径无效或未设置")
            return
        
        # 获取当前日期
        y, m, d = self.view.get_date_components()
        
        # 构造基本文件名模式
        base_name = f"农残检测记录表{y}.{m}.{d}.docx"
        pattern = re.compile(rf"农残检测记录表{re.escape(y)}\.{re.escape(m)}\.{re.escape(d)}(?:-(\d+))?\.docx$")
        
        # 添加调试信息
        self.view.append_status(f"扫描文件夹: {big_folder}")
        self.view.append_status(f"查找日期: {y}.{m}.{d}")
        self.view.append_status(f"文件名模式: {pattern.pattern}")
        
        # 扫描文件夹
        detected = []
        try:
            file_list = os.listdir(big_folder)
            self.view.append_status(f"文件夹中有 {len(file_list)} 个文件")
            for filename in file_list:
                match = pattern.match(filename)
                if match:
                    # 提取编号（如果有）
                    num_str = match.group(1)
                    num = int(num_str) if num_str else 0
                    filepath = os.path.join(big_folder, filename)
                    detected.append((num, filepath))
                    self.view.append_status(f"  匹配文件: {filename} (编号: {num})")
                else:
                    # 可选：显示不匹配的文件以便调试
                    pass
        except Exception as e:
            logging.error(f"扫描大表文件夹失败: {e}")
            self.view.append_status(f"扫描大表文件夹失败: {e}")
            return
        
        # 按编号排序（主文件编号0，-1编号1，-2编号2...）
        detected.sort(key=lambda x: x[0])
        self.detected_tables = [path for _, path in detected]
        
        # 更新视图显示
        self.view.set_detected_tables(self.detected_tables)
        
        # 记录日志
        if self.detected_tables:
            logging.info(f"自动检测到 {len(self.detected_tables)} 个大表文件")
            self.view.append_status(f"自动检测到 {len(self.detected_tables)} 个大表文件")
        else:
            logging.warning(f"未找到日期 {y}.{m}.{d} 的大表文件")
            self.view.append_status(f"未找到日期 {y}.{m}.{d} 的大表文件")

        # 加载大表菜名预览
        self.load_variety_preview()

    def date_changed(self):
        """日期变化时重新检测大表文件"""
        # 保存日期到配置
        self.view.save_date_to_config()
        # 重新检测大表文件
        self.auto_detect_tables()

    # 大表文件夹选择
    def pick_big_folder(self):
        dialog = QFileDialog(self.view, "选择大表文件夹")
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly, True)
        dialog.setDirectory(self.config.get("data_transfer_big_folder", "") or os.getcwd())
        if dialog.exec():
            path = dialog.selectedFiles()[0]
            self.config["data_transfer_big_folder"] = path
            save_config(self.config)
            self.view.set_big_folder_path(path)
            self.auto_detect_tables()
            logging.info(f"大表文件夹设置为: {path}")

    # 小表类型变化
    def small_type_changed(self, small_type: str):
        self.config["last_used_small_type"] = small_type
        save_config(self.config)
        self.view._update_small_template_label()

    # 小表模板选择
    def pick_small_template(self):
        small_type = self.view.get_small_type()
        dialog = QFileDialog(self.view, f"选择{small_type}小表模板文件")
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setNameFilter("Word documents (*.docx);;All files (*.*)")
        # 获取当前类型模板的目录作为起始目录
        current_path = self.config.get("small_templates", {}).get(small_type, "")
        dialog.setDirectory(os.path.dirname(current_path) or os.getcwd())
        if dialog.exec():
            path = dialog.selectedFiles()[0]
            self.view.set_small_template_path(path)
            logging.info(f"{small_type}小表模板设置为: {path}")

    # 输出目录选择
    def pick_output_dir(self):
        dialog = QFileDialog(self.view, "选择输出目录")
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly, True)
        dialog.setDirectory(self.config.get("output_dir", os.getcwd()))
        if dialog.exec():
            path = dialog.selectedFiles()[0]
            self.view.set_output_dir(path)
            logging.info(f"输出目录设置为: {path}")

    # 菜名输入验证
    def validate_veg(self):
        raw = self.view.get_veg_text().strip()
        if not raw:
            self.view.update_veg_status("")
            self.view.update_preview_colors(set(), {})
            return
        vegs = self._parse_veg_list(raw)
        self.view.update_veg_status(f"将提取 {len(vegs)} 个菜名的数据")
        self.update_preview_matching()

    def _parse_veg_list(self, raw_text: str) -> list:
        """解析菜名列表，支持逗号分隔或换行分隔"""
        if not raw_text:
            return []
        if ',' in raw_text or '，' in raw_text:
            vegs = raw_text.replace('，', ',').split(',')
        else:
            vegs = raw_text.strip().split('\n')
        return [v.strip() for v in vegs if v.strip()]

    def check_duplicates(self):
        """核对菜名是否重复，去重后回填输入框"""
        raw = self.view.get_veg_text().strip()
        if not raw:
            return

        vegs = self._parse_veg_list(raw)
        if not vegs:
            return

        seen = set()
        unique_vegs = []
        for veg in vegs:
            key = veg.strip().lower()
            if key not in seen:
                seen.add(key)
                unique_vegs.append(veg)

        removed = len(vegs) - len(unique_vegs)

        if removed > 0:
            self.view.set_veg_text(", ".join(unique_vegs))
            self.view.update_veg_status(f"去除了 {removed} 个重复菜名")
        else:
            self.view.update_veg_status("未发现重复菜名")

    def load_variety_preview(self):
        """从大表中加载全部品种名到预览列表"""
        if not self.detected_tables:
            self.view.set_variety_preview([])
            return
        try:
            varieties = self.model.extract_all_varieties(self.detected_tables)
            self.view.set_variety_preview(varieties)
            logging.info(f"加载了 {len(varieties)} 个品种名到预览")
        except Exception as e:
            logging.error(f"加载品种名预览失败: {e}")
            self.view.set_variety_preview([])

    def update_preview_matching(self):
        """根据用户输入的菜名实时更新预览列表的高亮状态"""
        raw = self.view.get_veg_text().strip()
        if not raw:
            self.view.update_preview_colors(set(), {})
            return

        user_inputs = self._parse_veg_list(raw)
        matched_set = set(v.strip().lower() for v in user_inputs)

        aliases_config = self.config.get("dish_name_aliases", {})
        aliases_map = {}
        for main_name, alias_list in aliases_config.items():
            aliases_map[main_name.strip().lower()] = [a.strip().lower() for a in alias_list]

        self.view.update_preview_colors(matched_set, aliases_map)

    # 清除输入
    def clear_inputs(self):
        self.view.set_veg_text("")
        self.view.update_veg_status("")
        self.view.clear_status()
        self.view.update_preview_colors(set(), {})

    # 执行数据迁移
    def run_transfer(self):
        # 验证输入
        if not self.detected_tables:
            self.view.show_message("缺失", "未检测到大表文件，请检查日期和大表文件夹路径。", QMessageBox.Warning)
            return

        small_template = self.view.get_small_template_path()
        if not small_template:
            self.view.show_message("缺失", "请选择小表模板文件。", QMessageBox.Warning)
            return

        veg_text = self.view.get_veg_text().strip()
        if not veg_text:
            self.view.show_message("缺失", "请输入菜名。", QMessageBox.Warning)
            return

        output_dir = self.view.get_output_dir()
        if not output_dir:
            self.view.show_message("缺失", "请选择输出目录。", QMessageBox.Warning)
            return

        # 解析菜名
        veg_names = self._parse_veg_list(veg_text)
        if not veg_names:
            self.view.show_message("输入有误", "未识别到有效的菜名。", QMessageBox.Warning)
            return

        # 生成输出文件名
        small_type = self.view.get_small_type()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{small_type}_数据迁移_{timestamp}.docx"
        output_path = os.path.join(output_dir, output_filename)

        # 执行迁移
        self.view.clear_status()
        self.view.append_status(f"开始数据迁移...")
        self.view.append_status(f"大表文件夹: {self.config.get('big_path', '')}")
        self.view.append_status(f"检测到的大表文件数: {len(self.detected_tables)}")
        self.view.append_status(f"小表类型: {small_type}")
        self.view.append_status(f"小表模板: {small_template}")
        self.view.append_status(f"菜名: {', '.join(veg_names)}")
        self.view.append_status(f"输出文件: {output_path}")

        try:
            self.view.append_status("正在处理大表文件...")
            
            # 使用模型处理多个大表文件
            result = self.model.process_multiple_tables(
                table_paths=self.detected_tables,
                small_template_path=small_template,
                veg_names=veg_names,
                output_path=output_path
            )

            self.view.append_status("")
            self.view.append_status("=== 迁移完成 ===")
            self.view.append_status(f"处理大表文件数: {result['processed_files']}")
            self.view.append_status(f"匹配品种数: {result['matched_count']}")
            self.view.append_status(f"写入数据行数: {result['written_count']}")
            self.view.append_status(f"输出文件: {result['output_file']}")
            self.view.append_status(result['message'])
            
            # 显示匹配详情
            if result['details']:
                self.view.append_status("")
                self.view.append_status("匹配详情（前10条）:")
                for i, detail in enumerate(result['details'][:10], 1):
                    variety = detail.get('品种', '')
                    rate = detail.get('抑制%', '')
                    result_val = detail.get('结果', '')
                    self.view.append_status(f"  {i}. 品种: {variety}, 抑制%: {rate}, 结果: {result_val}")
                if len(result['details']) > 10:
                    self.view.append_status(f"  ... 还有 {len(result['details'])-10} 条数据")

            # 显示成功消息
            dialog = QMessageBox(self.view)
            dialog.setWindowTitle("迁移完成")
            dialog.setText(f"数据迁移完成！\n\n处理 {result['processed_files']} 个大表文件\n匹配 {result['matched_count']} 个品种\n写入 {result['written_count']} 行数据\n\n是否打开输出目录？")
            dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            dialog.button(QMessageBox.Yes).setText("打开输出目录")
            dialog.button(QMessageBox.No).setText("关闭")
            if dialog.exec() == QMessageBox.Yes:
                self._open_output_dir(output_dir)

        except Exception as e:
            logging.error(f"数据迁移失败: {e}", exc_info=True)
            self.view.append_status("")
            self.view.append_status("=== 迁移失败 ===")
            self.view.append_status(f"错误: {e}")
            self.view.show_message("错误", f"数据迁移失败：{e}", QMessageBox.Critical)

    def _open_output_dir(self, output_dir: str):
        """打开输出目录"""
        if not output_dir or not os.path.isdir(output_dir):
            return
        try:
            os.startfile(output_dir)
        except Exception as e:
            logging.warning(f"打开输出目录失败: {e}")