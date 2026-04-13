# ui/widgets/video_player_view.py
"""
VideoPlayerView — 動画再生対応版
映像プレイヤー領域。cv2.VideoCapture + QPainter.drawImage() で MP4 を再生する。
再生/停止ボタン・シークバー・再生日時表示付き。
"""
import re
import logging
import sys
from datetime import datetime as _Datetime, timedelta
from pathlib import Path
from typing import Optional

import cv2

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import config

from ui_interface import RealtimeDetectionInterface

from PySide6.QtWidgets import (
    QWidget, QSizePolicy, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider, QStackedWidget,
)
from PySide6.QtCore import Qt, QSize, QTimer, Signal
from PySide6.QtGui import QImage, QPainter


def _frames_to_hms(frame: int, fps: float) -> str:
    total_sec = int(frame / fps) if fps > 0 else 0
    h = total_sec // 3600
    m = (total_sec % 3600) // 60
    s = total_sec % 60
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


class _VideoDisplayWidget(QWidget):
    """cv2 フレームを QPainter.drawImage() で描画するウィジェット。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet("background-color: black;")
        self._image: QImage | None = None
        self._aspect_w: int = 16
        self._aspect_h: int = 9

    def set_aspect_ratio(self, w: int, h: int) -> None:
        if w > 0 and h > 0:
            self._aspect_w = w
            self._aspect_h = h

    def set_image(self, image: QImage) -> None:
        self._image = image
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        if self._image is not None:
            # ウィジェット自体がアスペクト比に合わせてサイズ制御されるため IgnoreAspectRatio で描画
            scaled = self._image.scaled(
                self.width(), self.height(),
                Qt.IgnoreAspectRatio,
                Qt.SmoothTransformation,
            )
            painter.drawImage(0, 0, scaled)
        painter.end()


class VideoPlayerView(QWidget):
    """映像プレイヤー領域（再生/停止・シークバー・再生日時表示付き）。"""

    person_search_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._log = logging.getLogger("VideoPlayerView")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(320, 180)
        # 黒背景をスタイルシートで指定（paintEvent による余分な描画を排除）
        self.setStyleSheet("background-color: #141414;")

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 100, 0, 0)
        root_layout.setSpacing(0)

        # QStackedWidget でプレースホルダーと動画ウィジェットを切り替える
        self._video_stack = QStackedWidget(self)

        # プレースホルダー（動画未読み込み時 or エラー時）- index 0
        self._placeholder = QLabel("映像プレイヤー", self._video_stack)
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._placeholder.setStyleSheet("color: #888888; font-size: 18px; background: transparent;")
        self._video_stack.addWidget(self._placeholder)

        # 動画表示ウィジェット - index 1
        self._video_widget = _VideoDisplayWidget(self._video_stack)
        self._video_stack.addWidget(self._video_widget)

        root_layout.addWidget(self._video_stack, 1)

        # ---- コントロールバー ----
        self._control_bar = QWidget(self)
        self._control_bar.setStyleSheet("background-color: #FFFFFF;")
        self._control_bar.setVisible(False)
        ctrl_layout = QVBoxLayout(self._control_bar)
        ctrl_layout.setContentsMargins(8, 0, 8, 60)

        ctrl_layout.setSpacing(4)

        # 再生日時ラベル（seekbarの上）
        self._datetime_label = QLabel("", self._control_bar)
        self._datetime_label.setStyleSheet("color: #1a1a1a; font-size: 16px; padding-top: -50px;")
        self._datetime_label.setVisible(False)
        ctrl_layout.addWidget(self._datetime_label)

        # シークバー
        self._seek_slider = QSlider(Qt.Horizontal, self._control_bar)
        self._seek_slider.setRange(0, 0)
        self._seek_slider.setStyleSheet(
            """
            QSlider::groove:horizontal {
                height: 4px; background: #444444; border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 12px; height: 12px; margin: -4px 0;
                background: #1E88E5; border-radius: 6px;
            }
            QSlider::sub-page:horizontal {
                background: #1E88E5; border-radius: 2px;
            }
            """
        )
        ctrl_layout.addWidget(self._seek_slider)

        # 再生/停止ボタン + 時間表示
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(8)

        self._play_btn = QPushButton("▶ 再生", self._control_bar)
        self._play_btn.setFixedSize(80, 28)
        self._play_btn.setCursor(Qt.PointingHandCursor)
        self._play_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #1E88E5; color: #ffffff;
                border-radius: 4px; font-size: 16px;
            }
            QPushButton:hover { background-color: #1976D2; }
            """
        )
        btn_row.addWidget(self._play_btn)

        self._time_label = QLabel("00:00 / 00:00", self._control_bar)
        self._time_label.setStyleSheet("color: #1a1a1a; font-size: 16px;")
        btn_row.addWidget(self._time_label)
        btn_row.addStretch(1)

        ctrl_layout.addLayout(btn_row)
        root_layout.addWidget(self._control_bar)

        # cv2 関連
        self._cap: cv2.VideoCapture | None = None
        self._fps: float = 30.0
        self._total_frames: int = 0
        self._is_playing: bool = False

        # タイマー（フレーム更新用）
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_frame)

        # 開始日時（位置を実時刻に変換するために使用）
        self._start_datetime: _Datetime | None = None
        self._realtime_detection_enabled: bool = False
        self._camera_id: Optional[int] = None
        self._detection_iface: Optional[RealtimeDetectionInterface] = None

        # シグナル接続
        self._play_btn.clicked.connect(self._toggle_play_pause)
        self._seek_slider.sliderMoved.connect(self._seek_to_frame)

    # --- 公開API ---

    def load_video(
        self,
        path: str,
        datetime_str: str = "",
        camera_id: Optional[int] = None,
        realtime_detection: bool = False,
    ) -> None:
        """指定パスの動画ファイルを読み込んで再生する。

        Args:
            path: 動画ファイルのパス。
            datetime_str: コントロールバーに表示する再生日時文字列。省略時は非表示。
            camera_id: 速度測定用のカメラID。
            realtime_detection: True の場合は再生中フレームで検出・速度測定を行う。
        """
        self.set_realtime_detection_enabled(realtime_detection, camera_id=camera_id)

        if not Path(path).exists():
            self._placeholder.setText(f"動画ファイルが見つかりません:\n{path}")
            self._video_stack.setCurrentIndex(0)
            self._control_bar.setVisible(False)
            return

        # 既存のキャプチャを解放
        self._timer.stop()
        if self._cap is not None:
            self._cap.release()
            self._cap = None

        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            self._placeholder.setText(f"動画を開けませんでした:\n{path}")
            self._video_stack.setCurrentIndex(0)
            self._control_bar.setVisible(False)
            return

        self._cap = cap
        self._fps = self._cap.get(cv2.CAP_PROP_FPS) or 30.0
        self._total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self._reset_realtime_pipeline()

        # 動画解像度からアスペクト比を設定し、黒帯が出ないようウィジェット高さを更新
        vid_w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        vid_h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self._video_widget.set_aspect_ratio(vid_w, vid_h)
        self._update_video_stack_height()

        self._seek_slider.setRange(0, self._total_frames)
        self._seek_slider.setValue(0)
        self._update_time_label(0)

        self._video_stack.setCurrentIndex(1)
        self._control_bar.setVisible(True)

        # datetime_str の先頭にある "YYYY-MM-DD HH:MM:SS" を開始日時として解析
        self._start_datetime = None
        if datetime_str:
            m = re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', datetime_str)
            if m:
                try:
                    self._start_datetime = _Datetime.strptime(m.group(), "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    pass

        if datetime_str:
            self._datetime_label.setText(f"再生日時：{datetime_str}")
            self._datetime_label.setVisible(True)
        else:
            self._datetime_label.setVisible(False)

        self._is_playing = True
        self._play_btn.setText("⏸ 停止")
        self._timer.start(int(1000 / self._fps))

    # --- スロット ---

    def _toggle_play_pause(self) -> None:
        if self._cap is None:
            return
        self._is_playing = not self._is_playing
        if self._is_playing:
            self._play_btn.setText("⏸ 停止")
            self._timer.start(int(1000 / self._fps))
        else:
            self._play_btn.setText("▶ 再生")
            self._timer.stop()

    def _update_frame(self) -> None:
        if self._cap is None or not self._is_playing:
            return

        ret, frame = self._cap.read()
        if not ret:
            self._timer.stop()
            self._is_playing = False
            self._play_btn.setText("▶ 再生")
            return

        frame = self._apply_realtime_overlay(frame)

        current_frame = int(self._cap.get(cv2.CAP_PROP_POS_FRAMES))

        # シークバー更新（スライド中は上書きしない）
        if not self._seek_slider.isSliderDown():
            self._seek_slider.blockSignals(True)
            self._seek_slider.setValue(current_frame)
            self._seek_slider.blockSignals(False)

        self._update_time_label(current_frame)

        # BGR → RGB 変換して QImage に変換し QPainter で描画
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        q_img = QImage(frame_rgb.data, w, h, ch * w, QImage.Format_RGB888)
        self._video_widget.set_image(q_img.copy())

    def _seek_to_frame(self, frame_number: int) -> None:
        if self._cap is None:
            return
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        self._update_time_label(frame_number)

        # 一時停止中でもシーク先のフレームを即座に表示する
        if not self._is_playing:
            ret, frame = self._cap.read()
            if ret:
                frame = self._apply_realtime_overlay(frame)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = frame_rgb.shape
                q_img = QImage(frame_rgb.data, w, h, ch * w, QImage.Format_RGB888)
                self._video_widget.set_image(q_img.copy())

    def _update_time_label(self, current_frame: int) -> None:
        cur_str = _frames_to_hms(current_frame, self._fps)
        tot_str = _frames_to_hms(self._total_frames, self._fps)
        self._time_label.setText(f"{cur_str} / {tot_str}")

    # --- Qt overrides ---

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_video_stack_height()

    def _update_video_stack_height(self) -> None:
        """現在の幅と動画アスペクト比から _video_stack の最大高さを制限し黒帯を除去する。"""
        aw = self._video_widget._aspect_w
        ah = self._video_widget._aspect_h
        w = self.width()
        if aw <= 0 or ah <= 0 or w <= 0:
            return
        target_h = w * ah // aw
        self._video_stack.setMaximumHeight(target_h)

    def sizeHint(self) -> QSize:
        return QSize(960, 540)

    def set_sidebar_open(self, is_open: bool) -> None:
        pass

    def set_realtime_detection_enabled(self, enabled: bool, **kwargs) -> None:
        self._realtime_detection_enabled = enabled
        self._camera_id = kwargs.get("camera_id")
        self._reset_realtime_pipeline()

    def _reset_realtime_pipeline(self) -> None:
        self._detection_iface = None

    def _init_realtime_pipeline(self) -> bool:
        if not self._realtime_detection_enabled:
            return False
        if self._detection_iface is not None and self._detection_iface.is_initialized:
            return True

        iface = RealtimeDetectionInterface()
        if not iface.initialize(self._fps):
            self._log.error("リアルタイム検出初期化に失敗しました")
            self._realtime_detection_enabled = False
            self._detection_iface = None
            return False
        self._detection_iface = iface
        return True

    def _apply_realtime_overlay(self, frame):
        if not self._realtime_detection_enabled:
            return frame
        if not self._init_realtime_pipeline():
            return frame

        try:
            results = self._detection_iface.detect_and_track(frame)
            for result in results:
                x1, y1, x2, y2 = [int(v) for v in result.bbox]
                color = (
                    config.SPEED_WARNING_COLOR
                    if result.is_speeding
                    else config.SPEED_NORMAL_COLOR
                )
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, config.BBOX_THICKNESS)
                cv2.putText(
                    frame,
                    f"ID:{result.track_id} {result.speed_kmh:.1f}km/h",
                    (x1, max(y1 - 6, 0)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    config.FONT_SCALE,
                    color,
                    config.FONT_THICKNESS,
                )
        except Exception as exc:
            self._log.warning("リアルタイム検出中にエラーが発生しました: %s", exc)
            return frame

        return frame

    def updateGeometry(self) -> None:
        super().updateGeometry()
