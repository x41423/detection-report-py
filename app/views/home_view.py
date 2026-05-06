from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QSizePolicy,
    QSpacerItem,
)

try:
    import qtawesome as qta
except Exception:
    qta = None


class HomePage(QWidget):
    # 信号：点击农残检测卡片
    pesticide_clicked = Signal()
    # 信号：点击数据迁移卡片
    data_transfer_clicked = Signal()
    weekly_price_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._apply_icons()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(30)

        # 标题
        title_label = QLabel("滨鲜检测工具集")
        title_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #333;")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # 副标题
        subtitle_label = QLabel("请选择要使用的功能")
        subtitle_label.setStyleSheet("font-size: 16px; color: #666;")
        subtitle_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(subtitle_label)

        main_layout.addSpacing(20)

        # 卡片容器
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(30)

        # 卡片1：农残检测报告生成
        self.card_pesticide = self._create_card(
            icon_name="mdi.file-document",
            title="农残检测报告生成",
            description="生成蔬菜农药残留检测报告\n支持自动填充抑制率数据",
            callback=self.pesticide_clicked.emit
        )
        cards_layout.addWidget(self.card_pesticide)

        # 卡片2：大表数据写入小表
        self.card_data_transfer = self._create_card(
            icon_name="mdi.table-arrow-right",
            title="大表数据写入小表",
            description="从大表中提取指定菜名数据\n写入小表模板",
            callback=self.data_transfer_clicked.emit
        )
        cards_layout.addWidget(self.card_data_transfer)

        # 新增卡片：周报价录入（后续接入控制器）
        # 仅创建一次，确保不会重复创建
        self.card_weekly = self._create_card(
            icon_name="mdi.currency-usd",
            title="周报价录入",
            description="从两张表更新本周报价（Phase 1 任务）",
            callback=self.weekly_price_clicked.emit,
        )
        cards_layout.addWidget(self.card_weekly)

        # 可以在这里添加更多卡片
        # 预留空间
        cards_layout.addStretch()

        main_layout.addLayout(cards_layout)
        main_layout.addStretch()

    def _create_card(self, icon_name: str, title: str, description: str, callback) -> QPushButton:
        """创建卡片按钮"""
        card = QPushButton()
        card.setCursor(Qt.PointingHandCursor)
        card.setMinimumSize(280, 200)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 检测当前主题模式
        is_dark = False
        try:
            palette = QApplication.instance().palette()
            is_dark = palette.window().color().value() < 128
        except Exception:
            pass

        # 根据主题模式设置颜色
        if is_dark:
            icon_color = "#26C6DA"  # cyan 400
            title_color = "#E8EAED"
            desc_color = "#9AA0A6"
            card_bg = "rgba(32, 33, 36, 0.92)"
            card_border = "rgba(255, 255, 255, 0.12)"
            hover_border = "#26C6DA"
            hover_bg = "rgba(38, 198, 218, 0.08)"
            pressed_bg = "rgba(38, 198, 218, 0.16)"
        else:
            icon_color = "#00BCD4"  # cyan 500
            title_color = "#202124"
            desc_color = "#5F6368"
            card_bg = "rgba(255, 255, 255, 0.95)"
            card_border = "rgba(0, 0, 0, 0.12)"
            hover_border = "#00BCD4"
            hover_bg = "rgba(0, 188, 212, 0.08)"
            pressed_bg = "rgba(0, 188, 212, 0.16)"

        # 卡片内部布局
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 图标
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet(f"font-size: 48px; color: {icon_color};")
        # 图标将在_apply_icons中设置
        icon_label.setObjectName(f"icon_{icon_name}")
        layout.addWidget(icon_label)

        # 标题
        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {title_color};")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # 描述
        desc_label = QLabel(description)
        desc_label.setStyleSheet(f"font-size: 14px; color: {desc_color};")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # 连接点击信号
        card.clicked.connect(callback)

        # 卡片样式
        card.setStyleSheet(f"""
            QPushButton {{
                background-color: {card_bg};
                border: 2px solid {card_border};
                border-radius: 12px;
                text-align: center;
                padding: 10px;
            }}
            QPushButton:hover {{
                border-color: {hover_border};
                background-color: {hover_bg};
            }}
            QPushButton:pressed {{
                background-color: {pressed_bg};
            }}
        """)

        return card

    def _apply_icons(self):
        """应用图标"""
        if qta is None:
            return

        # 检测当前主题模式
        is_dark = False
        try:
            palette = QApplication.instance().palette()
            is_dark = palette.window().color().value() < 128
        except Exception:
            pass

        # 根据主题模式设置图标颜色
        if is_dark:
            icon_color = "#26C6DA"  # cyan 400
        else:
            icon_color = "#00BCD4"  # cyan 500

        def safe_icon(name: str, color: str = icon_color):
            try:
                return qta.icon(name, color=color)
            except Exception:
                return QIcon()

        # 为每个卡片设置图标
        for card, icon_name in [
            (self.card_pesticide, "mdi.file-document"),
            (self.card_data_transfer, "mdi.table-arrow-right"),
        ]:
            icon_label = card.findChild(QLabel, f"icon_{icon_name}")
            if icon_label:
                pixmap = safe_icon(icon_name).pixmap(QSize(48, 48))
                icon_label.setPixmap(pixmap)

    def reload_config(self):
        """重新加载配置（预留）"""
        pass
