# video_utils.py
# 動画キャプチャのユーティリティ

import sys
import os
import cv2
import config

# car_speeding_back の get_logger を使用してコンソール・ファイル両方に出力
_BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "car_speeding_back")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)
from car_speeding_back.utils.logger import get_logger

_logger = get_logger(__name__)

# VIDEO_ACCELERATION_* の値を名前で逆引きするマップ
_HW_ACCEL_NAMES = {
    getattr(cv2, "VIDEO_ACCELERATION_NONE", 0): "NONE (CPU)",
    getattr(cv2, "VIDEO_ACCELERATION_ANY",  1): "ANY",
    getattr(cv2, "VIDEO_ACCELERATION_D3D11",2): "D3D11",
    getattr(cv2, "VIDEO_ACCELERATION_VAAPI",3): "VAAPI",
    getattr(cv2, "VIDEO_ACCELERATION_MFX",  4): "MFX (Intel QSV)",
}


def open_video_capture(path: str) -> cv2.VideoCapture:
    """
    動画ファイルを開く。
    USE_GPU=True の場合、FFmpeg ハードウェアアクセラレーション（NVDEC等）を
    試行し、失敗時は通常の CPU デコードにフォールバックする。
    """
    if config.USE_GPU:
        try:
            hw_accel = getattr(cv2, "CAP_PROP_HW_ACCELERATION", 50)
            hw_any = getattr(cv2, "VIDEO_ACCELERATION_ANY", 1)
            cap = cv2.VideoCapture(path, cv2.CAP_FFMPEG, [hw_accel, hw_any])
            if cap.isOpened():
                accel_val = int(cap.get(hw_accel))
                accel_name = _HW_ACCEL_NAMES.get(accel_val, f"UNKNOWN({accel_val})")
                _logger.info("[VideoCapture] デコード: GPU  accel=%s  file=%s", accel_name, path)
                return cap
            cap.release()
            _logger.warning("[VideoCapture] GPU デコード失敗 → CPU にフォールバック  file=%s", path)
        except Exception as e:
            _logger.warning("[VideoCapture] GPU デコード例外 → CPU にフォールバック  error=%s  file=%s", e, path)
    cap = cv2.VideoCapture(path)
    _logger.info("[VideoCapture] デコード: CPU  file=%s", path)
    return cap
