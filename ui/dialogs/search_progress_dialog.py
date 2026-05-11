# # ui/dialogs/search_progress_dialog.py
# """
# 検索プログレスダイアログ — スタブ版
# """
# from PySide6.QtWidgets import (
#     QDialog,
#     QVBoxLayout,
#     QLabel,
#     QProgressBar,
#     QPushButton,
#     QSizePolicy,
# )
# from PySide6.QtCore import Qt, Signal


# class SearchProgressDialog(QDialog):
#     """検索処理中のモーダルプログレスバーダイアログ（スタブ）。"""

#     cancel_requested = Signal()

#     def __init__(self, parent=None, video_count: int = 0) -> None:
#         super().__init__(parent)
#         self.setWindowTitle("検索中")
#         self.setModal(True)
#         self.resize(400, 150)

#         layout = QVBoxLayout(self)

#         self._status_label = QLabel("検索を準備しています…", self)
#         self._status_label.setStyleSheet("font-size: 14px; font-weight: bold;")
#         layout.addWidget(self._status_label)

#         self._progress_bar = QProgressBar(self)
#         self._progress_bar.setRange(0, 100)
#         self._progress_bar.setValue(0)
#         layout.addWidget(self._progress_bar)

#         cancel_btn = QPushButton("キャンセル", self)
#         cancel_btn.clicked.connect(self.cancel_requested.emit)
#         layout.addWidget(cancel_btn)
