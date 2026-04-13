# ui/ui_interface.py
"""
UI ↔ バックエンド インターフェース

UIフォルダから car_speeding_back のメソッドを使用する際の中継レイヤー。
バックエンドへの直接依存を避けるため、ui フォルダ内のすべてのソースは
このモジュールを経由してバックエンド処理を呼び出してください。
"""
from __future__ import annotations

import logging
import sys
import traceback
from pathlib import Path
from typing import Optional

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import config

_BACKEND_DIR = Path(__file__).resolve().parents[1] / "car_speeding_back"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from car_speeding_back.yolo.detector_yolo import YoloDetector
from car_speeding_back.speed.check_speed import SpeedTracker


class RealtimeDetectionInterface:
    """リアルタイム車両検出インターフェース（バックエンド中継クラス）。

    VideoPlayerView から CarDetector / SpeedTracker を直接参照せず、
    必ずこのクラスを経由してください。
    """

    def __init__(self) -> None:
        self._log = logging.getLogger("RealtimeDetectionInterface")
        self._car_detector: Optional[YoloDetector] = None
        self._speed_tracker: Optional[SpeedTracker] = None

    @property
    def is_initialized(self) -> bool:
        return self._car_detector is not None and self._speed_tracker is not None

    def initialize(self, fps: float) -> bool:
        """YoloDetector と SpeedTracker を初期化する。

        Args:
            fps: 動画のフレームレート。
        Returns:
            初期化に成功した場合 True。
        """
        try:
            src_points = config.CALIB_SRC_POINTS
            road_width = config.CALIB_ROAD_WIDTH
            road_depth = config.CALIB_ROAD_DEPTH
            dst_points = [
                [0.0, 0.0],
                [road_width, 0.0],
                [road_width, road_depth],
                [0.0, road_depth],
            ]
            self._car_detector = YoloDetector()
            self._speed_tracker = SpeedTracker(
                src_points,
                dst_points,
                fps,
                speed_threshold_kmh=config.SPEED_LIMIT,
            )
            return True
        except Exception as exc:
            self._log.error("検出パイプラインの初期化に失敗しました: %s", exc)
            self._log.error("スタックトレース:\n%s", traceback.format_exc())
            self.reset()
            return False

    def detect_and_track(self, frame) -> list:
        """フレームを解析して車両のトラッキング結果リストを返す。

        Args:
            frame: OpenCV BGR ndarray。
        Returns:
            SpeedTracker.process_frame の戻り値リスト。
            未初期化または例外時は空リスト。
        """
        if not self.is_initialized:
            return []
        detections = self._car_detector.detect_cars(frame)
        return self._speed_tracker.process_frame(detections)

    def reset(self) -> None:
        """検出パイプラインをリセットする。"""
        self._car_detector = None
        self._speed_tracker = None