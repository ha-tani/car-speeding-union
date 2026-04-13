# ui/dialogs/person_search_dialog.py
"""
人物検索ダイアログ — スタブ版（バックエンド依存なし）
"""
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
)
from PySide6.QtCore import Qt, Signal


class PersonSearchDialog(QDialog):
    """人物検索ダイアログ（スタブ）。"""

    search_requested = Signal(str, str, str, str, list)

    def __init__(self, parent=None, **kwargs) -> None:
        super().__init__(parent)
        self.setWindowTitle("人物検索")
        self.setModal(True)
        self.resize(400, 200)

        layout = QVBoxLayout(self)
        label = QLabel("人物検索ダイアログ（スタブ）", self)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        close_btn = QPushButton("閉じる", self)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
