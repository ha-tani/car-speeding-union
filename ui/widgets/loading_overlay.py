import logging
from PySide6.QtWidgets import QWidget, QVBoxLayout, QProgressBar
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette

log = logging.getLogger("ui.loading_overlay")


class LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        log.info("[Overlay] __init__ called")

        if parent is None:
            log.warning("[Overlay] parent is None")

        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setWindowFlags(Qt.FramelessWindowHint)

        # 半透明背景
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(0, 0, 0, 120))
        self.setAutoFillBackground(True)
        self.setPalette(palette)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        self.spinner = QProgressBar()
        self.spinner.setRange(0, 0)  # 無限ループ
        self.spinner.setFixedWidth(200)

        layout.addWidget(self.spinner)

        self.hide()
        log.info("[Overlay] initialized and hidden")

    def showEvent(self, event):
        log.info("[Overlay] showEvent called")
        super().showEvent(event)

    def hideEvent(self, event):
        log.info("[Overlay] hideEvent called")
        super().hideEvent(event)

    def resizeEvent(self, event):
        if self.parent():
            self.setGeometry(self.parent().rect())
            log.debug(
                "[Overlay] resized to parent: %s",
                self.parent().rect(),
            )
        else:
            log.warning("[Overlay] resizeEvent but no parent")
        super().resizeEvent(event)
