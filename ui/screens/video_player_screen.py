# ui/screens/video_player_screen.py
"""
カメラ選択画面 — スタンドアロン版（バックエンド依存なし）
"""
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
)
from PySide6.QtCore import Qt, Signal

from widgets.breadcrumb_bar import BreadcrumbBar
from widgets.video_player_view import VideoPlayerView


class VideoPlayerScreen(QWidget):
    """
    映像プレイヤー画面。
    パンくずリスト + プレイヤー領域。
    """

    to_search_result_requested = Signal()
    back_to_person_select_requested = Signal()
    back_to_search_result_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._sidebar_open: bool = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setObjectName("video-player-screen")

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(12)

        # 中央寄せ用横レイアウト
        center_row = QHBoxLayout()
        center_row.setContentsMargins(0, 0, 0, 0)
        center_row.setSpacing(0)
        center_row.addStretch(1)

        center_col_widget = QWidget(self)
        center_col_layout = QVBoxLayout(center_col_widget)
        center_col_layout.setContentsMargins(0, 0, 0, 0)
        center_col_layout.setSpacing(8)

        # パンくずリスト
        self.breadcrumb = BreadcrumbBar(center_col_widget)
        self.breadcrumb.set_items([
            ("カメラ映像選択", lambda: self.back_to_person_select_requested.emit()),
            ("映像確認", None),
        ])
        center_col_layout.addWidget(self.breadcrumb, 0, alignment=Qt.AlignLeft)

        # プレイヤー
        self.video_view = VideoPlayerView(center_col_widget)
        center_col_layout.addWidget(self.video_view, 1)

        center_row.addWidget(center_col_widget)
        center_row.addStretch(1)

        root_layout.addLayout(center_row, 1)

    def load_video(
        self,
        path: str,
        datetime_str: str = "",
        camera_id: int | None = None,
        realtime_detection: bool = False,
    ) -> None:
        """指定パスの動画を VideoPlayerView に読み込んで再生する。"""
        self.video_view.load_video(
            path,
            datetime_str,
            camera_id=camera_id,
            realtime_detection=realtime_detection,
        )

    def set_source(self, source: str) -> None:
        """遷移元に応じてパンくずリストを更新する。

        Args:
            source: "search_result" → 違反車両一覧から、それ以外 → カメラ映像選択から
        """
        if source == "search_result":
            self.breadcrumb.set_items([
                ("違反車両一覧", lambda: self.back_to_search_result_requested.emit()),
                ("映像確認", None),
            ])
        else:
            self.breadcrumb.set_items([
                ("カメラ映像選択", lambda: self.back_to_person_select_requested.emit()),
                ("映像確認", None),
            ])

    def set_sidebar_open(self, is_open: bool) -> None:
        self._sidebar_open = is_open
        if hasattr(self.video_view, "set_sidebar_open"):
            self.video_view.set_sidebar_open(is_open)
