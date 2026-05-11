# ui/screens/camera_select_screen.py
"""
カメラ選択画面 — スタンドアロン版（バックエンド依存なし）
"""
from __future__ import annotations

import re
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



# class _SquareBlackFrame(QFrame):
#     def __init__(self, parent: QWidget | None = None) -> None:
#         super().__init__(parent)
#         self._sidebar_open: bool = True
#         self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
#         self.setFixedSize(200, 200)
#         self.setStyleSheet(
#             """
#             QFrame {
#                 background-color: #000000;
#                 border: 1px solid #333333;
#                 border-radius: 0px;
#             }
#             """
#         )


class CameraSelectScreen(QWidget):
    """カメラ選択画面。"""

    search_requested = Signal(str, str, str, str, str, str, list)
    person_select_requested = Signal(str, str)
    back_to_person_select_requested = Signal()
    video_play_requested = Signal(str, str, int)  # start_at, end_at, camera_id
    camera_combo_changed = Signal(int)

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

        self._combo_style = """
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
        _combo_style = self._combo_style

        # ■選択した時間から再生(30分間)
        self.camera_location_title = QLabel("■選択した時間から再生(30分間)", card)
        cl_font = self.camera_location_title.font()
        cl_font.setPointSize(11)
        cl_font.setBold(True)
        self.camera_location_title.setFont(cl_font)
        self.camera_location_title.setStyleSheet("QLabel { background: transparent; border: none; font-size: 18px; }")
        left_layout.addWidget(self.camera_location_title, alignment=Qt.AlignLeft)
        left_layout.addSpacing(4)

        # カメラ選択プルダウン
        self.camera_combo = QComboBox(card)
        self.camera_combo.setFixedHeight(40)
        self.camera_combo.setMinimumWidth(200)
        self.camera_combo.setStyleSheet(_combo_style)
        self.camera_combo.addItem("--- カメラを選択 ---")
        for name in ["カメラA", "カメラB", "カメラC", "カメラD", "カメラE", "カメラF", "カメラG", "カメラH", "カメラI", "カメラJ"]:
            self.camera_combo.addItem(name)
        _all_item = self.camera_combo.model().item(0)
        _all_item.setFlags(_all_item.flags() & ~(Qt.ItemIsEnabled | Qt.ItemIsSelectable))
        _all_item.setData("#aaaaaa", Qt.ForegroundRole)
        self.camera_combo.setCurrentIndex(1)
        self.camera_combo.currentIndexChanged.connect(
            lambda idx: self.camera_combo_changed.emit(idx)
        )
        left_layout.addWidget(self.camera_combo, alignment=Qt.AlignLeft)
        left_layout.addSpacing(8)

        # 撮影日 + 開始時間
        dt_row_widget = QWidget(card)
        dt_row_widget.setStyleSheet("background-color: #ffffff;")
        dt_row = QHBoxLayout(dt_row_widget)
        dt_row.setContentsMargins(0, 0, 0, 0)
        dt_row.setSpacing(8)

        self.date_input = DateInputWithCalendar(dt_row_widget)
        dt_row.addWidget(self.date_input)

        self.start_combo = QComboBox(dt_row_widget)
        self.start_combo.setFixedWidth(120)
        self.start_combo.setFixedHeight(40)
        self.start_combo.setStyleSheet(_combo_style)
        self.start_combo.setEditable(True)
        populate_time_combo(self.start_combo)
        self.start_combo.currentTextChanged.connect(self._on_start_time_changed)
        dt_row.addWidget(self.start_combo)

        self.start_error_label = QLabel("", dt_row_widget)
        self.start_error_label.setStyleSheet(
            "color: #e53935; font-size: 12px; background: transparent; border: none;"
        )
        self.start_error_label.setVisible(False)
        dt_row.addWidget(self.start_error_label)

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
    _CAMERA_ID_MAP: dict[str, int] = {"カメラA": 1, "カメラB": 2, "カメラC": 3, 
                                      "カメラD": 4, "カメラE": 5, "カメラF": 6,
                                        "カメラG": 7, "カメラH": 8, "カメラI": 9, "カメラJ": 10}

    def _on_check_video_clicked(self) -> None:
        """「映像を確認する」ボタン押下：日時とカメラIDをシグナルで発火する。"""
        # 日付取得
        date = self.date_input.get_date()
        if date is None or not date.isValid():
            return
        date_str = date.toString("yyyy-MM-dd")

        # 開始時間取得・バリデーション
        start_text = self.start_combo.currentText()
        error_msg = self._validate_start_time(start_text)
        self._apply_start_time_error(error_msg)
        if error_msg:
            return
        stripped = start_text.strip()
        m = re.fullmatch(r'(\d{1,2}):(\d{2})', stripped)
        h, mi = int(m.group(1)), int(m.group(2))
        start_at = f"{date_str} {h:02d}:{mi:02d}:00"

        # 終了時間 = 開始時間 + 30分
        total_min = h * 60 + mi + 30
        if total_min > 24 * 60:
            total_min = 24 * 60
        eh, em = divmod(total_min, 60)
        end_at = f"{date_str} {eh:02d}:{em:02d}:00"

        # カメラID取得
        camera_text = self.camera_combo.currentText()
        camera_id = self._CAMERA_ID_MAP.get(camera_text)
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

    def _validate_start_time(self, text: str) -> str:
        """開始時間のバリデーション。エラーメッセージを返す。問題なければ空文字列。"""
        stripped = text.strip()
        if not stripped:
            return "必須項目です。時刻を入力してください"
        m = re.fullmatch(r'(\d{1,2}):(\d{2})', stripped)
        if not m:
            return "時刻はHH:MMの形式で入力してください"
        h, mi = int(m.group(1)), int(m.group(2))
        if h > 24 or mi > 59 or (h == 24 and mi > 0):
            return "有効な時間を入力してください"
        return ""

    def _apply_start_time_error(self, error_msg: str) -> None:
        """error_msgが空なら正常スタイル、それ以外はエラー表示＋映像を確認するボタンを無効化する。"""
        if error_msg:
            self.start_combo.setStyleSheet("""
                QComboBox {
                    font-size: 14px;
                    background-color: #fff0f0;
                    color: #000000;
                    padding: 4px 8px;
                    border: 1px solid #e53935;
                    border-radius: 4px;
                }
                QComboBox QAbstractItemView {
                    background-color: #ffffff;
                    color: #000000;
                    selection-background-color: #1E88E5;
                    selection-color: #ffffff;
                }
            """)
            self.start_error_label.setText(error_msg)
            self.start_error_label.setVisible(True)
            self.search_person_button.setEnabled(False)

        else:
            self.start_combo.setStyleSheet(self._combo_style)
            self.start_error_label.setVisible(False)
            self.search_person_button.setEnabled(True)

    def _on_start_time_changed(self, text: str) -> None:
        self._apply_start_time_error(self._validate_start_time(text))

    def set_sidebar_open(self, is_open: bool) -> None:
        self._sidebar_open = is_open
