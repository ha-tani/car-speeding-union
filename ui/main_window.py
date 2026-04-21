# ui/main_window.py
"""
MainWindow — 画面遷移のみ（バックエンド依存なし）
"""
import logging
import os
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QStackedWidget,
    QFrame,
    QApplication,
)
from PySide6.QtCore import Qt, Slot

from widgets.common_header import CommonHeaderWidget
from widgets.common_sidebar import CommonSidebarWidget
from widgets.loading_overlay import LoadingOverlay
# from ui.screens.video_player_screen import VideoPlayerScreen
# from ui.screens.violating_vehicle_info_screen import SearchResultScreen
# from ui.screens.camera_select_screen import CameraSelectScreen
from screens.video_player_screen import VideoPlayerScreen
from screens.violating_vehicle_info_screen import SearchResultScreen
from screens.camera_select_screen import CameraSelectScreen
from search_video import find_and_clip_video, find_and_clip_video_centered, find_and_clip_video_range


class MainWindow(QMainWindow):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Car Speeding App")
        self.resize(1920, 1080)

        self._sidebar_visible = True
        self.log = logging.getLogger("MainWindow")

        self._setup_ui()

        # ローディングオーバーレイ
        self.loading_overlay = LoadingOverlay(self)

    def _setup_ui(self) -> None:
        central = QWidget(self)
        central.setObjectName("central-root")
        central.setStyleSheet("#central-root { background-color: white; }")
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ヘッダー
        self.header = CommonHeaderWidget(self)
        root_layout.addWidget(self.header)

        # ボディ（サイドバー + メインコンテンツ）
        body_widget = QWidget(self)
        body_layout = QHBoxLayout(body_widget)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        self._body_layout = body_layout

        self.sidebar = CommonSidebarWidget(self)
        self.sidebar.sidebar_toggle_requested.connect(self._toggle_sidebar)
        body_layout.addWidget(self.sidebar)

        self.separator = QFrame(self)
        self.separator.setFrameShape(QFrame.VLine)
        self.separator.setFrameShadow(QFrame.Plain)
        self.separator.setLineWidth(1)
        self.separator.setStyleSheet("color: #cccccc;")
        body_layout.addWidget(self.separator)

        self.screen_stack = QStackedWidget(self)
        body_layout.addWidget(self.screen_stack)

        body_layout.setStretch(0, 1)
        body_layout.setStretch(1, 0)
        body_layout.setStretch(2, 1)

        root_layout.addWidget(body_widget, 1)

        # ===== 各画面の登録 =====
        self.search_screen = SearchResultScreen(parent=self)
        self.screen_stack.addWidget(self.search_screen)
        self.screen_stack.setCurrentWidget(self.search_screen)

        self.video_player_screen = VideoPlayerScreen(parent=self)
        self.screen_stack.addWidget(self.video_player_screen)

        self.person_select_screen = CameraSelectScreen(self)
        self.screen_stack.addWidget(self.person_select_screen)

        # ===== シグナル接続（画面遷移） =====
        # ハンバーガーメニュー → 違反車両一覧
        self.header.video_person_select_requested.connect(self._show_search_result_screen)
        # ハンバーガーメニュー → カメラ選択画面
        self.header.person_select_requested.connect(self._on_person_select_requested)

        # 映像プレイヤー画面 → 検索結果画面
        self.video_player_screen.to_search_result_requested.connect(self._show_search_result_screen)
        # 映像プレイヤー画面（映像確認）→ カメラ映像選択画面に戻る
        self.video_player_screen.back_to_person_select_requested.connect(self._on_person_select_requested)
        # 映像プレイヤー画面（映像確認）→ 違反車両一覧に戻る
        self.video_player_screen.back_to_search_result_requested.connect(self._show_search_result_screen)
        # 検索結果画面 → 映像プレイヤー画面に戻る
        self.search_screen.back_to_person_select_requested.connect(self._show_search_result_screen)
        # 人物指定画面 → カメラ画面に戻る
        self.person_select_screen.back_to_person_select_requested.connect(self._show_search_result_screen)
        # 人物指定画面 → 映像プレイヤー画面へ
        self.person_select_screen.video_play_requested.connect(self._on_video_play_requested)

        # コンボボックス連動
        self.sidebar.map_combobox.currentIndexChanged.connect(self._on_sidebar_camera_changed)
        self.search_screen.camera_combo.currentIndexChanged.connect(self._on_result_camera_changed)
        self.person_select_screen.camera_combo_changed.connect(self._on_person_select_camera_changed)

        # 検索結果の再生ボタン
        self.search_screen.play_icon_clicked.connect(self._on_play_icon_clicked)

        self._tmp_video_path: str | None = None

        self._apply_sidebar_visibility()

    # -----------------------------------
    # 画面遷移
    # -----------------------------------
    def _show_camera_select_screen(self) -> None:
        self._sidebar_visible = False
        self._apply_sidebar_visibility()
        self.screen_stack.setCurrentWidget(self.video_player_screen)
        self._set_all_cameras_item_enabled(True)

    def _show_search_result_screen(self) -> None:
        self._apply_sidebar_visibility()
        self.screen_stack.setCurrentWidget(self.search_screen)
        self._set_all_cameras_item_enabled(True)

    def _on_person_select_requested(self) -> None:
        self._apply_sidebar_visibility()
        self.screen_stack.setCurrentWidget(self.person_select_screen)
        self._set_all_cameras_item_enabled(False)

    def _on_check_videos_clicked(self) -> None:
        """サイドバーの「映像を確認する」ボタン押下。"""
        self.log.info("映像を確認する ボタンが押されました（スタブ）")

    def _on_video_play_requested(self, start_at: str, end_at: str, camera_id: int) -> None:
        """CameraSelectScreen から動画再生要求を受けて範囲内の全動画を結合・再生する。"""
        self.log.info("動画再生要求: start=%s end=%s camera_id=%s", start_at, end_at, camera_id)
        tmp_path = find_and_clip_video_range(start_at, end_at, camera_id)
        if tmp_path is None:
            self.log.warning("動画の切り出しに失敗しました")
            return

        if self._tmp_video_path and os.path.exists(self._tmp_video_path):
            try:
                os.remove(self._tmp_video_path)
            except OSError:
                pass
        self._tmp_video_path = tmp_path

        self.video_player_screen.load_video(
            tmp_path,
            f"{start_at} ～ {end_at}",
            camera_id=camera_id,
            realtime_detection=True,
        )
        self.video_player_screen.set_source("person_select")
        self._sidebar_visible = False
        self._apply_sidebar_visibility()
        self.screen_stack.setCurrentWidget(self.video_player_screen)

    def _set_all_cameras_item_enabled(self, enabled: bool) -> None:
        """両コンボボックスの「すべてのカメラ」項目（index=0）の有効/無効を切り替える。
        enabled=False 且つ現在index=0が選択されている場合は次の項目（index=1）へ移動する。
        """
        for combo in (self.sidebar.map_combobox, self.search_screen.camera_combo):
            if combo is None:
                continue
            item = combo.model().item(0)
            if item is None:
                continue
            if enabled:
                item.setFlags(item.flags() | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            else:
                item.setFlags(item.flags() & ~(Qt.ItemIsEnabled | Qt.ItemIsSelectable))
                if combo.currentIndex() == 0:
                    combo.setCurrentIndex(1)

    @Slot(int)
    def _on_sidebar_camera_changed(self, index: int) -> None:
        """サイドバーのmap_combobox変更 → 他ウィジェットに同期。"""
        text = self.sidebar.map_combobox.currentText()
        self.search_screen.camera_combo.blockSignals(True)
        self.search_screen.camera_combo.setCurrentIndex(index)
        self.search_screen.camera_combo.blockSignals(False)
        self.person_select_screen.camera_combo.blockSignals(True)
        self.person_select_screen.camera_combo.setCurrentIndex(index)
        self.person_select_screen.camera_combo.blockSignals(False)

    @Slot(int)
    def _on_result_camera_changed(self, index: int) -> None:
        """search_result_screenのcamera_combo変更 → 他ウィジェットに同期。"""
        text = self.search_screen.camera_combo.currentText()
        self.sidebar.map_combobox.blockSignals(True)
        self.sidebar.map_combobox.setCurrentIndex(index)
        self.sidebar.map_combobox.blockSignals(False)
        self.sidebar.map_view.select_camera(text)
        self.person_select_screen.camera_combo.blockSignals(True)
        self.person_select_screen.camera_combo.setCurrentIndex(index)
        self.person_select_screen.camera_combo.blockSignals(False)

    @Slot(int)
    def _on_person_select_camera_changed(self, index: int) -> None:
        """カメラ選択画面のcamera_combo変更 → 他ウィジェットに同期。"""
        text = self.person_select_screen.camera_combo.currentText()
        self.sidebar.map_combobox.blockSignals(True)
        self.sidebar.map_combobox.setCurrentIndex(index)
        self.sidebar.map_combobox.blockSignals(False)
        self.sidebar.map_view.select_camera(text)
        self.search_screen.camera_combo.blockSignals(True)
        self.search_screen.camera_combo.setCurrentIndex(index)
        self.search_screen.camera_combo.blockSignals(False)

    # -----------------------------------
    # 再生ボタン処理（ffmpeg切り取り → 動画再生）
    # -----------------------------------
    def _on_play_icon_clicked(self, row_data: dict) -> None:
        """検索結果の再生ボタン押下 → ffmpeg で動画を切り取り → 映像プレイヤー画面で再生。"""
        detected_at = row_data.get("detected_at")
        camera_id = row_data.get("camera_id")

        if detected_at is None or camera_id is None:
            self.log.warning("再生に必要な情報が不足しています: %s", row_data)
            return

        source = "search_result"  # 検索結果画面からの遷移であることを示すフラグ
        self._play_clipped_video(detected_at, camera_id, source, centered=True)

    def _play_clipped_video(
        self,
        detected_at,
        camera_id: int,
        source: str,
        centered: bool = False,
    ) -> None:
        """ffmpeg で切り出した一時ファイルを映像プレイヤー画面で再生する共通処理。"""
        if centered:
            tmp_path = find_and_clip_video_centered(
                detected_at,
                camera_id,
                before_seconds=3.0,
                after_seconds=3.0,
            )
        else:
            tmp_path = find_and_clip_video(detected_at, camera_id)

        if tmp_path is None:
            self.log.warning("動画の切り出しに失敗しました")
            return

        # 以前の一時ファイルを削除
        if self._tmp_video_path and os.path.exists(self._tmp_video_path):
            try:
                os.remove(self._tmp_video_path)
            except OSError:
                pass
        self._tmp_video_path = tmp_path

        self.video_player_screen.load_video(
            tmp_path,
            str(detected_at),
            camera_id=camera_id,
            realtime_detection=True,
        )
        if source:
            self.video_player_screen.set_source(source)
        self._sidebar_visible = False
        self._apply_sidebar_visibility()
        self.screen_stack.setCurrentWidget(self.video_player_screen)

    # -----------------------------------
    # サイドバー開閉
    # -----------------------------------
    def _toggle_sidebar(self) -> None:
        self._sidebar_visible = not self._sidebar_visible
        self._apply_sidebar_visibility()

    def _apply_sidebar_visibility(self) -> None:
        is_open = self._sidebar_visible
        self.sidebar.set_sidebar_open(is_open)
        self.separator.setVisible(is_open)

        if is_open:
            self._body_layout.setStretch(0, 1)
            self._body_layout.setStretch(2, 1)
        else:
            self._body_layout.setStretch(0, 0)
            self._body_layout.setStretch(2, 1)

        # 各画面にサイドバー状態を通知
        if hasattr(self.search_screen, 'set_sidebar_open'):
            self.search_screen.set_sidebar_open(is_open)
        if hasattr(self.video_player_screen, 'set_sidebar_open'):
            self.video_player_screen.set_sidebar_open(is_open)

    # -----------------------------------
    # ローディングオーバーレイ
    # -----------------------------------
    def show_loading(self):
        self.loading_overlay.show()
        self.loading_overlay.raise_()
        QApplication.processEvents()

    def hide_loading(self):
        self.loading_overlay.hide()
