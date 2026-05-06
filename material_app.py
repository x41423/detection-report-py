import os
import sys
import json
import logging
from datetime import datetime

from PySide6.QtCore import Qt, QCoreApplication, QSize
from PySide6.QtGui import QAction, QIcon

try:
    import qtawesome as qta
except Exception:  # pragma: no cover
    qta = None
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSizePolicy,
    QSpacerItem,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QGraphicsDropShadowEffect,
    QListView,
)

try:
    from qt_material import apply_stylesheet
except Exception:  # pragma: no cover
    apply_stylesheet = None

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
from shared.logging_utils import configure_application_logging


APP_TITLE = "滨鲜农残检测助手 V12.0 - Material Design"


class MaterialPesticideApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(980, 860)

        configure_application_logging("material-desktop.log")
        logging.info("程序启动 (Material UI)")

        self.config = load_config()
        self.path_big_root = self.config.get("big_path", "")
        self.path_small_root = self.config.get("small_path", "")
        self.path_output = self.config.get("output_dir", "")
        self.inspector_name = self.config.get("inspector_name", "朱林初")

        set_risk_lists(self.config.get("high_risk", []), self.config.get("low_risk", []))
        set_rate_ranges(self.config.get("rate_ranges", {}))

        self.veg_placeholder = "例如: 白菜,菠菜,生菜"
        self.current_theme = self.config.get("ui_theme", "light_blue.xml")

        self._build_actions()
        self._build_toolbar()
        self._build_ui()
        self._set_today()
        self._refresh_paths_ui()
        self._apply_theme(self.current_theme)
        self._apply_material_icons()
        self._apply_responsive_layout()
        self._update_status("就绪")

    # --------------------- UI BUILD ---------------------
    def _build_actions(self):
        self.act_open_output = QAction("打开输出目录", self)
        self.act_open_output.triggered.connect(self.open_output_dir)

        self.act_reload_config = QAction("重新加载配置", self)
        self.act_reload_config.triggered.connect(self.reload_config)

    def _build_toolbar(self):
        tb = QToolBar("Main")
        tb.setMovable(False)
        self.addToolBar(tb)
        tb.addAction(self.act_open_output)
        tb.addSeparator()

        theme_label = QLabel("主题")
        theme_label.setObjectName("toolbarLabel")
        self.theme_selector = QComboBox()
        self.theme_selector.addItems([
            "light_blue.xml",
            "light_cyan.xml",
            "light_teal.xml",
            "light_pink.xml",
            "dark_blue.xml",
            "dark_cyan.xml",
            "dark_teal.xml",
            "dark_pink.xml",
        ])
        self.theme_selector.setCurrentText(self.current_theme)
        self.theme_selector.currentTextChanged.connect(self.change_theme)
        self.theme_selector.setMinimumWidth(150)
        tb.addWidget(theme_label)
        tb.addWidget(self.theme_selector)

        tb.addSeparator()
        tb.addAction(self.act_reload_config)

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)

        main = QVBoxLayout(root)
        main.setContentsMargins(16, 16, 16, 16)
        main.setSpacing(14)

        # 1) Paths - Card
        grp_paths = self._card_box("1. 路径锁定（直接在选定目录下查找）")
        paths = QGridLayout(grp_paths)
        paths.setColumnStretch(1, 1)

        self.btn_big = QPushButton("选择大表文件夹")
        self.btn_small = QPushButton("选择小表文件夹")
        self.btn_output = QPushButton("选择输出文件夹")
        self.btn_big.clicked.connect(self.pick_big_dir)
        self.btn_small.clicked.connect(self.pick_small_dir)
        self.btn_output.clicked.connect(self.pick_output_dir)

        self.lbl_big = QLabel("未设置")
        self.lbl_small = QLabel("未设置")
        self.lbl_output = QLabel("未设置")
        self.lbl_big.setWordWrap(True)
        self.lbl_small.setWordWrap(True)
        self.lbl_output.setWordWrap(True)
        self.lbl_big.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_small.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_output.setTextInteractionFlags(Qt.TextSelectableByMouse)

        paths.addWidget(self.btn_big, 0, 0)
        paths.addWidget(self.lbl_big, 0, 1)
        paths.addWidget(self.btn_small, 1, 0)
        paths.addWidget(self.lbl_small, 1, 1)
        paths.addWidget(self.btn_output, 2, 0)
        paths.addWidget(self.lbl_output, 2, 1)

        # 2) Date + Inspector - Card
        grp_date = self._card_box("2. 检测日期")
        date = QHBoxLayout(grp_date)

        self.cmb_year = QComboBox()
        self.cmb_month = QComboBox()
        self.cmb_day = QComboBox()
        self.cmb_year.addItems(["2025", "2026", "2027"])
        self.cmb_month.addItems([f"{i:02d}" for i in range(1, 13)])
        self.cmb_day.addItems([f"{i:02d}" for i in range(1, 32)])
        self.cmb_year.currentIndexChanged.connect(self.validate_date)
        self.cmb_month.currentIndexChanged.connect(self.validate_date)
        self.cmb_day.currentIndexChanged.connect(self.validate_date)

        for combo in (self.cmb_year, self.cmb_month, self.cmb_day):
            combo.setView(QListView())
            combo.view().setMinimumWidth(80)
            combo.setMinimumWidth(90)
            combo.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.lbl_year = QLabel("年")
        self.lbl_month = QLabel("月")
        self.lbl_day = QLabel("日")
        self.lbl_year.setMinimumWidth(20)
        self.lbl_month.setMinimumWidth(20)
        self.lbl_day.setMinimumWidth(20)

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
        self.edt_inspector.setText(self.inspector_name)
        self.edt_inspector.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        date.addWidget(self.edt_inspector, 1)

        # 3) Data input - Card
        grp_data = self._card_box("3. 数据录入")
        data = QVBoxLayout(grp_data)
        data.setSpacing(10)

        veg_row = QVBoxLayout()
        veg_row.addWidget(QLabel("蔬菜品种（逗号分隔或每行一个）"))
        self.txt_veg = QPlainTextEdit()
        self.txt_veg.setPlaceholderText(self.veg_placeholder)
        self.txt_veg.textChanged.connect(self.validate_veg)
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

        self.btn_gen.clicked.connect(self.generate_rates)
        self.btn_dedup.clicked.connect(self.check_duplicates)
        self.btn_clear.clicked.connect(self.clear_inputs)
        self.btn_import.clicked.connect(self.import_from_file)
        self.btn_format.clicked.connect(self.format_json)

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
        self.txt_json.textChanged.connect(self.validate_json)
        self.txt_json.setMinimumHeight(220)
        json_row.addWidget(self.txt_json)
        self.lbl_json_status = QLabel("")
        json_row.addWidget(self.lbl_json_status)
        data.addLayout(json_row)

        # 4) Controls - Card
        grp_ctrl = self._card_box("4. 操作")
        ctrl = QHBoxLayout(grp_ctrl)

        self.btn_reset = QPushButton("重置数据")
        self.btn_run = QPushButton("开启任务（排版保护）")
        self.btn_reset.clicked.connect(self.reset_form)
        self.btn_run.clicked.connect(self.run_task)

        ctrl.addWidget(self.btn_reset)
        ctrl.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        ctrl.addWidget(self.btn_run)

        main.addWidget(grp_paths)
        main.addWidget(grp_date)
        main.addWidget(grp_data, 1)
        main.addWidget(grp_ctrl)

        # Floating Action Button (Run)
        self.fab = QPushButton("开始", root)
        self.fab.setObjectName("fab")
        self.fab.clicked.connect(self.run_task)
        self.fab.setFixedSize(56, 56)
        self.fab.raise_()

        sb = QStatusBar()
        self.setStatusBar(sb)

    # --------------------- Helpers ---------------------
    def _update_status(self, msg: str):
        self.statusBar().showMessage(msg, 8000)

    def _card_box(self, title: str) -> QGroupBox:
        box = QGroupBox(title)
        box.setObjectName("card")
        shadow = QGraphicsDropShadowEffect(blurRadius=24, xOffset=0, yOffset=6)
        shadow.setColor(Qt.black)
        box.setGraphicsEffect(shadow)
        return box

    def _open_dialog_safely(self, dialog):
        dialog.setWindowModality(Qt.ApplicationModal)
        dialog.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        dialog.adjustSize()
        if dialog.size().width() < 520:
            dialog.resize(520, dialog.size().height())
        return dialog

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Place FAB at bottom-right
        if hasattr(self, "fab"):
            margin = 24
            x = self.centralWidget().width() - self.fab.width() - margin
            y = self.centralWidget().height() - self.fab.height() - margin
            self.fab.move(x, y)

        # Ensure date combo widths remain usable on resize
        for combo in (getattr(self, "cmb_year", None), getattr(self, "cmb_month", None), getattr(self, "cmb_day", None)):
            if combo is not None:
                combo.setMinimumWidth(90)

    def _set_today(self):
        t = datetime.now()
        self.cmb_year.setCurrentText(str(t.year))
        self.cmb_month.setCurrentText(f"{t.month:02d}")
        self._refresh_day_options()
        self.cmb_day.setCurrentText(f"{t.day:02d}")

    def _refresh_paths_ui(self):
        self.lbl_big.setText(self.path_big_root or "未设置")
        self.lbl_small.setText(self.path_small_root or "未设置")
        self.lbl_output.setText(self.path_output or "未设置")

    def _is_date_valid(self) -> bool:
        try:
            y = int(self.cmb_year.currentText())
            m = int(self.cmb_month.currentText())
            d = int(self.cmb_day.currentText())
            datetime(y, m, d)
            return True
        except Exception:
            return False

    def validate_date(self):
        self._refresh_day_options()
        if self._is_date_valid():
            self._update_status("日期有效")
        else:
            self._update_status("日期无效，请重新选择")

    def _refresh_day_options(self):
        try:
            y = int(self.cmb_year.currentText())
            m = int(self.cmb_month.currentText())
        except Exception:
            return
        # Calculate days in month
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

    def validate_veg(self):
        raw = self.txt_veg.toPlainText().strip()
        if not raw:
            self.lbl_veg_status.setText("")
            return
        try:
            vegs = parse_vegetable_list(raw)
            self.lbl_veg_status.setText(f"有效：{len(vegs)} 个品种")
        except Exception as e:
            self.lbl_veg_status.setText(f"无效：{e}")

    def validate_json(self):
        raw = self.txt_json.toPlainText().strip()
        if not raw:
            self.lbl_json_status.setText("")
            self.lbl_count.setText("品种总数：0")
            return
        try:
            data = parse_json_data(raw)
            self.lbl_json_status.setText(f"有效：{len(data)} 条记录")
            self.lbl_count.setText(f"品种总数：{len(data)}")
        except Exception as e:
            self.lbl_json_status.setText(f"无效：{e}")

    def _get_target_files(self):
        y = self.cmb_year.currentText()
        m = self.cmb_month.currentText()
        d = self.cmb_day.currentText()
        d_int = int(d)
        big = os.path.join(self.path_big_root, f"农残检测记录表{y}.{m}.{d}.docx")
        small = os.path.join(self.path_small_root, f"单位农残记录表{m}.{d_int}.docx")
        return big, small

    def _ensure_paths_ok(self) -> bool:
        if not self._is_date_valid():
            QMessageBox.warning(self, "日期无效", "请选择有效日期后再执行。")
            return False

        if not self.path_big_root or not self.path_small_root or not self.path_output:
            QMessageBox.critical(self, "缺失", "请先设置大表、小表和输出文件夹路径。")
            return False

        if not os.path.isdir(self.path_big_root) or not os.path.isdir(self.path_small_root):
            QMessageBox.critical(self, "缺失", "大表或小表路径无效，请重新选择。")
            return False

        if not os.path.isdir(self.path_output):
            QMessageBox.critical(self, "缺失", "输出路径无效，请重新选择。")
            return False

        return True

    # --------------------- Actions ---------------------
    def pick_big_dir(self):
        dialog = QFileDialog(self, "选择大表文件夹")
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly, True)
        dialog.setDirectory(self.path_big_root or os.getcwd())
        dialog = self._open_dialog_safely(dialog)
        if dialog.exec():
            p = dialog.selectedFiles()[0]
            self.path_big_root = p
            self.config["big_path"] = p
            save_config(self.config)
            self._refresh_paths_ui()
            self._update_status("已更新大表路径")
            logging.info(f"大表路径设置为: {p}")

    def pick_small_dir(self):
        dialog = QFileDialog(self, "选择小表文件夹")
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly, True)
        dialog.setDirectory(self.path_small_root or os.getcwd())
        dialog = self._open_dialog_safely(dialog)
        if dialog.exec():
            p = dialog.selectedFiles()[0]
            self.path_small_root = p
            self.config["small_path"] = p
            save_config(self.config)
            self._refresh_paths_ui()
            self._update_status("已更新小表路径")
            logging.info(f"小表路径设置为: {p}")

    def pick_output_dir(self):
        dialog = QFileDialog(self, "选择输出文件夹")
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly, True)
        dialog.setDirectory(self.path_output or os.getcwd())
        dialog = self._open_dialog_safely(dialog)
        if dialog.exec():
            p = dialog.selectedFiles()[0]
            self.path_output = p
            self.config["output_dir"] = p
            save_config(self.config)
            self._refresh_paths_ui()
            self._update_status("已更新输出路径")
            logging.info(f"输出路径设置为: {p}")

    def open_output_dir(self):
        if not self.path_output or not os.path.isdir(self.path_output):
            QMessageBox.information(self, "提示", "输出目录未设置或无效。")
            return
        try:
            os.startfile(self.path_output)
        except Exception as e:
            QMessageBox.warning(self, "打开失败", str(e))

    def change_theme(self, theme_name: str):
        self.current_theme = theme_name
        self.config["ui_theme"] = theme_name
        save_config(self.config)
        self._apply_theme(theme_name)
        self._update_status(f"已切换主题：{theme_name}")

    def _apply_theme(self, theme_name: str):
        app = QApplication.instance()
        if apply_stylesheet is None or app is None:
            return
        try:
            apply_stylesheet(app, theme=theme_name)
            self._apply_custom_styles()
            self._apply_material_icons()
        except Exception:
            pass

    def _apply_custom_styles(self):
        app = QApplication.instance()
        is_dark = False
        if app is not None:
            palette = app.palette()
            is_dark = palette.window().color().value() < 128

        card_bg = "rgba(32, 33, 36, 0.92)" if is_dark else "rgba(255, 255, 255, 0.95)"
        card_fg = "#E8EAED" if is_dark else "#202124"
        fab_bg = "#8AB4F8" if is_dark else "#2962FF"
        fab_hover = "#6EA1F2" if is_dark else "#1E4ED8"
        fab_pressed = "#5B8AE5" if is_dark else "#153EAB"

        self.setStyleSheet(
            f"""
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
            """
        )

    def _apply_material_icons(self):
        if qta is None:
            return
        icon_color = "#FFFFFF"
        try:
            palette = QApplication.instance().palette()
            icon_color = "#E8EAED" if palette.window().color().value() < 128 else "#202124"
        except Exception:
            pass

        # Toolbar
        self.act_open_output.setIcon(qta.icon("mdi.folder-open", color=icon_color))
        self.act_reload_config.setIcon(qta.icon("mdi.refresh", color=icon_color))

        # Buttons
        self.btn_big.setIcon(qta.icon("mdi.folder", color=icon_color))
        self.btn_small.setIcon(qta.icon("mdi.folder", color=icon_color))
        self.btn_output.setIcon(qta.icon("mdi.folder", color=icon_color))

        self.btn_gen.setIcon(qta.icon("mdi.auto-fix", color=icon_color))
        self.btn_dedup.setIcon(qta.icon("mdi.find-replace", color=icon_color))
        self.btn_clear.setIcon(qta.icon("mdi.eraser", color=icon_color))
        self.btn_import.setIcon(qta.icon("mdi.file-import", color=icon_color))
        self.btn_format.setIcon(qta.icon("mdi.code-json", color=icon_color))

        self.btn_reset.setIcon(qta.icon("mdi.refresh", color=icon_color))
        self.btn_run.setIcon(qta.icon("mdi.rocket-launch", color=icon_color))

        # FAB
        self.fab.setIcon(qta.icon("mdi.play", color="#FFFFFF"))

        self._apply_icon_alignment()

    def _apply_icon_alignment(self):
        buttons = [
            self.btn_big,
            self.btn_small,
            self.btn_output,
            self.btn_gen,
            self.btn_dedup,
            self.btn_clear,
            self.btn_import,
            self.btn_format,
            self.btn_reset,
            self.btn_run,
        ]
        for btn in buttons:
            btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            btn.setIconSize(QSize(18, 18))
            btn.setMinimumHeight(34)

    def _apply_responsive_layout(self):
        # Ensure text wraps and controls expand on high DPI or small width
        self.lbl_big.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.lbl_small.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.lbl_output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.txt_json.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.txt_veg.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # Date controls fixed minimum widths to prevent clipping
        for combo in (self.cmb_year, self.cmb_month, self.cmb_day):
            combo.setMinimumWidth(90)

    def _open_dialog_safely(self, dialog):
        dialog.setWindowModality(Qt.ApplicationModal)
        dialog.setSizeGripEnabled(True)
        dialog.setMinimumSize(760, 520)
        dialog.adjustSize()
        return dialog


    def _apply_material_icons(self):
        if qta is None:
            return

        def safe_icon(name: str, color: str | None = None):
            try:
                return qta.icon(name, color=color) if color else qta.icon(name)
            except Exception:
                return QIcon()

        icon_color = None
        try:
            palette = QApplication.instance().palette()
            icon_color = "#E8EAED" if palette.window().color().value() < 128 else "#202124"
        except Exception:
            icon_color = None

        self.act_open_output.setIcon(safe_icon("mdi.folder-open-outline", icon_color))
        self.act_reload_config.setIcon(safe_icon("mdi.refresh", icon_color))
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
        self.fab.setIcon(safe_icon("mdi.play", "#FFFFFF"))
        self.fab.setText("")
    def reload_config(self):
        self.config = load_config()
        self.path_big_root = self.config.get("big_path", "")
        self.path_small_root = self.config.get("small_path", "")
        self.path_output = self.config.get("output_dir", "")
        self.inspector_name = self.config.get("inspector_name", "朱林初")
        self.current_theme = self.config.get("ui_theme", self.current_theme)

        set_risk_lists(self.config.get("high_risk", []), self.config.get("low_risk", []))
        set_rate_ranges(self.config.get("rate_ranges", {}))

        self.edt_inspector.setText(self.inspector_name)
        self.theme_selector.setCurrentText(self.current_theme)
        self._apply_theme(self.current_theme)
        self._refresh_paths_ui()
        self._update_status("配置已重新加载")

    def clear_inputs(self):
        self.txt_veg.clear()
        self.txt_json.clear()
        self.lbl_count.setText("品种总数：0")
        self.lbl_veg_status.setText("")
        self.lbl_json_status.setText("")
        self._update_status("已清除输入")

    def reset_form(self):
        self.clear_inputs()
        self._set_today()
        self._update_status("已重置")

    def import_from_file(self):
        dialog = QFileDialog(self, "导入品种文件")
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setNameFilter("Text files (*.txt);;All files (*.*)")
        dialog.setDirectory(os.getcwd())
        dialog = self._open_dialog_safely(dialog)
        if not dialog.exec():
            return
        file_path = dialog.selectedFiles()[0]
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            self.txt_veg.setPlainText(content)
            self._update_status("已导入文件")
            logging.info(f"从文件导入: {file_path}")
        except Exception as e:
            logging.error(f"导入失败: {e}")
            QMessageBox.critical(self, "错误", f"导入失败：{e}")

    def format_json(self):
        try:
            data = parse_json_data(self.txt_json.toPlainText())
            self.txt_json.setPlainText(format_json_data(data))
            self._update_status("JSON 已格式化")
        except Exception as e:
            QMessageBox.warning(self, "输入有误", str(e))

    def generate_rates(self):
        try:
            if not self._is_date_valid():
                QMessageBox.warning(self, "日期无效", "请选择有效日期后再生成抑制率。")
                return
            raw = self.txt_veg.toPlainText().strip()
            if not raw:
                QMessageBox.warning(self, "输入有误", "请输入蔬菜品种后再生成抑制率。")
                return

            vegs = parse_vegetable_list(raw)
            res = gen_inhibition_rates(vegs)
            self.txt_json.setPlainText(format_json_data(res))
            self.lbl_count.setText(f"品种总数：{len(res)}")
            self._update_status(f"抑制率已生成：{len(res)} 条")
            logging.info(f"生成抑制率成功: {len(res)} 个品种")
        except Exception as e:
            logging.error(f"生成抑制率失败: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"生成抑制率失败：{e}")

    def check_duplicates(self):
        try:
            data = parse_json_data(self.txt_json.toPlainText())
            unique_data, removed = remove_duplicate_varieties(data)
            self.txt_json.setPlainText(format_json_data(unique_data))
            self.lbl_count.setText(f"品种总数：{len(unique_data)}")
            self._update_status(f"已去重：删除 {removed} 条")
            logging.info(f"查重完成: 删除了 {removed} 个重复品种")
            QMessageBox.information(self, "查重完成", f"删除了 {removed} 个重复品种。")
        except Exception as e:
            logging.error(f"查重失败: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"查重失败：{e}")

    def run_task(self):
        if not self._ensure_paths_ok():
            return

        big, small = self._get_target_files()
        if not os.path.exists(big) or not os.path.exists(small):
            QMessageBox.critical(
                self,
                "缺失",
                f"文件不存在，请检查路径和日期是否匹配！\n\n大表: {big}\n小表: {small}",
            )
            logging.error(f"文件不存在: 大表={big}, 小表={small}")
            return

        try:
            data = parse_json_data(self.txt_json.toPlainText())
            if not data:
                QMessageBox.critical(self, "错误", "JSON 数据为空，请先生成或粘贴数据。")
                return

            date_label = self.config.get("date_format", "{y}年{m}月{d}日").format(
                y=self.cmb_year.currentText(),
                m=int(self.cmb_month.currentText()),
                d=int(self.cmb_day.currentText()),
            )
            inspector_name = self.edt_inspector.text().strip() or self.inspector_name

            process_documents(big, small, data, date_label, self.path_output, inspector_name)

            # 保存核验员为上次使用值
            if inspector_name != self.config.get("inspector_name"):
                self.config["inspector_name"] = inspector_name
                save_config(self.config)

            logging.info("任务成功完成")
            self._update_status("任务完成")

            dialog = QMessageBox(self)
            dialog.setWindowTitle("成功")
            dialog.setText("任务完成！日期和主检人已修改，排版保护已生效。\n\n是否打开输出目录？")
            dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            dialog.button(QMessageBox.Yes).setText("打开输出目录")
            dialog.button(QMessageBox.No).setText("关闭")
            self._open_dialog_safely(dialog)
            if dialog.exec() == QMessageBox.Yes:
                self.open_output_dir()
        except PermissionError:
            QMessageBox.critical(self, "错误", "输出文件被占用或没有权限，请关闭已打开的文档后重试。")
        except Exception as e:
            logging.error(f"任务失败: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"发生错误：{e}")


def main():
    QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    # Apply Material theme if available
    if apply_stylesheet is not None:
        try:
            apply_stylesheet(app, theme="light_blue.xml")
        except Exception:
            pass

    win = MaterialPesticideApp()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
