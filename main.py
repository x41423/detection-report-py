import sys
import logging
from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtWidgets import QApplication

try:
    from qt_material import apply_stylesheet
except Exception:
    apply_stylesheet = None

from app.views.main_window import MainWindow
from app.views.home_view import HomePage
from app.views.pesticide_view import PesticideView
from app.views.data_transfer_view import DataTransferView
from app.views.weekly_price_view import WeeklyPriceView
from app.controllers.pesticide_controller import PesticideController
from app.controllers.data_transfer_controller import DataTransferController
from app.controllers.weekly_price_controller import WeeklyPriceController


def main():
    # 高DPI缩放在PySide6中默认启用，无需手动设置

    app = QApplication(sys.argv)
    # 初始化本地数据库（SQLite）并进行初步迁移（若需要）
    try:
        from app.db import init_database
        init_database()
    except Exception as db_ex:
        logging.getLogger(__name__).warning(f"数据库初始化失败：{db_ex}")
    try:
        from app.db.migration import migrate_json_to_db
        migrate_json_to_db()
    except Exception as mig_ex:
        logging.getLogger(__name__).info(
            f"数据迁移检查未执行或失败（如首次运行）: {mig_ex}"
        )

    # 触发周价录入模块的初始化钩子（若未来集成 UI 按钮，可以在此注册）

    # 应用Material主题（如果可用）
    if apply_stylesheet is not None:
        try:
            apply_stylesheet(app, theme="light_cyan.xml")
        except Exception:
            pass

    # 创建主窗口
    main_window = MainWindow()

    # 创建各个页面
    home_page = HomePage()
    pesticide_page = PesticideView()
    data_transfer_page = DataTransferView()
    weekly_price_page = WeeklyPriceView()

    # 创建控制器
    pesticide_controller = PesticideController(pesticide_page)
    data_transfer_controller = DataTransferController(data_transfer_page)
    weekly_price_controller = WeeklyPriceController(weekly_price_page)

    # 设置页面引用（新增周价页面）
    main_window.set_pages(home_page, pesticide_page, data_transfer_page, weekly_price_page)
    
    # 设置控制器引用（用于浮动按钮事件）
    main_window.set_controllers(pesticide_controller, data_transfer_controller, weekly_price_controller)
    # 将周价视图绑定控制器
    weekly_price_page.set_controller(weekly_price_controller)

    # 连接主页信号到页面切换
    home_page.pesticide_clicked.connect(lambda: main_window.switch_to(pesticide_page))
    home_page.data_transfer_clicked.connect(lambda: main_window.switch_to(data_transfer_page))
    home_page.weekly_price_clicked.connect(lambda: main_window.switch_to(weekly_price_page))

    # 连接主窗口的返回主页信号
    main_window.switch_to_home.connect(lambda: main_window.switch_to(home_page))

    # 显示主窗口
    main_window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
