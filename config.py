# config.py
# アプリ全体の設定を一元管理する
# 設定値は .env ファイルに記載する

import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# -------------------------
# パス設定
# -------------------------
BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "car_speeding_back" / "models"
ENGINES_DIR = BASE_DIR / "car_speeding_back" / "engines"
VIDEO_DIR = BASE_DIR / "car_speeding_back" / "video"       # 動画ルートフォルダ: video/カメラ名/日時.mp4

# -------------------------
# TensorRT設定
# -------------------------
USE_TENSORRT = os.getenv("USE_TENSORRT", "true").lower() == "true"
TENSORRT_BATCH_SIZE = int(os.getenv("TENSORRT_BATCH_SIZE", "128"))
YOLO_DETECT_BATCH_SIZE = int(os.getenv("YOLO_DETECT_BATCH_SIZE", "128"))
NUM_READ_WORKERS = int(os.getenv("NUM_READ_WORKERS", "3"))
WORKER_QUEUE_MAX_BATCHES = int(os.getenv("WORKER_QUEUE_MAX_BATCHES", "8"))

# -------------------------
# 車検出モデル選択
# -------------------------
CAR_DETECTOR_MODEL = os.getenv("CAR_DETECTOR_MODEL", "yolo26s")

_CAR_MODEL_PATHS = {
    "yolov8s": (MODELS_DIR / "yolov8s.engine", MODELS_DIR / "yolov8s.pt"),
    "yolo26n": (MODELS_DIR / "yolo26n.engine", MODELS_DIR / "yolo26n.pt"),
    "yolo26s": (MODELS_DIR / "yolo26s.engine", MODELS_DIR / "yolo26s.pt"),
}
YOLO_ENGINE_PATH, YOLO_MODEL_PATH = _CAR_MODEL_PATHS[CAR_DETECTOR_MODEL]

# モデルごとのTensorRT最大バッチサイズ (エンジンビルド時の max_batch に合わせること)
_CAR_MODEL_MAX_BATCH = {
    "yolov8s": 128,
    "yolo26n": 128,
    "yolo26s": 128,
}
YOLO_ENGINE_MAX_BATCH = _CAR_MODEL_MAX_BATCH[CAR_DETECTOR_MODEL]

YOLO_PLATE_ENGINE_PATH = MODELS_DIR / "yolov8n-np.engine"
YOLO_PLATE_MODEL_PATH = MODELS_DIR / "yolov8n-np.pt"  # ナンバープレート検出専用モデル
FAST_PLATE_OCR_MODEL_DIR = MODELS_DIR / "fast-plate-ocr"  # fast-plate-ocrモデル保存先

# -------------------------
# YOLO設定
# -------------------------
VEHICLE_CLASS_IDS = json.loads(os.getenv("VEHICLE_CLASS_IDS", "[2,3,5,7]"))  # 車、バイク、バス、トラック
CAR_CLASS_ID = int(os.getenv("CAR_CLASS_ID", "2"))  # 後方互換性のため維持
CONF_TH = float(os.getenv("CONF_TH", "0.25"))
NMS_IOU_TH = float(os.getenv("NMS_IOU_TH", "0.1"))
MIN_BBOX_SIZE = int(os.getenv("MIN_BBOX_SIZE", "0"))
PLATE_CONF_TH = float(os.getenv("PLATE_CONF_TH", "0.25"))
YOLO_INFER_SKIP = int(os.getenv("YOLO_INFER_SKIP", "1"))

# -------------------------
# デバイス設定
# -------------------------
USE_GPU = os.getenv("USE_GPU", "true").lower() == "true"

# -------------------------
# 描画設定
# -------------------------
BBOX_COLOR = tuple(json.loads(os.getenv("BBOX_COLOR", "[0,255,0]")))
BBOX_THICKNESS = int(os.getenv("BBOX_THICKNESS", "2"))
FONT_SCALE = float(os.getenv("FONT_SCALE", "0.6"))
FONT_THICKNESS = int(os.getenv("FONT_THICKNESS", "2"))

# 速度超過警告設定
SPEED_WARNING_COLOR = tuple(json.loads(os.getenv("SPEED_WARNING_COLOR", "[0,0,255]")))
SPEED_NORMAL_COLOR = tuple(json.loads(os.getenv("SPEED_NORMAL_COLOR", "[0,255,0]")))

# ナンバープレートBBOX設定
PLATE_BBOX_NORMAL_COLOR = tuple(json.loads(os.getenv("PLATE_BBOX_NORMAL_COLOR", "[255,255,0]")))
PLATE_BBOX_THICKNESS = int(os.getenv("PLATE_BBOX_THICKNESS", "2"))

# -------------------------
# UI設定
# -------------------------
WINDOW_NAME = os.getenv("WINDOW_NAME", "Vehicle Player")
RIBBON_HEIGHT = int(os.getenv("RIBBON_HEIGHT", "110"))        # 画面上部リボンの高さ
SEEKBAR_HEIGHT = int(os.getenv("SEEKBAR_HEIGHT", "40"))       # シークバー領域の高さ
BUTTON_AREA_HEIGHT = int(os.getenv("BUTTON_AREA_HEIGHT", "40"))  # ボタン領域の高さ

