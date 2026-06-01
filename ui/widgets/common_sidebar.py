# ui/widgets/common_sidebar.py
"""
CommonSidebarWidget — スタンドアロン版（config / VIDEOS_ROOT 依存なし）
"""
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QLineEdit,
    QComboBox,
    QPushButton,
    QDialog,
    QCalendarWidget,
)
from PySide6.QtCore import Qt, QDate, QSize, Signal
from PySide6.QtGui import QAction, QIcon, QPixmap, QPainter

from widgets.map_view import MapGraphicsView


class CalendarLineEdit(QLineEdit):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setPlaceholderText("YYYY/MM/DD")
        self.setMaxLength(10)
        self.setFixedWidth(140)
        self.setMinimumHeight(40)
        self.setStyleSheet("font-size: 14px; padding-right: 22px;")

        self._calendar_action = QAction(self)
        self._calendar_action.setIcon(self._create_calendar_icon())
        self._calendar_action.setToolTip("カレンダーから選択")
        self.addAction(self._calendar_action, QLineEdit.TrailingPosition)
        self._icon_area_width = 22

    @property
    def calendar_action(self) -> QAction:
        return self._calendar_action

    def _create_calendar_icon(self) -> QIcon:
        size = 18
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing, True)
        font = painter.font()
        font.setPointSize(12)
        painter.setFont(font)
        painter.drawText(pix.rect(), Qt.AlignCenter, "📅")
        painter.end()
        return QIcon(pix)

    def _is_on_icon(self, pos) -> bool:
        rect = self.rect()
        return pos.x() >= rect.width() - self._icon_area_width

    def mouseMoveEvent(self, event) -> None:
        if self._is_on_icon(event.pos()):
            self.setCursor(Qt.PointingHandCursor)
        else:
            self.setCursor(Qt.IBeamCursor)
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        self.setCursor(Qt.IBeamCursor)
        super().leaveEvent(event)


