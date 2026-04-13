# ui/screens/violating_vehicle_info_screen.py
"""
違反車両一覧画面 — スタンドアロン版（バックエンド依存なし）
"""
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QFrame,
    QComboBox,
    QScrollArea,
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QIcon

from util import DateInputWithCalendar, populate_time_combo
from db.db_query import search_violation_events


class _SquareBlackFrame(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setMinimumSize(80, 80)
        self.setStyleSheet(
            """
            QFrame {
                background-color: #000000;
                border: 1px solid #333333;
            }
            """
        )

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        h = self.height()
        if h > 0:
            self.setMinimumWidth(h)
            self.setMaximumWidth(h)


class _ResultRow(QFrame):
    """枠付き・クリック可能な結果行ウィジェット"""

    clicked = Signal(dict)

    def __init__(self, row_data: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._row_data = row_data
        self.setObjectName("result-row")
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(
            "QFrame#result-row {"
            "  border: 1px solid #cccccc;"
            "  background-color: #ffffff;"
            "}"
            "QFrame#result-row:hover {"
            "  background-color: #e8f0fe;"
            "}"
        )

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._row_data)
        super().mousePressEvent(event)


class SearchResultScreen(QWidget):
    """違反車両一覧画面"""

    back_to_person_select_requested = Signal()
    play_requested = Signal(str, int)
    row_clicked = Signal(dict)
    play_icon_clicked = Signal(dict)

    _PLAY_ICON_PATH: str = str(
        Path(__file__).parent.parent.parent / "assets" / "sidebar" / "play.png"
    )

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._sidebar_open: bool = True
        self._results_layout: QVBoxLayout | None = None
        self._setup_ui()
        self._on_search_clicked()

    def _setup_ui(self) -> None:
        self.setObjectName("search-result-screen")

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(8, 12, 8, 8)
        root_layout.setSpacing(12)

        # 違反車両一覧タイトル
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(4)

        self.result_label = QLabel("違反車両一覧（0件）", self)
        self.result_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: black;"
        )
        title_row.addWidget(self.result_label)
        title_row.addStretch(1)
        root_layout.addLayout(title_row)

        # --- 検索条件パネル 1行目 ---
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)

        search_label = QLabel("検索条件", self)
        search_label.setStyleSheet("font-size: 12px;")
        row.addWidget(search_label)

        root_layout.addLayout(row)

        # [撮影日選択][開始時間]～[終了時間][カメラの設置場所]
        row1 = QHBoxLayout()
        row1.setContentsMargins(0, 0, 0, 0)
        row1.setSpacing(8)

        # 撮影日
        self.date_input = DateInputWithCalendar(self)
        row1.addWidget(self.date_input)

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

        # 開始時間(手入力＋コンボ)
        self.start_combo = QComboBox(self)
        self.start_combo.setFixedWidth(110)
        self.start_combo.setFixedHeight(40)
        self.start_combo.setStyleSheet(_combo_style)
        populate_time_combo(self.start_combo)
        # self.start_combo.setEditable(True)
        # regex = QRegularExpression(r"^([01]\d|2[0-3]):([0-5]\d)$")
        # self.start_combo.setValidator(QRegularExpressionValidator(regex))
        row1.addWidget(self.start_combo)

        # ～
        time_label = QLabel("～", self)
        time_label.setStyleSheet("font-size: 12px;")
        row1.addWidget(time_label)

        # 終了時間(手入力＋コンボ)
        self.end_combo = QComboBox(self)
        self.end_combo.setFixedWidth(110)
        self.end_combo.setFixedHeight(40)
        self.end_combo.setStyleSheet(_combo_style)
        populate_time_combo(self.end_combo)
        self.end_combo.setCurrentText("24:00")
        # self.end_combo.setEditable(True)
        # regex = QRegularExpression(r"^([01]\d|2[0-3]):([0-5]\d)$")
        # self.end_combo.setValidator(QRegularExpressionValidator(regex))
        row1.addWidget(self.end_combo)

        # カメラの設置場所
        self.camera_combo = QComboBox(self)
        self.camera_combo.setFixedWidth(160)
        self.camera_combo.setFixedHeight(40)
        self.camera_combo.setStyleSheet(_combo_style)
        self.camera_combo.addItem("すべてのカメラ")
        self.camera_combo.addItem("カメラA")
        self.camera_combo.addItem("カメラB")
        row1.addWidget(self.camera_combo)

        row1.addStretch(1)
        root_layout.addLayout(row1)

        # --- 検索条件パネル 2行目 ---
        # [制限速度][検索ボタン]
        row2 = QHBoxLayout()
        row2.setContentsMargins(0, 0, 0, 0)
        row2.setSpacing(8)

        # 制限速度
        self.speed_combo = QComboBox(self)
        self.speed_combo.setFixedWidth(120)
        self.speed_combo.setFixedHeight(40)
        self.speed_combo.setStyleSheet(_combo_style)
        self.speed_combo.addItem("制限速度")
        self.speed_combo.addItem("5 km/h")
        self.speed_combo.addItem("35 km/h")
        self.speed_combo.addItem("45 km/h")
        self.speed_combo.setCurrentText("5 km/h")
        row2.addWidget(self.speed_combo)

        # 検索ボタン
        self.search_button = QPushButton("この条件で検索", self)
        self.search_button.setFixedHeight(30)
        self.search_button.setStyleSheet(
            "QPushButton { background: #0078d4; color: white; border-radius: 4px;"
            " font-size: 14px; padding: 0 16px; }"
            "QPushButton:hover { background: #006cbd; }"
        )
        self.search_button.clicked.connect(self._on_search_clicked)
        row2.addWidget(self.search_button)
        row2.addStretch(1)
        root_layout.addLayout(row2)

        # --- 結果グリッド領域（スクロール可能）---
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")

        scroll_content = QWidget()
        self._results_layout = QVBoxLayout(scroll_content)
        self._results_layout.setContentsMargins(0, 0, 0, 0)
        self._results_layout.setSpacing(8)

        scroll_area.setWidget(scroll_content)
        scroll_area.setMinimumHeight(540)  # 6行分表示（6×80px + 5×12px）
        root_layout.addWidget(scroll_area, 1)

    # ─────────────────────────────────────────────
    # カメラ名 → camera_id マッピング
    # ─────────────────────────────────────────────
    _CAMERA_ID_MAP: dict[str, int] = {
        "カメラA": 1,
        "カメラB": 2,
    }

    def _on_search_clicked(self) -> None:
        # ① 撮影日 + 開始時間 → TIMESTAMP 文字列
        date = self.date_input.get_date()
        if date is None:
            print("[検索] 撮影日が未入力または不正です")
            return
        date_str = date.toString("yyyy-MM-dd")
        start_time = self.start_combo.currentText()   # "HH:MM"
        detected_at_from = f"{date_str} {start_time}:00"

        # ② 撮影日 + 終了時間 → TIMESTAMP 文字列
        end_time = self.end_combo.currentText()       # "HH:MM"
        detected_at_to = f"{date_str} {end_time}:00"

        # ③ カメラの設置場所 → camera_id (None = すべて)
        camera_text = self.camera_combo.currentText()
        camera_id: int | None = self._CAMERA_ID_MAP.get(camera_text)  # 「すべてのカメラ」は None

        # ④ 制限速度 → 数値 (None = 絞り込みなし)
        speed_text = self.speed_combo.currentText()
        speed_limit: float | None = None
        if speed_text != "制限速度":
            numeric_part = speed_text.split()[0]      # "35 km/h" → "35"
            try:
                speed_limit = float(numeric_part)
            except ValueError:
                print(f"[検索] 制限速度の解析に失敗しました: {speed_text}")
                return

        print(
            f"[検索] 条件: detected_at={detected_at_from!r} ～ {detected_at_to!r}, "
            f"camera_id={camera_id!r}, speed_limit={speed_limit!r}"
        )

        # ⑤ DB 検索
        try:
            rows = search_violation_events(
                detected_at_from=detected_at_from,
                detected_at_to=detected_at_to,
                camera_id=camera_id,
                speed_limit=speed_limit,
            )
        except Exception as exc:
            print(f"[検索] DB エラー: {exc}")
            return

        # ⑥ 結果をグリッドエリアに表示
        self.result_label.setText(f"違反車両一覧（{len(rows)} 件）")
        self._populate_results(rows)

    # ─────────────────────────────────────────────
    # camera_id → カメラ名 マッピング
    # ─────────────────────────────────────────────
    _CAMERA_NAME_MAP: dict[int, str] = {1: "カメラA", 2: "カメラB"}

    def _clear_results(self) -> None:
        layout = self._results_layout
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _make_image_label(self, path: str | None) -> QLabel:
        label = QLabel(self)
        label.setFixedSize(120, 80)
        label.setAlignment(Qt.AlignCenter)
        if path:
            pix = QPixmap(path)
            if not pix.isNull():
                label.setPixmap(
                    pix.scaled(120, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                return label
        label.setStyleSheet("background-color: #000000; border: 1px solid #333333;")
        return label

    def _populate_results(self, rows: list[dict]) -> None:
        self._clear_results()

        _text_style = "font-size: 12px; color: #000000;"
        for row in rows:
            row_widget = _ResultRow(row, self)
            row_widget.clicked.connect(self._on_row_clicked)

            row_h_layout = QHBoxLayout(row_widget)
            row_h_layout.setContentsMargins(8, 8, 8, 8)
            row_h_layout.setSpacing(12)

            # ナンバープレート画像
            row_h_layout.addWidget(self._make_image_label(row.get("plate_image_path")))
            # 車両画像
            row_h_layout.addWidget(self._make_image_label(row.get("vehicle_image_path")))
            # 画像とテキストの間にスペース
            row_h_layout.addSpacing(30) 
            # テキスト情報 4行
            detected_at = row.get("detected_at")
            if detected_at is not None:
                dt_str = str(detected_at)
                date_part = dt_str[:10]    # "YYYY-MM-DD"
                time_part = dt_str[11:19]  # "HH:MM:SS"
            else:
                date_part = "—"
                time_part = "—"

            camera_id_val = row.get("camera_id")
            camera_name = self._CAMERA_NAME_MAP.get(
                camera_id_val, str(camera_id_val) if camera_id_val is not None else "—"
            )
            measured_speed = row.get("measured_speed")

            info_widget = QWidget(row_widget)
            info_layout = QVBoxLayout(info_widget)
            info_layout.setContentsMargins(0, 4, 0, 4)
            info_layout.setSpacing(4)
            for text in [
                f"日時：{date_part}",
                f"時間：{time_part}",
                f"速度：{measured_speed if measured_speed is not None else '—'}km/h",
                f"カメラ：{camera_name}",
            ]:
                lbl = QLabel(text, info_widget)
                lbl.setStyleSheet(_text_style)
                info_layout.addWidget(lbl)
            info_layout.addStretch(1)

            row_h_layout.addWidget(info_widget)

            play_btn = QPushButton(row_widget)
            play_btn.setIcon(QIcon(self._PLAY_ICON_PATH))
            play_btn.setIconSize(QSize(36, 36))
            play_btn.setFixedSize(44, 44)
            play_btn.setStyleSheet(
                "QPushButton { background: transparent; border: none; }"
                "QPushButton:hover { background: rgba(0,0,0,0.08); border-radius: 22px; }"
            )
            play_btn.clicked.connect(
                lambda checked=False, r=row: self.play_icon_clicked.emit(r)
            )

            row_h_layout.addStretch(1)
            row_h_layout.addWidget(play_btn, alignment=Qt.AlignVCenter)

            self._results_layout.addWidget(row_widget)

        # 末尾に伸縮スペーサーを追加
        self._results_layout.addStretch(1)

    def _on_row_clicked(self, row_data: dict) -> None:
        self.row_clicked.emit(row_data)

    def set_sidebar_open(self, is_open: bool) -> None:
        self._sidebar_open = is_open