# 表示サイズ制限（画面に収まるよう自動縮小）
MAX_DISPLAY_WIDTH = int(os.getenv("MAX_DISPLAY_WIDTH", "1280"))
MAX_DISPLAY_HEIGHT = int(os.getenv("MAX_DISPLAY_HEIGHT", "720"))

# -------------------------
# 速度推定設定
# -------------------------
SPEED_SMOOTHING_WINDOW = int(os.getenv("SPEED_SMOOTHING_WINDOW", "6"))
SPEED_HISTORY_SIZE = int(os.getenv("SPEED_HISTORY_SIZE", "20"))
SPEED_MIN_THRESHOLD_KMH = float(os.getenv("SPEED_MIN_THRESHOLD_KMH", "3.0"))
SPEED_MIN_PIXEL_MOVEMENT = float(os.getenv("SPEED_MIN_PIXEL_MOVEMENT", "2.0"))
SPEED_MAX_LIMIT = float(os.getenv("SPEED_MAX_LIMIT", "80.0"))
SPEED_LIMIT = float(os.getenv("SPEED_LIMIT", "25.0"))  # DB未設定時のフォールバック値
BBOX_OVERLAP_SPEED_SPIKE_IOU_TH = float(os.getenv("BBOX_OVERLAP_SPEED_SPIKE_IOU_TH", "0.2"))
BBOX_OVERLAP_SPEED_SPIKE_RATIO = float(os.getenv("BBOX_OVERLAP_SPEED_SPIKE_RATIO", "2.0"))
MAX_CENTROID_JUMP_PX = int(os.getenv("MAX_CENTROID_JUMP_PX", "60"))
TRACK_MIN_AGE_FRAMES = int(os.getenv("TRACK_MIN_AGE_FRAMES", "6"))

# -------------------------
# ByteTrack 設定
# -------------------------
BYTE_TRACK_MAX_AGE = int(os.getenv("BYTE_TRACK_MAX_AGE", "10"))
BYTE_TRACK_MIN_HITS = int(os.getenv("BYTE_TRACK_MIN_HITS", "1"))
BYTE_TRACK_IOU_THRESHOLD = float(os.getenv("BYTE_TRACK_IOU_THRESHOLD", "0.15"))
BYTE_TRACK_HIGH_THRESH = float(os.getenv("BYTE_TRACK_HIGH_THRESH", "0.5"))
BYTE_TRACK_LOW_THRESH = float(os.getenv("BYTE_TRACK_LOW_THRESH", "0.1"))
BYTE_TRACK_SECOND_IOU_THRESH = float(os.getenv("BYTE_TRACK_SECOND_IOU_THRESH", "0.3"))
BYTE_TRACK_USE_GPU = os.getenv("BYTE_TRACK_USE_GPU", "false").lower() == "true"

# -------------------------
# 静止車両フィルタ設定
# -------------------------
# ENABLE_STATIONARY_FILTER: False にすると _is_stationary が常に False を返し、
# 静止判定によるトラックスキップ・長期静止リセット処理がまるごと無効化される。
ENABLE_STATIONARY_FILTER = os.getenv("ENABLE_STATIONARY_FILTER", "true").lower() == "true"
STATIONARY_FILTER_FRAMES = int(os.getenv("STATIONARY_FILTER_FRAMES", "5"))
STATIONARY_MIN_DISPLACEMENT = int(os.getenv("STATIONARY_MIN_DISPLACEMENT", "7"))  # パス2(速度計算)で使用
PROBE_STATIONARY_MIN_DISPLACEMENT = int(os.getenv("PROBE_STATIONARY_MIN_DISPLACEMENT", "7"))  # パス1/1.5(probe静止判定)で使用
STATIONARY_OVERLAP_IOU_TH = float(os.getenv("STATIONARY_OVERLAP_IOU_TH", "0.2"))

# -------------------------
# キャリブレーション設定
# -------------------------
CALIB_SRC_POINTS = json.loads(os.getenv("CALIB_SRC_POINTS", "[[279,381],[1255,436],[1066,599],[23,429]]"))
CALIB_ROAD_WIDTH = float(os.getenv("CALIB_ROAD_WIDTH", "10.0"))
CALIB_ROAD_DEPTH = float(os.getenv("CALIB_ROAD_DEPTH", "3.5"))
VIDEO_FPS = int(os.getenv("VIDEO_FPS", "30"))

# -------------------------
# DB接続設定
# -------------------------
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "vehicle_speed_db")
DB_USER = os.getenv("DB_USER", "vehicle_speed_app")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_CONNECT_TIMEOUT = int(os.getenv("DB_CONNECT_TIMEOUT", "10"))
DB_CLIENT_ENCODING = os.getenv("DB_CLIENT_ENCODING", "UTF8")

# -------------------------
# パイプライン設定
# -------------------------
PIPELINE_MAX_WORKERS = int(os.getenv("PIPELINE_MAX_WORKERS", "5"))
CAPTURE_DIR_CAR = BASE_DIR / "image" / "car"      # 車両キャプチャ保存先
CAPTURE_DIR_PLATE = BASE_DIR / "image" / "plate"   # プレートキャプチャ保存先

# -------------------------
# 開発モード設定
# -------------------------
DEV_MODE = os.getenv("DEV_MODE", "true").lower() == "true"

# -------------------------
# OCR設定
# -------------------------
USE_OCR = os.getenv("USE_OCR", "true").lower() == "true"