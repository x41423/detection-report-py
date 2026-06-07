import os
import logging
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QColor
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QPlainTextEdit,
    QSizePolicy,
    QSpacerItem,
    QComboBox,
    QGraphicsDropShadowEffect,
    QFileDialog,
    QMessageBox,
    QListView,
    QScrollArea,
    QTextBrowser,
)

try:
    import qtawesome as qta
except Exception:
    qta = None

from app.models.config_model import load_config, save_config


class DataTransferView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = load_config()
        self._build_ui()
        self._apply_material_icons()
        self._load_config_to_ui()

    def _build_ui(self):
        # 主水平布局 - 左右两栏
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        # ===== 左栏 - 主要操作区域 =====
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        left_scroll.setMinimumWidth(480)
        
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(12)
        left_layout.setContentsMargins(0, 0, 8, 0)

        # 1) 大表文件夹和日期选择卡片
        grp_big = self._card_box("1. 大表文件夹和日期设置")
        big_layout = QGridLayout(grp_big)
        big_layout.setColumnStretch(1, 1)

        # 大表文件夹路径（可点击选择）
        big_layout.addWidget(QLabel("大表文件夹路径"), 0, 0)
        self.btn_big_folder = QPushButton("选择大表文件夹")
        self.btn_big_folder.setMinimumWidth(120)
        big_layout.addWidget(self.btn_big_folder, 0, 1)
        
        # 自动检测按钮
        self.btn_auto_detect = QPushButton("自动检测大表文件")
        big_layout.addWidget(self.btn_auto_detect, 0, 2)
        
        # 大表文件夹路径显示（只读）
        big_layout.addWidget(QLabel("当前路径"), 1, 0)
        self.lbl_big_folder = QLabel("未设置")
        self.lbl_big_folder.setWordWrap(True)
        self.lbl_big_folder.setTextInteractionFlags(Qt.TextSelectableByMouse)
        big_layout.addWidget(self.lbl_big_folder, 1, 1, 1, 2)
        
        # 日期选择器
        big_layout.addWidget(QLabel("检测日期"), 2, 0)
        date_layout = QHBoxLayout()
        self.cmb_year = QComboBox()
        self.cmb_month = QComboBox()
        self.cmb_day = QComboBox()
        self.cmb_year.addItems([str(y) for y in range(2025, 2028)])
        self.cmb_month.addItems([f"{m:02d}" for m in range(1, 13)])
        self.cmb_day.addItems([f"{d:02d}" for d in range(1, 32)])
        
        # 设置下拉框宽度，确保数字完全显示
        for combo in (self.cmb_year, self.cmb_month, self.cmb_day):
            combo.setView(QListView())
            combo.view().setMinimumWidth(80)
            combo.setMinimumWidth(90)
            combo.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        
        date_layout.addWidget(self.cmb_year)
        date_layout.addWidget(QLabel("年"))
        date_layout.addWidget(self.cmb_month)
        date_layout.addWidget(QLabel("月"))
        date_layout.addWidget(self.cmb_day)
        date_layout.addWidget(QLabel("日"))
        date_layout.addStretch()
        big_layout.addLayout(date_layout, 2, 1, 1, 2)
        
        # 检测到的大表文件列表
        big_layout.addWidget(QLabel("检测到的大表文件"), 3, 0)
        self.lbl_detected_tables = QLabel("未检测")
        self.lbl_detected_tables.setWordWrap(True)
        big_layout.addWidget(self.lbl_detected_tables, 3, 1, 1, 2)

        # 2) 小表类型和模板卡片
        grp_small = self._card_box("2. 选择小表类型和模板")
        small_layout = QGridLayout(grp_small)
        small_layout.setColumnStretch(1, 1)

        # 小表类型选择
        small_layout.addWidget(QLabel("小表类型"), 0, 0)
        self.cmb_small_type = QComboBox()
        self.cmb_small_type.addItems(["滨鲜", "1号", "5号", "6号", "7号", "8号", "顾家"])
        self.cmb_small_type.setMinimumWidth(120)
        small_layout.addWidget(self.cmb_small_type, 0, 1)

        # 小表模板路径
        small_layout.addWidget(QLabel("小表模板文件"), 1, 0)
        self.btn_small_template = QPushButton("选择模板文件")
        self.lbl_small_template = QLabel("未选择")
        self.lbl_small_template.setWordWrap(True)
        self.lbl_small_template.setTextInteractionFlags(Qt.TextSelectableByMouse)
        small_layout.addWidget(self.btn_small_template, 1, 1)
        small_layout.addWidget(self.lbl_small_template, 1, 2)

        # 3) 菜名输入卡片
        grp_veg = self._card_box("3. 输入菜名")
        veg_layout = QVBoxLayout(grp_veg)

        veg_layout.addWidget(QLabel("菜名（逗号分隔或每行一个）"))
        self.txt_veg = QPlainTextEdit()
        self.txt_veg.setPlaceholderText("例如: 白菜,菠菜,生菜")
        self.txt_veg.setMaximumHeight(120)
        veg_layout.addWidget(self.txt_veg)

        # 菜名操作按钮行
        veg_btn_layout = QHBoxLayout()
        self.btn_check_dup = QPushButton("核对菜名重复")
        veg_btn_layout.addWidget(self.btn_check_dup)
        veg_btn_layout.addStretch()
        veg_layout.addLayout(veg_btn_layout)

        self.lbl_veg_status = QLabel("")
        veg_layout.addWidget(self.lbl_veg_status)

        # 添加到左栏
        left_layout.addWidget(grp_big)
        left_layout.addWidget(grp_small)
        left_layout.addWidget(grp_veg, 1)
        
        left_scroll.setWidget(left_widget)

        # ===== 右栏 - 辅助信息区域 =====
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(12)
        right_layout.setContentsMargins(8, 0, 0, 0)

        # 4) 输出目录卡片
        grp_output = self._card_box("4. 选择输出目录")
        output_layout = QGridLayout(grp_output)
        output_layout.setColumnStretch(1, 1)

        self.btn_output_dir = QPushButton("选择输出目录")
        self.lbl_output_dir = QLabel("未选择")
        self.lbl_output_dir.setWordWrap(True)
        self.lbl_output_dir.setTextInteractionFlags(Qt.TextSelectableByMouse)
        output_layout.addWidget(self.btn_output_dir, 0, 0)
        output_layout.addWidget(self.lbl_output_dir, 0, 1)

        # 5) 大表菜名预览卡片
        grp_preview = self._card_box("5. 大表菜名预览")
        preview_layout = QVBoxLayout(grp_preview)
        self.lbl_preview_info = QLabel("未加载")
        preview_layout.addWidget(self.lbl_preview_info)
        self.preview_browser = QTextBrowser()
        self.preview_browser.setMinimumHeight(80)
        self.preview_browser.setMaximumHeight(160)
        self.preview_browser.setOpenExternalLinks(False)
        preview_layout.addWidget(self.preview_browser)

        # 6) 操作卡片
        grp_action = self._card_box("6. 执行")
        action_layout = QVBoxLayout(grp_action)
        action_layout.setSpacing(10)

        self.btn_clear = QPushButton("清除输入")
        self.btn_run = QPushButton("开始提取并写入")
        action_layout.addWidget(self.btn_clear)
        action_layout.addWidget(self.btn_run)

        # 6) 状态显示
        grp_status = self._card_box("状态")
        status_layout = QVBoxLayout(grp_status)
        self.txt_status = QPlainTextEdit()
        self.txt_status.setReadOnly(True)
        self.txt_status.setMinimumHeight(150)
        status_layout.addWidget(self.txt_status)

        # 添加到右栏
        right_layout.addWidget(grp_output)
        right_layout.addWidget(grp_preview)
        right_layout.addWidget(grp_action)
        right_layout.addWidget(grp_status, 1)

        # 设置比例 2:1
        main_layout.addWidget(left_scroll, 2)
        main_layout.addWidget(right_widget, 1)

    def _card_box(self, title: str) -> QGroupBox:
        box = QGroupBox(title)
        box.setObjectName("card")
        shadow = QGraphicsDropShadowEffect(blurRadius=24, xOffset=0, yOffset=6)
        shadow.setColor(Qt.black)
        box.setGraphicsEffect(shadow)
        return box

    def _apply_material_icons(self):
        if qta is None:
            return

        def safe_icon(name: str, color: str = None):
            try:
                return qta.icon(name, color=color) if color else qta.icon(name)
            except Exception:
                return QIcon()

        # 确定图标颜色
        icon_color = "#00BCD4"  # 默认青色
        try:
            palette = QApplication.instance().palette()
            is_dark = palette.window().color().value() < 128
            icon_color = "#26C6DA" if is_dark else "#00BCD4"
        except Exception:
            pass

        # 按钮图标
        self.btn_big_folder.setIcon(safe_icon("mdi.folder", icon_color))
        self.btn_auto_detect.setIcon(safe_icon("mdi.magnify", icon_color))
        self.btn_small_template.setIcon(safe_icon("mdi.file-document", icon_color))
        self.btn_output_dir.setIcon(safe_icon("mdi.folder", icon_color))
        self.btn_clear.setIcon(safe_icon("mdi.eraser", icon_color))
        self.btn_run.setIcon(safe_icon("mdi.play", icon_color))
        self.btn_check_dup.setIcon(safe_icon("mdi.check-circle", icon_color))

    def _load_config_to_ui(self):
        """从配置加载UI状态"""
        # 大表文件夹路径（从独立配置读取）
        big_folder_path = self.config.get("data_transfer_big_folder", "")
        self.lbl_big_folder.setText(big_folder_path or "未设置")
        
        # 日期设置（默认今日，或从配置读取上次日期）
        from datetime import datetime
        today = datetime.now()
        last_date = self.config.get("data_transfer_last_date", "")
        if last_date:
            try:
                year, month, day = last_date.split("-")
                self.cmb_year.setCurrentText(year)
                self.cmb_month.setCurrentText(month)
                self.cmb_day.setCurrentText(day)
            except (ValueError, IndexError):
                # 如果解析失败，使用今日日期
                self.cmb_year.setCurrentText(str(today.year))
                self.cmb_month.setCurrentText(f"{today.month:02d}")
                self.cmb_day.setCurrentText(f"{today.day:02d}")
        else:
            self.cmb_year.setCurrentText(str(today.year))
            self.cmb_month.setCurrentText(f"{today.month:02d}")
            self.cmb_day.setCurrentText(f"{today.day:02d}")

        # 小表类型
        last_type = self.config.get("last_used_small_type", "滨鲜")
        index = self.cmb_small_type.findText(last_type)
        if index >= 0:
            self.cmb_small_type.setCurrentIndex(index)

        # 小表模板路径（根据当前选择的类型）
        self._update_small_template_label()

        # 输出目录
        output_dir = self.config.get("output_dir", "")
        self.lbl_output_dir.setText(output_dir or "未选择")

    def _update_small_template_label(self):
        """更新小表模板标签显示"""
        small_type = self.cmb_small_type.currentText()
        templates = self.config.get("small_templates", {})
        path = templates.get(small_type, "")
        self.lbl_small_template.setText(path or "未选择")

    def reload_config(self):
        """重新加载配置"""
        self.config = load_config()
        self._load_config_to_ui()

    # 以下方法用于控制器连接信号
    def set_controller_connections(self, controller):
        """设置控制器连接的信号"""
        self.btn_big_folder.clicked.connect(controller.pick_big_folder)
        self.btn_auto_detect.clicked.connect(controller.auto_detect_tables)
        self.cmb_year.currentIndexChanged.connect(controller.date_changed)
        self.cmb_month.currentIndexChanged.connect(controller.date_changed)
        self.cmb_day.currentIndexChanged.connect(controller.date_changed)
        self.cmb_small_type.currentTextChanged.connect(controller.small_type_changed)
        self.btn_small_template.clicked.connect(controller.pick_small_template)
        self.btn_output_dir.clicked.connect(controller.pick_output_dir)
        self.btn_clear.clicked.connect(controller.clear_inputs)
        self.btn_run.clicked.connect(controller.run_transfer)
        self.btn_check_dup.clicked.connect(controller.check_duplicates)
        self.txt_veg.textChanged.connect(controller.validate_veg)

    # 以下方法用于控制器更新视图
    def update_veg_status(self, message: str):
        self.lbl_veg_status.setText(message)

    def set_veg_text(self, text: str):
        self.txt_veg.setPlainText(text)

    def get_veg_text(self) -> str:
        return self.txt_veg.toPlainText()

    def get_big_folder_path(self) -> str:
        return self.lbl_big_folder.text() if self.lbl_big_folder.text() != "未设置" else ""

    def get_small_type(self) -> str:
        return self.cmb_small_type.currentText()

    def get_small_template_path(self) -> str:
        return self.lbl_small_template.text() if self.lbl_small_template.text() != "未选择" else ""

    def get_output_dir(self) -> str:
        return self.lbl_output_dir.text() if self.lbl_output_dir.text() != "未选择" else ""

    def set_big_file_path(self, path: str):
        self.lbl_big_file.setText(path or "未选择")
        self.config["big_table_path"] = path
        save_config(self.config)

    def set_small_template_path(self, path: str):
        small_type = self.get_small_type()
        templates = self.config.get("small_templates", {})
        templates[small_type] = path
        self.config["small_templates"] = templates
        save_config(self.config)
        self._update_small_template_label()

    def set_output_dir(self, path: str):
        self.lbl_output_dir.setText(path or "未选择")
        self.config["output_dir"] = path
        save_config(self.config)

    def append_status(self, message: str):
        """追加状态消息"""
        self.txt_status.appendPlainText(message)

    def clear_status(self):
        """清除状态"""
        self.txt_status.clear()

    def show_message(self, title: str, message: str, icon=QMessageBox.Warning):
        QMessageBox(icon, title, message, QMessageBox.Ok, self).exec()

    # 新增方法
    def set_big_folder_path(self, path: str):
        """设置大表文件夹路径显示"""
        self.lbl_big_folder.setText(path or "未设置")
        # 更新按钮文本显示当前路径
        if path:
            self.btn_big_folder.setToolTip(path)

    def set_detected_tables(self, tables: list):
        """设置检测到的大表文件列表显示"""
        if not tables:
            self.lbl_detected_tables.setText("未检测到大表文件")
            return
        
        # 显示检测到的文件列表
        text = f"检测到 {len(tables)} 个大表文件:\n"
        for i, table_path in enumerate(tables[:3]):  # 最多显示3个
            filename = os.path.basename(table_path)
            text += f"  {i+1}. {filename}\n"
        if len(tables) > 3:
            text += f"  ... 还有 {len(tables)-3} 个文件"
        
        self.lbl_detected_tables.setText(text.strip())

    def get_date_components(self) -> tuple:
        """获取日期组件（年、月、日）"""
        return (
            self.cmb_year.currentText(),
            self.cmb_month.currentText(),
            self.cmb_day.currentText(),
        )

    def save_date_to_config(self):
        """保存当前日期到配置"""
        y, m, d = self.get_date_components()
        date_str = f"{y}-{m}-{d}"
        self.config["data_transfer_last_date"] = date_str
        save_config(self.config)

    def set_variety_preview(self, varieties: list):
        """设置大表品种预览列表"""
        self._variety_list = varieties
        if not varieties:
            self.lbl_preview_info.setText("未加载")
            self.preview_browser.clear()
            return
        # 初始全部默认色
        parts = [f'<span style="color:#333">{v}</span>' for v in varieties]
        self.preview_browser.setHtml(" 、 ".join(parts))
        self.lbl_preview_info.setText(f"共 {len(varieties)} 个品种")

    def update_preview_colors(self, matched_lower_set: set, aliases_map: dict):
        """
        根据匹配集合更新预览文字颜色。

        Args:
            matched_lower_set: 用户输入菜名的 lower() 集合
            aliases_map: {主名lower: [别名lower, ...]} 的映射
        """
        if not hasattr(self, '_variety_list') or not self._variety_list:
            return

        # 反向构建: 每个名称 -> 同义词组集合
        name_to_group = {}
        for main_name, alias_list in aliases_map.items():
            group = {main_name} | set(alias_list)
            for name in group:
                if name not in name_to_group:
                    name_to_group[name] = group

        matched_count = 0
        parts = []
        for variety in self._variety_list:
            variety_lower = variety.strip().lower()
            is_matched = variety_lower in matched_lower_set

            if not is_matched and variety_lower in name_to_group:
                related = name_to_group[variety_lower]
                is_matched = bool(related & matched_lower_set)

            if is_matched:
                parts.append(f'<span style="color:#006400;font-weight:bold">{variety}</span>')
                matched_count += 1
            else:
                parts.append(f'<span style="color:#333">{variety}</span>')

        self.preview_browser.setHtml(" 、 ".join(parts))
        total = len(self._variety_list)
        self.lbl_preview_info.setText(f"共 {total} 个品种，已匹配 {matched_count} 个")