class DateInputWithCalendar(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.line_edit = CalendarLineEdit(self)
        layout.addWidget(self.line_edit)

        self.calendar_action: QAction = self.line_edit.calendar_action
        self.calendar_action.triggered.connect(self._open_calendar)

        today = QDate.currentDate()
        self.set_date(today)

    def _open_calendar(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("日付を選択")
        dialog.setModal(True)

        vbox = QVBoxLayout(dialog)
        calendar = QCalendarWidget(dialog)
        calendar.setGridVisible(True)
        calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)

        current = self.get_date()
        if current is not None:
            calendar.setSelectedDate(current)

        vbox.addWidget(calendar)

        def on_date_selected(date: QDate) -> None:
            self.set_date(date)
            dialog.accept()

        calendar.clicked.connect(on_date_selected)
        dialog.resize(320, 240)
        dialog.exec()

    def set_date(self, date: QDate) -> None:
        if not date.isValid():
            return
        text = date.toString("yyyy/MM/dd")
        self.line_edit.setText(text)

    def get_date(self) -> QDate | None:
        text = self.line_edit.text().strip()
        if not text:
            return None
        parts = text.split("/")
        if len(parts) != 3:
            return None
        try:
            y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
        except ValueError:
            return None
        date = QDate(y, m, d)
        return date if date.isValid() else None


class CommonSidebarWidget(QWidget):
    """全画面共通サイドバー。"""

    sidebar_toggle_requested = Signal()
    map_changed = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._icon_open: QPixmap | None = None
        self._icon_close: QPixmap | None = None
        self._collapsed_width: int = 48
        self._toggle_button: QPushButton | None = None
        self._content_panel: QWidget | None = None

        self.zoom_out_button: QPushButton | None = None
        self.zoom_in_button: QPushButton | None = None
        self.zoom_reset_button: QPushButton | None = None
        self.zoom_label: QLabel | None = None
        self.map_combobox: QComboBox | None = None

        self._setup_ui()

    def _project_root(self) -> Path:
        return Path.cwd()

    def _load_sidebar_icon(self, base_name: str) -> QPixmap | None:
        root = self._project_root()
        exts = ("png", "jpg", "jpeg", "svg")
        candidates: list[Path] = []
        for ext in exts:
            candidates.append(root / "assets" / "sidebar" / f"{base_name}.{ext}")
            candidates.append(root / "src" / "assets" / "sidebar" / f"{base_name}.{ext}")
        for path in candidates:
            if path.exists():
                pix = QPixmap(str(path))
                if not pix.isNull():
                    return pix
        return None

    def _setup_ui(self) -> None:
        self.setObjectName("common-sidebar")
        self.setStyleSheet(
            """
            #common-sidebar { background-color: #f5f5f5; }
            #common-sidebar QLabel { color: #333333; }
            """
        )

        self._icon_close = self._load_sidebar_icon("sidebar_close")
        self._icon_open = self._load_sidebar_icon("sidebar_open")

        icon_for_width = self._icon_close or self._icon_open
        if icon_for_width is not None and not icon_for_width.isNull():
            self._collapsed_width = 48
        else:
            self._collapsed_width = 48

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(8, 12, 8, 8)
        root_layout.setSpacing(12)

        # 右上: 開閉用アイコン
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(0)
        header_row.addStretch(1)

        self._toggle_button = QPushButton(self)
        self._toggle_button.setFlat(True)
        self._toggle_button.setCursor(Qt.PointingHandCursor)
        self._toggle_button.setStyleSheet(
            "QPushButton { background: transparent; border: none;"
            " padding: 2px; }"
            "QPushButton:hover { background: #dddddd; border-radius: 4px; }"
        )
        self._toggle_button.setFixedSize(36, 36)
        if self._icon_close is not None and not self._icon_close.isNull():
            self._toggle_button.setIcon(QIcon(self._icon_close))
            self._toggle_button.setIconSize(QSize(28, 28))
        else:
            self._toggle_button.setText("☰")

        self._toggle_button.clicked.connect(self.sidebar_toggle_requested.emit)
        header_row.addWidget(self._toggle_button, 0, alignment=Qt.AlignRight | Qt.AlignTop)
        root_layout.addLayout(header_row)

        # コンテンツパネル
        self._content_panel = QWidget(self)
        content_layout = QVBoxLayout(self._content_panel)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        # 横一列: マップ選択・撮影日・撮影時間・ボタン
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(48)

        # カメラの設置場所
        map_col = QWidget(self._content_panel)
        map_col_layout = QVBoxLayout(map_col)
        map_col_layout.setContentsMargins(0, 0, 0, 0)
        map_col_layout.setSpacing(4)
        map_label = QLabel("カメラの設置場所", map_col)
        map_label.setStyleSheet("font-size: 12px;")
        map_col_layout.addWidget(map_label)

        self.map_combobox = QComboBox(map_col)
        self.map_combobox.addItem("すべてのカメラ")
        self.map_combobox.addItem("カメラA")
        self.map_combobox.addItem("カメラB")
        self.map_combobox.addItem("カメラC")
        self.map_combobox.addItem("カメラD")
        self.map_combobox.addItem("カメラE")
        self.map_combobox.addItem("カメラF")
        self.map_combobox.addItem("カメラG")
        self.map_combobox.addItem("カメラH")
        self.map_combobox.addItem("カメラI")
        self.map_combobox.addItem("カメラJ")
        self.map_combobox.addItem("カメラQ")
        self.map_combobox.setMinimumHeight(40)
        self.map_combobox.setStyleSheet("font-size: 14px;")
        self.map_combobox.currentIndexChanged.connect(self._on_map_changed)
        map_col_layout.addWidget(self.map_combobox)
        top_row.addWidget(map_col, 0)

        wrapper = QHBoxLayout()
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.setSpacing(0)
        wrapper.addLayout(top_row)
        wrapper.addStretch(1)
        content_layout.addLayout(wrapper)

        # マップビュー
        self.map_view = MapGraphicsView(self._content_panel)
        self.map_view.setMinimumHeight(200)
        self.map_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        content_layout.addWidget(self.map_view, 1)

        # 縮尺ボタン群
        zoom_row = QHBoxLayout()
        zoom_row.setContentsMargins(0, 4, 0, 0)
        zoom_row.setSpacing(4)
        zoom_row.addStretch(1)

        self.zoom_out_button = QPushButton("－", self._content_panel)
        self.zoom_out_button.setFixedSize(28, 28)
        self.zoom_out_button.setCursor(Qt.PointingHandCursor)
        self.zoom_out_button.clicked.connect(self._on_zoom_out_clicked)
        zoom_row.addWidget(self.zoom_out_button)

        self.zoom_in_button = QPushButton("＋", self._content_panel)
        self.zoom_in_button.setFixedSize(28, 28)
        self.zoom_in_button.setCursor(Qt.PointingHandCursor)
        self.zoom_in_button.clicked.connect(self._on_zoom_in_clicked)
        zoom_row.addWidget(self.zoom_in_button)

        self.zoom_label = QLabel("100%", self._content_panel)
        self.zoom_label.setAlignment(Qt.AlignCenter)
        self.zoom_label.setMinimumWidth(48)
        zoom_row.addWidget(self.zoom_label)

        self.zoom_reset_button = QPushButton("リセット", self._content_panel)
        self.zoom_reset_button.setFixedHeight(28)
        self.zoom_reset_button.setCursor(Qt.PointingHandCursor)
        self.zoom_reset_button.clicked.connect(self._on_zoom_reset_clicked)
        zoom_row.addWidget(self.zoom_reset_button)

        content_layout.addLayout(zoom_row)

        if hasattr(self.map_view, "zoom_changed"):
            self.map_view.zoom_changed.connect(self._on_map_zoom_changed)
        if hasattr(self.map_view, "camera_icon_clicked"):
            self.map_view.camera_icon_clicked.connect(self._on_camera_icon_clicked)

        # 初期アイコン状態を同期
        if self.map_combobox is not None:
            self.map_view.select_camera(self.map_combobox.currentText())

        root_layout.addWidget(self._content_panel, 1)

    def _on_map_changed(self) -> None:
        if self.map_combobox is None:
            return
        text = self.map_combobox.currentText()
        if text:
            self.map_view.select_camera(text)
            self.map_changed.emit(text)

    def _on_zoom_in_clicked(self) -> None:
        self.map_view.zoom_in()

    def _on_zoom_out_clicked(self) -> None:
        self.map_view.zoom_out()

    def _on_zoom_reset_clicked(self) -> None:
        self.map_view.reset_view()

    def _on_map_zoom_changed(self, percent: int) -> None:
        if self.zoom_label is not None:
            self.zoom_label.setText(f"{percent}%")

    def _on_camera_icon_clicked(self, camera_name: str) -> None:
        if self.map_combobox is None:
            return
        index = self.map_combobox.findText(camera_name)
        if index >= 0:
            self.map_combobox.setCurrentIndex(index)

    def _populate_time_combo(self) -> None:
        self.time_combo.clear()
        times: list[str] = []
        for hour in range(0, 24):
            for minute in (0, 30):
                times.append(f"{hour:02d}:{minute:02d}")
        self.time_combo.addItems(times)
        default_time = "08:00"
        index = self.time_combo.findText(default_time)
        if index >= 0:
            self.time_combo.setCurrentIndex(index)

    def set_sidebar_open(self, is_open: bool) -> None:
        if self._toggle_button is not None:
            # 開いているときは「閉じる」アイコン、閉じているときは「開く」アイコン
            pix = self._icon_close if is_open else self._icon_open
            if pix is not None and not pix.isNull():
                self._toggle_button.setIcon(QIcon(pix))
                self._toggle_button.setIconSize(QSize(28, 28))
                self._toggle_button.setText("")
            else:
                self._toggle_button.setIcon(QIcon())
                self._toggle_button.setText("☰")
        if self._content_panel is not None:
            self._content_panel.setVisible(is_open)

    def collapsed_width(self) -> int:
        return self._collapsed_width
