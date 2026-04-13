# ui/screens/person_list_screen.py
"""
人物一覧画面 — スタンドアロン版（バックエンド依存なし）
"""
from typing import Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QFrame,
    QGridLayout,
)
from PySide6.QtCore import Qt, Signal


class _SquareBlackFrame(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        base_w = 160
        w = int(round(base_w * 2 / 5))
        h = int(round(w * 4 / 3))
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setMinimumWidth(w)
        self.setMaximumWidth(w)
        self.setMinimumHeight(h)
        self.setMaximumHeight(h)
        self.setStyleSheet(
            """
            QFrame {
                background-color: #000000;
                border: 1px solid #333333;
            }
            """
        )


class PersonListScreen(QWidget):
    """人物一覧画面。"""

    back_requested = Signal()
    search_requested = Signal()
    person_selected = Signal(str, str, object)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._sidebar_open: bool = True
        self._results_layout: Optional[QGridLayout] = None
        self._selected_index: Optional[int] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setObjectName("person-list-screen")

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(12)

        # パンくず
        breadcrumb_row = QHBoxLayout()
        breadcrumb_row.setContentsMargins(0, 0, 0, 0)
        breadcrumb_row.setSpacing(4)

        self.back_button = QPushButton("戻る", self)
        self.back_button.setFlat(True)
        self.back_button.setCursor(Qt.PointingHandCursor)
        self.back_button.setStyleSheet(
            """
            QPushButton {
                border: none; background: transparent;
                color: #0078d4; font-size: 18px; font-weight: bold;
                text-decoration: underline;
            }
            QPushButton:hover { color: #005a9e; }
            """
        )
        self.back_button.clicked.connect(self.back_requested.emit)

        arrow_label = QLabel(">", self)
        arrow_label.setStyleSheet("font-size: 16px; color: #444444;")

        self.title_label = QLabel("人物一覧", self)
        self.title_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: black;"
        )

        breadcrumb_row.addWidget(self.back_button)
        breadcrumb_row.addWidget(arrow_label)
        breadcrumb_row.addWidget(self.title_label)
        breadcrumb_row.addStretch(1)

        root_layout.addLayout(breadcrumb_row)

        # グリッド領域
        grid_widget = QWidget(self)
        self._results_layout = QGridLayout(grid_widget)
        self._results_layout.setContentsMargins(0, 0, 0, 0)
        self._results_layout.setSpacing(12)

        # プレースホルダー
        placeholder = QLabel("人物一覧はここに表示されます", grid_widget)
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("color: #999999; font-size: 16px; padding: 40px;")
        self._results_layout.addWidget(placeholder, 0, 0)

        root_layout.addWidget(grid_widget, 1)
