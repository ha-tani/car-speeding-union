# video_utils.py
# 動画キャプチャのユーティリティ

import cv2
import config


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
                return cap
            cap.release()
        except Exception:
            pass
    return cv2.VideoCapture(path)
