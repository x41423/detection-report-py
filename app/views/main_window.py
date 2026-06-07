import os
import sys
import logging
from PySide6.QtCore import Qt, QCoreApplication, QSize, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QStackedWidget,
    QToolBar,
    QStatusBar,
    QLabel,
    QComboBox,
    QMessageBox,
    QFileDialog,
    QPushButton,
)

try:
    import qtawesome as qta
except Exception:
    qta = None

try:
    from qt_material import apply_stylesheet
except Exception:
    apply_stylesheet = None

from app.models.config_model import load_config, save_config
from shared.logging_utils import configure_application_logging


class MainWindow(QMainWindow):
    # 信号：切换到主页
    switch_to_home = Signal()
    # 信号：切换到农残检测页面
    switch_to_pesticide = Signal()
    # 信号：切换到数据迁移页面
    switch_to_data_transfer = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("滨鲜检测工具集")
        self.resize(1200, 900)
        configure_application_logging("desktop.log")

        # 初始化日志
        configure_application_logging("desktop.log")
        logging.info("主窗口启动")

        # 加载配置
        self.config = load_config()
        self.current_theme = self.config.get("ui_theme", "light_cyan.xml")

        # 创建堆栈窗口部件
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # 构建UI
        self._build_actions()
        self._build_toolbar()
        self._build_statusbar()

        # 应用主题
        self._apply_theme(self.current_theme)
        self._apply_material_icons()

        # 页面引用（将由外部设置）
        self.home_page = None
        self.pesticide_page = None
        self.data_transfer_page = None
        self.weekly_price_page = None
        self.weekly_price_controller = None

        # 浮动按钮
        self.fab = None
        self._init_fab()
        
        # 控制器引用（将由外部设置）
        self.pesticide_controller = None
        self.data_transfer_controller = None
        
        # 当前页面标识
        self.current_page = None
        
        # 创建浮动操作按钮
        self._build_fab()

    def _build_fab(self):
        """创建浮动操作按钮"""
        self.fab = QPushButton(self)
        self.fab.setObjectName("fab")
        self.fab.setFixedSize(56, 56)
        self.fab.setToolTip("执行当前任务")
        self.fab.clicked.connect(self._on_fab_clicked)
        self.fab.hide()  # 默认隐藏，只在子页面显示
        
        # 应用浮动按钮样式
        self._apply_fab_style()

    def _apply_fab_style(self):
        """应用浮动按钮样式"""
        self.fab.setStyleSheet("""
            QPushButton#fab {
                border-radius: 28px;
                font-weight: 700;
                font-size: 18px;
                background: #00BCD4;
                color: white;
                border: none;
            }
            QPushButton#fab:hover {
                background: #0097A7;
            }
            QPushButton#fab:pressed {
                background: #00838F;
            }
        """)

    def _on_fab_clicked(self):
        """浮动按钮点击事件处理"""
        if self.current_page == self.pesticide_page and self.pesticide_controller:
            self.pesticide_controller.run_task()
        elif self.current_page == self.data_transfer_page and self.data_transfer_controller:
            self.data_transfer_controller.run_transfer()
        elif getattr(self, 'weekly_price_page', None) is not None and self.current_page == self.weekly_price_page:
            if self.weekly_price_controller:
                self.weekly_price_controller.run_update()

    def resizeEvent(self, event):
        """窗口大小变化时重新定位浮动按钮"""
        super().resizeEvent(event)
        if hasattr(self, 'fab'):
            margin = 24
            x = self.width() - self.fab.width() - margin
            y = self.height() - self.fab.height() - margin
            self.fab.move(x, y)

    def _build_actions(self):
        self.act_open_output = QAction("打开输出目录", self)
        self.act_open_output.triggered.connect(self.open_output_dir)

        self.act_reload_config = QAction("重新加载配置", self)
        self.act_reload_config.triggered.connect(self.reload_config)

        self.act_back_home = QAction("返回主页", self)
        self.act_back_home.triggered.connect(self._on_back_home)

    def _build_toolbar(self):
        tb = QToolBar("主工具栏")
        tb.setMovable(False)
        self.addToolBar(tb)

        tb.addAction(self.act_back_home)
        tb.addSeparator()
        tb.addAction(self.act_open_output)
        tb.addSeparator()

        # 主题选择器
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

    def _build_statusbar(self):
        self.statusBar().showMessage("就绪", 5000)

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
        # 可以添加自定义样式
        pass

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

        # 设置动作图标
        self.act_open_output.setIcon(safe_icon("mdi.folder-open-outline", icon_color))
        self.act_reload_config.setIcon(safe_icon("mdi.refresh", icon_color))
        self.act_back_home.setIcon(safe_icon("mdi.home", icon_color))

    def set_pages(self, home_page, pesticide_page, data_transfer_page, weekly_price_page=None):
        """设置堆栈中的页面"""
        self.home_page = home_page
        self.pesticide_page = pesticide_page
        self.data_transfer_page = data_transfer_page
        self.weekly_price_page = weekly_price_page

        self.stacked_widget.addWidget(home_page)
        self.stacked_widget.addWidget(pesticide_page)
        self.stacked_widget.addWidget(data_transfer_page)
        if weekly_price_page is not None:
            self.stacked_widget.addWidget(weekly_price_page)

        # 默认显示主页
        self.stacked_widget.setCurrentWidget(home_page)

    def set_controllers(self, pesticide_controller, data_transfer_controller, weekly_price_controller=None):
        """设置控制器引用"""
        self.pesticide_controller = pesticide_controller
        self.data_transfer_controller = data_transfer_controller
        self.weekly_price_controller = weekly_price_controller

    def switch_to(self, page_widget):
        """切换到指定页面"""
        if page_widget in [self.home_page, self.pesticide_page, self.data_transfer_page, getattr(self, 'weekly_price_page', None)]:
            self.stacked_widget.setCurrentWidget(page_widget)
            self.current_page = page_widget
            
            # 更新状态栏和浮动按钮
            if page_widget == self.home_page:
                self.statusBar().showMessage("主页", 3000)
                self.fab.hide()
            elif page_widget == self.pesticide_page:
                self.statusBar().showMessage("农残检测报告生成", 3000)
                self._update_fab_for_pesticide()
                self.fab.show()
            elif page_widget == self.data_transfer_page:
                self.statusBar().showMessage("大表数据写入小表", 3000)
                self._update_fab_for_data_transfer()
                self.fab.show()
            elif page_widget == getattr(self, 'weekly_price_page', None):
                self.statusBar().showMessage("周报价录入", 3000)
                if self.weekly_price_controller and hasattr(self.weekly_price_controller, 'run_update'):
                    self.fab.setVisible(True)
                else:
                    self.fab.hide()
            elif page_widget == getattr(self, 'weekly_price_page', None):
                self.statusBar().showMessage("周报价录入", 3000)
                self.fab.show()

    def _update_fab_for_pesticide(self):
        """更新浮动按钮为农药残留检测功能"""
        self.fab.setToolTip("开启任务（排版保护）")
        if qta:
            try:
                icon_color = "#FFFFFF"
                self.fab.setIcon(qta.icon("mdi.rocket-launch", color=icon_color))
            except Exception:
                self.fab.setText("▶")
        else:
            self.fab.setText("▶")

    def _update_fab_for_data_transfer(self):
        """更新浮动按钮为数据迁移功能"""
        self.fab.setToolTip("开始提取并写入")
        if qta:
            try:
                icon_color = "#FFFFFF"
                self.fab.setIcon(qta.icon("mdi.play", color=icon_color))
            except Exception:
                self.fab.setText("▶")
        else:
            self.fab.setText("▶")

    def _on_back_home(self):
        """返回主页"""
        self.switch_to_home.emit()
        self.switch_to(self.home_page)

    def open_output_dir(self):
        output_dir = self.config.get("output_dir", "")
        if not output_dir or not os.path.isdir(output_dir):
            QMessageBox.information(self, "提示", "输出目录未设置或无效。")
            return
        try:
            os.startfile(output_dir)
        except Exception as e:
            QMessageBox.warning(self, "打开失败", str(e))

    def reload_config(self):
        self.config = load_config()
        self.current_theme = self.config.get("ui_theme", self.current_theme)
        self.theme_selector.setCurrentText(self.current_theme)
        self._apply_theme(self.current_theme)
        self.statusBar().showMessage("配置已重新加载", 3000)
        # 通知子页面重新加载配置
        if self.pesticide_page:
            self.pesticide_page.reload_config()
        if self.data_transfer_page:
            self.data_transfer_page.reload_config()

    def change_theme(self, theme_name: str):
        self.current_theme = theme_name
        self.config["ui_theme"] = theme_name
        save_config(self.config)
        self._apply_theme(theme_name)
        self.statusBar().showMessage(f"已切换主题：{theme_name}", 3000)

    def update_status(self, message: str, timeout: int = 5000):
        """更新状态栏消息"""
        self.statusBar().showMessage(message, timeout)

    def closeEvent(self, event):
        """关闭窗口时保存配置"""
        save_config(self.config)
        super().closeEvent(event)
