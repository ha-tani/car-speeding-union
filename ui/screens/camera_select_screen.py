# ui/screens/camera_select_screen.py
"""
カメラ選択画面 — スタンドアロン版（バックエンド依存なし）
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QSizePolicy,
    QFrame,
    QComboBox,
)
from PySide6.QtCore import Qt, Signal

from util import DateInputWithCalendar, populate_time_combo



class _SquareBlackFrame(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._sidebar_open: bool = True
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setFixedSize(200, 200)
        self.setStyleSheet(
            """
            QFrame {
                background-color: #000000;
                border: 1px solid #333333;
                border-radius: 0px;
            }
            """
        )


class CameraSelectScreen(QWidget):
    """カメラ選択画面。"""

    search_requested = Signal(str, str, str, str, str, str, list)
    person_select_requested = Signal(str, str)
    back_to_person_select_requested = Signal()
    video_play_requested = Signal(str, str, int)  # start_at, end_at, camera_id

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._face_label: Optional[QLabel] = None
        self.current_employee_id: str = ""
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setObjectName("camera-select-screen")

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        bg = QFrame(self)
        bg.setStyleSheet("background-color: #eeeeee;")
        root_layout.addWidget(bg)

        bg_layout = QVBoxLayout(bg)
        bg_layout.setContentsMargins(16, 16, 16, 16)
        bg_layout.addSpacing(12)
        bg_layout.addStretch(4)

        # カード
        card = QFrame(bg)
        card.setMinimumWidth(760)
        card.setStyleSheet(
            """
            QFrame {
                background-color: #ffffff;
                border: 1px solid #d0d0d0;
                border-radius: 10px;
            }
            """
        )

        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(24, 32, 32, 32)
        card_layout.setSpacing(40)

        # 入力エリア
        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)
        left_layout.addStretch(1)

        # ■カメラの設置場所
        self.camera_location_title = QLabel("■カメラの設置場所", card)
        cl_font = self.camera_location_title.font()
        cl_font.setPointSize(11)
        cl_font.setBold(True)
        self.camera_location_title.setFont(cl_font)
        self.camera_location_title.setStyleSheet("QLabel { background: transparent; border: none; font-size: 18px; }")
        left_layout.addWidget(self.camera_location_title, alignment=Qt.AlignLeft)
        left_layout.addSpacing(4)

        # 撮影日 + 開始時間 ～ 終了時間
        dt_row_widget = QWidget(card)
        dt_row_widget.setStyleSheet("background-color: #ffffff;")
        dt_row = QHBoxLayout(dt_row_widget)
        dt_row.setContentsMargins(0, 0, 0, 0)
        dt_row.setSpacing(8)

        self.date_input = DateInputWithCalendar(dt_row_widget)
        dt_row.addWidget(self.date_input)

        _combo_style = """
            QComboBox {
                font-size: 14px;
                background-color: #ffffff;
                color: #000000;
                padding: 4px 8px;
                border: 1px solid #c0c0c0;
                border-radius: 4px;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #000000;
                selection-background-color: #1E88E5;
                selection-color: #ffffff;
            }
        """

        self.start_combo = QComboBox(dt_row_widget)
        self.start_combo.setFixedWidth(120)
        self.start_combo.setFixedHeight(40)
        self.start_combo.setStyleSheet(_combo_style)
        populate_time_combo(self.start_combo)
        dt_row.addWidget(self.start_combo)

        time_label = QLabel("～", card)
        time_label.setStyleSheet("font-size: 12px; border: none; background: transparent;")
        dt_row.addWidget(time_label)

        self.end_combo = QComboBox(dt_row_widget)
        self.end_combo.setFixedWidth(120)
        self.end_combo.setFixedHeight(40)
        self.end_combo.setStyleSheet(_combo_style)
        populate_time_combo(self.end_combo)
        self.end_combo.setCurrentText("00:30")
        dt_row.addWidget(self.end_combo)

        dt_row.addStretch(1)
        left_layout.addWidget(dt_row_widget)

        left_layout.addSpacing(8)

        self.search_person_button = QPushButton("映像を確認する", card)
        self.search_person_button.setFixedSize(200, 36)
        self.search_person_button.setCursor(Qt.PointingHandCursor)
        self.search_person_button.setStyleSheet(
            """
            QPushButton {
                background-color: #1E88E5; color: #ffffff;
                border-radius: 4px; font-size: 14px;
            }
            QPushButton:hover { background-color: #1976D2; }
            QPushButton:disabled { background-color: #bdbdbd; color: #ffffff; }
            """
        )
        left_layout.addWidget(self.search_person_button, alignment=Qt.AlignLeft)
        left_layout.addStretch(1)

        self.search_person_button.clicked.connect(self._on_check_video_clicked)


        card_layout.addLayout(left_layout)

        bg_layout.addWidget(card, 0, Qt.AlignHCenter)
        bg_layout.addStretch(6)

    # --- helpers ---
    _CAMERA_ID_MAP: dict[str, int] = {"カメラA": 1, "カメラB": 2, "カメラC": 3}

    def _on_check_video_clicked(self) -> None:
        """「映像を確認する」ボタン押下：日時とカメラIDをシグナルで発火する。"""
        # 日付取得
        date = self.date_input.get_date()
        if date is None or not date.isValid():
            return
        date_str = date.toString("yyyy-MM-dd")  # "2026-04-08"

        # 開始時間取得（"HH:MM" → "HH:MM:00"）
        start_text = self.start_combo.currentText()  # e.g. "10:30"
        start_at = f"{date_str} {start_text}:00"     # "2026-04-08 10:30:00"

        # 終了時間取得
        end_text = self.end_combo.currentText()      # e.g. "11:00"
        end_at = f"{date_str} {end_text}:00"         # "2026-04-08 11:00:00"

        # カメラ名取得（"■カメラA" → "カメラA"）→ camera_id
        label_text = self.camera_location_title.text()  # e.g. "■カメラA"
        camera_jp = label_text.lstrip("■").strip()       # e.g. "カメラA"
        camera_id = self._CAMERA_ID_MAP.get(camera_jp)
        if camera_id is None:
            return

        self.video_play_requested.emit(start_at, end_at, camera_id)

    def _on_select_clicked(self) -> None:
        employee_id = self.employee_id_edit.text().strip()
        employee_name = self.employee_name_edit.text().strip()
        self.person_select_requested.emit(employee_id, employee_name)

    def _apply_input_style(self, edit: QLineEdit) -> None:
        edit.setFixedHeight(36)
        edit.setStyleSheet("QLineEdit { padding: 6px; font-size: 14px; }")

    def set_sidebar_open(self, is_open: bool) -> None:
        self._sidebar_open = is_open
