import os
import logging
from datetime import datetime
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
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
    QListView,
    QMessageBox,
    QFileDialog,
    QScrollArea,
    QFrame,
)

try:
    import qtawesome as qta
except Exception:
    qta = None

from app.models.config_model import load_config, save_config


class PesticideView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = load_config()
        self.veg_placeholder = "例如: 白菜,菠菜,生菜"
        self._build_ui()
        self._set_today()
        self._refresh_paths_ui()
        self._apply_material_icons()

    def _build_ui(self):
        # 主水平布局 - 左右两栏
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        # ===== 左栏 - 主要操作区域 =====
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        left_scroll.setMinimumWidth(400)
        
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(12)
        left_layout.setContentsMargins(0, 0, 8, 0)

        # 1) 路径卡片
        grp_paths = self._card_box("1. 路径锁定")
        paths = QGridLayout(grp_paths)
        paths.setColumnStretch(1, 1)

        self.btn_big = QPushButton("选择大表文件夹")
        self.btn_small = QPushButton("选择小表文件夹")
        self.btn_output = QPushButton("选择输出文件夹")

        self.lbl_big = QLabel("未设置")
        self.lbl_small = QLabel("未设置")
        self.lbl_output = QLabel("未设置")
        for lbl in (self.lbl_big, self.lbl_small, self.lbl_output):
            lbl.setWordWrap(True)
            lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)

        paths.addWidget(self.btn_big, 0, 0)
        paths.addWidget(self.lbl_big, 0, 1)
        paths.addWidget(self.btn_small, 1, 0)
        paths.addWidget(self.lbl_small, 1, 1)
        paths.addWidget(self.btn_output, 2, 0)
        paths.addWidget(self.lbl_output, 2, 1)

        # 2) 日期 + 检测人卡片
        grp_date = self._card_box("2. 检测日期")
        date = QHBoxLayout(grp_date)

        self.cmb_year = QComboBox()
        self.cmb_month = QComboBox()
        self.cmb_day = QComboBox()
        self.cmb_year.addItems(["2025", "2026", "2027"])
        self.cmb_month.addItems([f"{i:02d}" for i in range(1, 13)])
        self.cmb_day.addItems([f"{i:02d}" for i in range(1, 32)])

        for combo in (self.cmb_year, self.cmb_month, self.cmb_day):
            combo.setView(QListView())
            combo.view().setMinimumWidth(80)
            combo.setMinimumWidth(90)
            combo.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.lbl_year = QLabel("年")
        self.lbl_month = QLabel("月")
        self.lbl_day = QLabel("日")
        for lbl in (self.lbl_year, self.lbl_month, self.lbl_day):
            lbl.setMinimumWidth(20)

        date.addWidget(self.lbl_year)
        date.addWidget(self.cmb_year)
        date.addSpacing(8)
        date.addWidget(self.lbl_month)
        date.addWidget(self.cmb_month)
        date.addSpacing(8)
        date.addWidget(self.lbl_day)
        date.addWidget(self.cmb_day)
        date.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        date.addWidget(QLabel("核验员"))
        self.edt_inspector = QLineEdit()
        self.edt_inspector.setPlaceholderText("例如：朱林初")
        self.edt_inspector.setText(self.config.get("inspector_name", "朱林初"))
        self.edt_inspector.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        date.addWidget(self.edt_inspector, 1)

        # 3) 数据录入卡片
        grp_data = self._card_box("3. 数据录入")
        data = QVBoxLayout(grp_data)
        data.setSpacing(10)

        veg_row = QVBoxLayout()
        veg_row.addWidget(QLabel("蔬菜品种（逗号分隔或每行一个）"))
        self.txt_veg = QPlainTextEdit()
        self.txt_veg.setPlaceholderText(self.veg_placeholder)
        self.txt_veg.setMaximumHeight(90)
        veg_row.addWidget(self.txt_veg)
        self.lbl_veg_status = QLabel("")
        veg_row.addWidget(self.lbl_veg_status)
        data.addLayout(veg_row)

        btns = QHBoxLayout()
        self.btn_gen = QPushButton("自动生成抑制率")
        self.btn_dedup = QPushButton("查重并删除重复")
        self.btn_clear = QPushButton("清除输入")
        self.btn_import = QPushButton("导入文件")
        self.btn_format = QPushButton("自动格式化 JSON")

        btns.addWidget(self.btn_gen)
        btns.addWidget(self.btn_dedup)
        btns.addWidget(self.btn_clear)
        btns.addWidget(self.btn_import)
        btns.addWidget(self.btn_format)
        btns.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.lbl_count = QLabel("品种总数：0")
        btns.addWidget(self.lbl_count)
        data.addLayout(btns)

        json_row = QVBoxLayout()
        json_row.addWidget(QLabel("JSON 数据（自动生成或手动编辑）"))
        self.txt_json = QPlainTextEdit()
        self.txt_json.setMinimumHeight(220)
        json_row.addWidget(self.txt_json)
        self.lbl_json_status = QLabel("")
        json_row.addWidget(self.lbl_json_status)
        data.addLayout(json_row)

        # 添加到左栏
        left_layout.addWidget(grp_paths)
        left_layout.addWidget(grp_date)
        left_layout.addWidget(grp_data, 1)
        
        left_scroll.setWidget(left_widget)

        # ===== 右栏 - 辅助信息区域 =====
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(12)
        right_layout.setContentsMargins(8, 0, 0, 0)

        # 4) 操作卡片
        grp_ctrl = self._card_box("4. 操作")
        ctrl = QVBoxLayout(grp_ctrl)
        ctrl.setSpacing(10)
        
        self.btn_reset = QPushButton("重置数据")
        self.btn_run = QPushButton("开启任务（排版保护）")
        ctrl.addWidget(self.btn_reset)
        ctrl.addWidget(self.btn_run)

        # 5) 预览信息卡片
        grp_preview = self._card_box("预览信息")
        preview_layout = QVBoxLayout(grp_preview)
        preview_layout.setSpacing(8)
        
        self.lbl_preview_date = QLabel("日期：未设置")
        self.lbl_path_status = QLabel("路径：未验证")
        self.lbl_data_count = QLabel("数据：0 条")
        
        preview_layout.addWidget(self.lbl_preview_date)
        preview_layout.addWidget(self.lbl_path_status)
        preview_layout.addWidget(self.lbl_data_count)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        preview_layout.addWidget(line)
        
        # 使用提示
        tip_label = QLabel("提示：先设置路径和日期，再输入菜名生成数据")
        tip_label.setWordWrap(True)
        tip_label.setStyleSheet("color: #666; font-size: 11px;")
        preview_layout.addWidget(tip_label)
        preview_layout.addStretch()

        # 添加到右栏
        right_layout.addWidget(grp_ctrl)
        right_layout.addWidget(grp_preview, 1)

        # 设置比例 2:1
        main_layout.addWidget(left_scroll, 2)
        main_layout.addWidget(right_widget, 1)

        # 应用自定义样式
        self._apply_custom_styles()

    def _card_box(self, title: str) -> QGroupBox:
        box = QGroupBox(title)
        box.setObjectName("card")
        shadow = QGraphicsDropShadowEffect(blurRadius=24, xOffset=0, yOffset=6)
        shadow.setColor(Qt.black)
        box.setGraphicsEffect(shadow)
        return box

    def _apply_custom_styles(self):
        # 根据当前主题调整颜色
        app = QApplication.instance()
        is_dark = False
        if app is not None:
            palette = app.palette()
            is_dark = palette.window().color().value() < 128

        # 现代简洁风格颜色方案
        if is_dark:
            card_bg = "rgba(32, 33, 36, 0.92)"
            card_fg = "#E8EAED"
            fab_bg = "#26C6DA"  # cyan 400
            fab_hover = "#00BCD4"  # cyan 500
            fab_pressed = "#00ACC1"  # cyan 600
        else:
            card_bg = "rgba(255, 255, 255, 0.95)"
            card_fg = "#202124"
            fab_bg = "#00BCD4"  # cyan 500
            fab_hover = "#0097A7"  # cyan 700
            fab_pressed = "#00838F"  # cyan 800

        self.setStyleSheet(f"""
            QGroupBox#card {{
                border-radius: 12px;
                padding: 12px;
                margin-top: 8px;
                color: {card_fg};
                background: {card_bg};
            }}
            QGroupBox#card::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                font-weight: 600;
            }}
            QPushButton#fab {{
                border-radius: 28px;
                font-weight: 700;
                background: {fab_bg};
                color: white;
            }}
            QPushButton#fab:hover {{
                background: {fab_hover};
            }}
            QPushButton#fab:pressed {{
                background: {fab_pressed};
            }}
            QPushButton {{
                padding: 6px 12px;
            }}
            QPushButton::menu-indicator {{
                width: 0px;
            }}
        """)

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
        self.btn_big.setIcon(safe_icon("mdi.folder", icon_color))
        self.btn_small.setIcon(safe_icon("mdi.folder", icon_color))
        self.btn_output.setIcon(safe_icon("mdi.folder", icon_color))
        self.btn_gen.setIcon(safe_icon("mdi.auto-fix", icon_color))
        self.btn_dedup.setIcon(safe_icon("mdi.find-replace", icon_color))
        self.btn_clear.setIcon(safe_icon("mdi.eraser", icon_color))
        self.btn_import.setIcon(safe_icon("mdi.file-import", icon_color))
        self.btn_format.setIcon(safe_icon("mdi.code-json", icon_color))
        self.btn_reset.setIcon(safe_icon("mdi.refresh", icon_color))
        self.btn_run.setIcon(safe_icon("mdi.rocket-launch", icon_color))

        # 图标对齐
        buttons = [
            self.btn_big, self.btn_small, self.btn_output,
            self.btn_gen, self.btn_dedup, self.btn_clear,
            self.btn_import, self.btn_format, self.btn_reset, self.btn_run,
        ]
        for btn in buttons:
            btn.setIconSize(QSize(18, 18))
            btn.setMinimumHeight(34)

    def _set_today(self):
        t = datetime.now()
        self.cmb_year.setCurrentText(str(t.year))
        self.cmb_month.setCurrentText(f"{t.month:02d}")
        self._refresh_day_options()
        self.cmb_day.setCurrentText(f"{t.day:02d}")

    def _refresh_day_options(self):
        try:
            y = int(self.cmb_year.currentText())
            m = int(self.cmb_month.currentText())
        except Exception:
            return
        # 计算月份天数
        if m == 12:
            next_month = datetime(y + 1, 1, 1)
        else:
            next_month = datetime(y, m + 1, 1)
        last_day = (next_month - datetime.resolution).day
        current_day = self.cmb_day.currentText()

        self.cmb_day.blockSignals(True)
        self.cmb_day.clear()
        self.cmb_day.addItems([f"{i:02d}" for i in range(1, last_day + 1)])
        if current_day in [f"{i:02d}" for i in range(1, last_day + 1)]:
            self.cmb_day.setCurrentText(current_day)
        else:
            self.cmb_day.setCurrentIndex(last_day - 1)
        self.cmb_day.blockSignals(False)

    def _refresh_paths_ui(self):
        self.lbl_big.setText(self.config.get("big_path", "") or "未设置")
        self.lbl_small.setText(self.config.get("small_path", "") or "未设置")
        self.lbl_output.setText(self.config.get("output_dir", "") or "未设置")

    def _is_date_valid(self) -> bool:
        try:
            y = int(self.cmb_year.currentText())
            m = int(self.cmb_month.currentText())
            d = int(self.cmb_day.currentText())
            datetime(y, m, d)
            return True
        except Exception:
            return False

    def reload_config(self):
        self.config = load_config()
        self._refresh_paths_ui()
        self.edt_inspector.setText(self.config.get("inspector_name", "朱林初"))

    # 以下方法将由控制器连接信号
    # 这里只定义占位符，实际连接在控制器中
    def set_controller_connections(self, controller):
        """设置控制器连接的信号"""
        # 路径选择按钮
        self.btn_big.clicked.connect(controller.pick_big_dir)
        self.btn_small.clicked.connect(controller.pick_small_dir)
        self.btn_output.clicked.connect(controller.pick_output_dir)
        # 日期变化
        self.cmb_year.currentIndexChanged.connect(controller.validate_date)
        self.cmb_month.currentIndexChanged.connect(controller.validate_date)
        self.cmb_day.currentIndexChanged.connect(controller.validate_date)
        # 数据输入
        self.txt_veg.textChanged.connect(controller.validate_veg)
        self.txt_json.textChanged.connect(controller.validate_json)
        # 操作按钮
        self.btn_gen.clicked.connect(controller.generate_rates)
        self.btn_dedup.clicked.connect(controller.check_duplicates)
        self.btn_clear.clicked.connect(controller.clear_inputs)
        self.btn_import.clicked.connect(controller.import_from_file)
        self.btn_format.clicked.connect(controller.format_json)
        self.btn_reset.clicked.connect(controller.reset_form)
        self.btn_run.clicked.connect(controller.run_task)

    # 以下方法用于控制器更新视图
    def update_veg_status(self, message: str):
        self.lbl_veg_status.setText(message)

    def update_json_status(self, message: str):
        self.lbl_json_status.setText(message)

    def update_count_label(self, count: int):
        self.lbl_count.setText(f"品种总数：{count}")

    def set_veg_text(self, text: str):
        self.txt_veg.setPlainText(text)

    def set_json_text(self, text: str):
        self.txt_json.setPlainText(text)

    def get_veg_text(self) -> str:
        return self.txt_veg.toPlainText()

    def get_json_text(self) -> str:
        return self.txt_json.toPlainText()

    def get_date_components(self) -> tuple:
        return (
            self.cmb_year.currentText(),
            self.cmb_month.currentText(),
            self.cmb_day.currentText(),
        )

    def get_inspector_name(self) -> str:
        return self.edt_inspector.text().strip()

    def show_message(self, title: str, message: str, icon=QMessageBox.Warning):
        QMessageBox(icon, title, message, QMessageBox.Ok, self).exec()