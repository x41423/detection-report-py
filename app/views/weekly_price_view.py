from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

try:
    import qtawesome as qta
except Exception:
    qta = None


class WeeklyPriceView(QWidget):
    run_requested = Signal()

    def __init__(self, parent=None, config=None):
        super().__init__(parent)
        self.config = config or {}
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        left = QGroupBox("1. 选择文件")
        left_layout = QVBoxLayout(left)

        self.btn_update_file = QPushButton("选择待更新表（Excel）")
        self.lbl_update_path = QLabel("未选择")
        self.btn_ref_file = QPushButton("选择参考表（Excel）")
        self.lbl_ref_path = QLabel("未选择")
        self.btn_output_file = QPushButton("选择输出文件")
        self.lbl_output_path = QLabel("未选择")

        for label in (self.lbl_update_path, self.lbl_ref_path, self.lbl_output_path):
            label.setWordWrap(True)
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        left_layout.addWidget(self.btn_update_file)
        left_layout.addWidget(self.lbl_update_path)
        left_layout.addWidget(self.btn_ref_file)
        left_layout.addWidget(self.lbl_ref_path)
        left_layout.addWidget(self.btn_output_file)
        left_layout.addWidget(self.lbl_output_path)
        left.setLayout(left_layout)

        right = QGroupBox("2. 结果与日志")
        right_layout = QVBoxLayout(right)
        self.txt_status = QPlainTextEdit()
        self.txt_status.setReadOnly(True)
        right_layout.addWidget(self.txt_status)
        right.setLayout(right_layout)

        main = QHBoxLayout()
        main.addWidget(left, 2)
        main.addWidget(right, 1)
        root.addLayout(main)

        self.btn_run = QPushButton("执行更新")
        root.addWidget(self.btn_run, alignment=Qt.AlignRight)

        self._apply_material_icons()

    def _apply_material_icons(self):
        if qta is None:
            return
        try:
            file_icon = qta.icon("mdi.file-document")
            save_icon = qta.icon("mdi.content-save-outline")
            self.btn_update_file.setIcon(file_icon)
            self.btn_ref_file.setIcon(file_icon)
            self.btn_output_file.setIcon(save_icon)
        except Exception:
            pass

    def set_controller(self, controller):
        self.view_controller = controller
        self.btn_update_file.clicked.connect(controller.pick_update_file)
        self.btn_ref_file.clicked.connect(controller.pick_reference_file)
        self.btn_output_file.clicked.connect(controller.pick_output_file)
        self.btn_run.clicked.connect(controller.run_update)

    def get_update_path(self) -> str:
        return self.lbl_update_path.text() if self.lbl_update_path.text() != "未选择" else ""

    def get_reference_path(self) -> str:
        return self.lbl_ref_path.text() if self.lbl_ref_path.text() != "未选择" else ""

    def get_output_path(self) -> str:
        return self.lbl_output_path.text() if self.lbl_output_path.text() != "未选择" else ""

    def set_update_path(self, path: str):
        self.lbl_update_path.setText(path or "未选择")

    def set_reference_path(self, path: str):
        self.lbl_ref_path.setText(path or "未选择")

    def set_output_path(self, path: str):
        self.lbl_output_path.setText(path or "未选择")

    def update_status(self, message: str):
        self.txt_status.appendPlainText(message)
