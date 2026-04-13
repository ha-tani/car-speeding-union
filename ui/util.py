# ui/util.py
"""
共通ウィジェット・ユーティリティ
"""

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLineEdit,
    QComboBox,
    QDialog,
    QVBoxLayout,
    QCalendarWidget,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QAction, QIcon, QPixmap, QPainter


def populate_time_combo(combo: QComboBox) -> None:
    """30分刻みの時刻文字列を QComboBox に追加する。"""
    combo.clear()
    minutes = 0
    while minutes <= 24 * 60:
        h = minutes // 60
        m = minutes % 60
        combo.addItem(f"{h:02d}:{m:02d}")
        minutes += 30


class CalendarLineEdit(QLineEdit):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setPlaceholderText("YYYY/MM/DD")
        self.setMaxLength(10)
        self.setFixedWidth(140)
        self.setMinimumHeight(40)
        self.setStyleSheet("font-size: 14px; padding-right: 22px; background-color: #ffffff; color: #000000;")

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
        calendar.setStyleSheet(
            """
            QCalendarWidget QAbstractItemView {
                background-color: #ffffff;
                color: #000000;
                selection-background-color: #1E88E5;
                selection-color: #ffffff;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #f5f5f5;
            }
            QCalendarWidget QToolButton {
                color: #000000;
                background-color: transparent;
            }
            QCalendarWidget QSpinBox {
                color: #000000;
                background-color: #ffffff;
            }
            """
        )

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
