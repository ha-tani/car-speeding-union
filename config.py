# config.py
# アプリ全体の設定を一元管理する

from pathlib import Path

# -------------------------
# パス設定
# -------------------------
BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "car_speeding_back" / "models"
ENGINES_DIR = BASE_DIR / "car_speeding_back" / "engines"
VIDEO_DIR = BASE_DIR / "video"          # 動画ルートフォルダ: video/カメラ名/日時.mp4

# TensorRT設定
USE_TENSORRT = True  # True: TensorRTエンジン使用, False: PyTorchモデル使用
TENSORRT_BATCH_SIZE = 512  # TensorRTバッチ推論のバッチサイズ
YOLO_ENGINE_PATH = MODELS_DIR / "yolov8s.engine"
YOLO_PLATE_ENGINE_PATH = MODELS_DIR / "yolov8n-np.engine"
YOLO_MODEL_PATH = MODELS_DIR / "yolov8s.pt"
YOLO_PLATE_MODEL_PATH = MODELS_DIR / "yolov8n-np.pt"  # ナンバープレート検出専用モデル
FAST_PLATE_OCR_MODEL_DIR = MODELS_DIR / "fast-plate-ocr"  # fast-plate-ocrモデル保存先

# -------------------------
# YOLO設定
# -------------------------
# COCO想定: car=2, motorcycle=3, bus=5, truck=7
# 複数クラスを検出対象に
VEHICLE_CLASS_IDS = [2, 3, 5, 7]  # 車、バイク、バス、トラック
CAR_CLASS_ID = 2  # 後方互換性のため維持
CONF_TH = 0.3  # 誤検出を抑えつつ検出漏れを防ぐバランス値
NMS_IOU_TH = 0.3  # YOLO NMS の IoU 閾値
MIN_BBOX_SIZE = 30  # 最小BBoxサイズ [px] (これ未満の検出は除外)
PLATE_CONF_TH = 0.25  # ナンバープレート検出の信頼度閾値

# -------------------------
# デバイス設定
# -------------------------
USE_GPU = True  # False にすると強制CPU

# -------------------------
# 描画設定
# -------------------------
BBOX_COLOR = (0, 255, 0)   # Green
BBOX_THICKNESS = 2
FONT_SCALE = 0.6
FONT_THICKNESS = 2

# 速度超過警告設定
SPEED_WARNING_COLOR = (0, 0, 255)  # Red (赤色)
SPEED_NORMAL_COLOR = (0, 255, 0)   # Green (緑色)

# ナンバープレートBBOX設定
PLATE_BBOX_NORMAL_COLOR = (255, 255, 0)   # Cyan (水色 - BGR)
PLATE_BBOX_THICKNESS = 2

# -------------------------
# UI設定
# -------------------------
WINDOW_NAME = "Vehicle Player"
RIBBON_HEIGHT = 110      # 画面上部リボンの高さ
SEEKBAR_HEIGHT = 40  # シークバー領域の高さ
BUTTON_AREA_HEIGHT = 40  # ボタン領域の高さ

# 表示サイズ制限（画面に収まるよう自動縮小）
MAX_DISPLAY_WIDTH = 1280
MAX_DISPLAY_HEIGHT = 720

# -------------------------
# 速度推定設定
# -------------------------
SPEED_SMOOTHING_WINDOW = 15   # 速度スムージングのフレーム数
SPEED_HISTORY_SIZE = 20       # 位置履歴の保持フレーム数
SPEED_MIN_THRESHOLD_KMH = 3.0 # この速度以下は停車とみなす [km/h]
SPEED_MIN_PIXEL_MOVEMENT = 3.0 # このピクセル以下の移動はノイズとみなす
SPEED_MAX_LIMIT = 80.0 # 速度上限 [km/h] (これ以上は異常値とみなしBBOX非表示)
SPEED_LIMIT = 25.0 # 速度制限 [km/h] (DB未設定時のフォールバック値)
TRACK_MIN_AGE_FRAMES = 10     # この検出フレーム数未満のトラックは速度計算しない

# -------------------------
# ByteTrack 設定
# -------------------------
BYTE_TRACK_MAX_AGE = 10           # トラック消滅までの最大未検出フレーム数
BYTE_TRACK_MIN_HITS = 1           # トラック出力に必要な最小連続検出数
BYTE_TRACK_IOU_THRESHOLD = 0.15   # 1st association の IoU 閾値
BYTE_TRACK_HIGH_THRESH = 0.5      # 高信頼度検出の闾値
BYTE_TRACK_LOW_THRESH = 0.1       # 低信頼度検出の下限 (2nd association 用)
BYTE_TRACK_SECOND_IOU_THRESH = 0.3  # 2nd association の IoU 閾値

# -------------------------
# 静止車両フィルタ設定
# -------------------------
STATIONARY_FILTER_FRAMES = 5  # 静止判定に使う位置履歴のフレーム数
STATIONARY_MIN_DISPLACEMENT = 10 # この距離 [px] 未満の変位なら静止とみなす
STATIONARY_OVERLAP_IOU_TH = 0.2  # 非移動トラックが移動車両と重複していると判断する IoU 閾値

# -------------------------
# キャリブレーション設定
# -------------------------
CALIB_SRC_POINTS = [[279, 381], [1255, 436], [1066, 599], [23, 429]] # 画像内の4参照点 (左上→右上→右下→左下) [ピクセル座標]
CALIB_ROAD_WIDTH = 10.0 # 横幅 (道路の幅) 実世界の道路サイズ [メートル]
CALIB_ROAD_DEPTH = 3.5 # 奥行 (進行方向の長さ) 実世界の道路サイズ [メートル]
VIDEO_FPS = 30 # フレームレート [fps] 

# -------------------------
# DB接続設定
# -------------------------
DB_HOST     = "localhost"
DB_PORT     = 5432
DB_NAME     = "vehicle_speed_db"
DB_USER     = "vehicle_speed_app"
DB_PASSWORD = "cosmo#1752"
DB_CONNECT_TIMEOUT = 10
DB_CLIENT_ENCODING = "UTF8"

# -------------------------
# パイプライン設定
# -------------------------
PIPELINE_MAX_WORKERS = 2  # 同時に解析する動画の最大数（2以下でも実行可能）
CAPTURE_DIR_CAR = BASE_DIR / "image" / "car"      # 車両キャプチャ保存先
CAPTURE_DIR_PLATE = BASE_DIR / "image" / "plate"   # プレートキャプチャ保存先

# -------------------------
# 開発モード設定
# -------------------------
DEV_MODE = True  # True: 結果JSONを result/ に出力する / False: JSON出力しない