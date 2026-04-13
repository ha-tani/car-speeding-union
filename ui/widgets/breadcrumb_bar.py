# ui/widgets/breadcrumb_bar.py
"""
BreadcrumbBar — 汎用パンくずリストウィジェット

使い方:
    bar = BreadcrumbBar(parent)
    bar.set_items([
        ("カメラ映像選択", some_callable),  # クリッカブルリンク
        ("映像確認", None),                 # 現在ページ（非クリッカブル）
    ])

コールバックが None の項目は現在ページとして太字で表示する。
コールバックが渡された項目はクリッカブルなリンクとして表示し、クリック時に呼び出す。
"""
from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt


class BreadcrumbBar(QWidget):
    """汎用パンくずリストウィジェット。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(6)
        self._layout.addStretch(1)

    def set_items(self, items: list[tuple[str, Callable | None]]) -> None:
        """パンくずアイテムを設定する。既存アイテムはクリアされる。

        Args:
            items: (ラベル文字列, コールバック or None) のリスト。
                   コールバックが None のものは現在ページ（非クリッカブル）として表示。
        """
        # 末尾の stretch を残しながら既存ウィジェットを削除
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, (label, callback) in enumerate(items):
            # 区切り記号
            if i > 0:
                sep = QLabel(">", self)
                sep.setStyleSheet(
                    "font-size: 15px; color: #666666; background: transparent;"
                )
                self._layout.insertWidget(self._layout.count() - 1, sep)

            if callback is None:
                # 現在ページ — 非クリッカブル太字
                lbl = QLabel(label, self)
                lbl.setStyleSheet(
                    "font-size: 16px; font-weight: bold; color: #222222;"
                    " background: transparent;"
                )
                self._layout.insertWidget(self._layout.count() - 1, lbl)
            else:
                # クリッカブルリンク
                btn = QPushButton(label, self)
                btn.setFlat(True)
                btn.setCursor(Qt.PointingHandCursor)
                btn.setStyleSheet(
                    """
                    QPushButton {
                        border: none; background: transparent;
                        color: #0078d4; font-size: 16px; font-weight: bold;
                        text-decoration: underline; padding: 0px;
                    }
                    QPushButton:hover { color: #005fa3; }
                    """
                )
                btn.clicked.connect(callback)
                self._layout.insertWidget(self._layout.count() - 1, btn)
