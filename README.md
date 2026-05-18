# Car Speeding Detection System

車載カメラの映像を解析し、速度超過車両を自動検出・記録するシステムです。  
YOLOv8 + TensorRT による高速物体検出、ByteTracker によるオブジェクト追跡、透視変換を用いた速度推定を組み合わせています。

---

## 機能概要

- **動画フォルダ監視** — 指定フォルダを定期ポーリングし、新規動画ファイルを自動検出・解析
- **車両検出** — YOLOv8（TensorRT GPU 推論 / PyTorch CPU フォールバック）で車・バイク・バス・トラックを検出
- **速度推定** — 透視変換 + Kalman フィルタによる中央値スムージングで km/h を算出
- **ナンバープレート検出** — 速度超過車両のプレートを自動クロップ・保存
- **DB 登録** — 違反情報（速度・キャプチャ画像・タイムスタンプ）を PostgreSQL に保存
- **GUI** — PySide6 製の閲覧 UI（カメラ選択・違反一覧・動画プレイヤー）
- **キャリブレーションツール** — 道路の透視変換座標をドラッグ操作で視覚的に調整

---

## ディレクトリ構成

```
car-speeding-ui/
├── main.py                     # バックエンド起動エントリポイント（動画監視・解析）
├── config.py                   # 全設定（.env から読み込み）
├── video_utils.py              # VideoCapture ユーティリティ
├── db/
│   ├── db_connection.py        # PostgreSQL 接続プール
│   └── db_query.py             # CRUD クエリ
├── ui/
│   ├── app.py                  # GUI 起動エントリポイント
│   ├── main_window.py          # メインウィンドウ（画面遷移管理）
│   ├── screens/
│   │   ├── camera_select_screen.py         # カメラ選択画面
│   │   ├── violating_vehicle_info_screen.py # 違反車両一覧画面
│   │   └── video_player_screen.py          # 動画プレイヤー画面
│   └── widgets/                # 共通ウィジェット（ヘッダー・サイドバー等）
└── car_speeding_back/
    ├── pipeline/
    │   └── analysis_pipeline.py  # 解析パイプライン（オーケストレータ）
    ├── yolo/
    │   ├── detector_car.py       # 車両検出器（YOLO）
    │   ├── detector_np.py        # ナンバープレート検出器（YOLO）
    │   └── trt_inference.py      # TensorRT 推論エンジン
    ├── speed/
    │   ├── check_speed.py        # 速度推定（透視変換 + Kalman）
    │   ├── byte_tracker.py       # ByteTracker（CPU）
    │   └── byte_tracker_gpu.py   # ByteTracker（GPU 版）
    ├── image_src/
    │   └── image_capture.py      # 車両・プレート画像キャプチャ
    ├── tools/
    │   ├── calibration.py        # 透視変換キャリブレーションツール
    │   └── scale_calibration.py  # スケールキャリブレーションツール（多点対応）
    ├── export_engine.py          # TensorRT エンジンビルド
    ├── models/                   # YOLO モデル（.pt / .engine）
    └── video/                    # 入力動画フォルダ（カメラ名サブフォルダ）
```

---

## 必要環境

| コンポーネント | バージョン |
|---|---|
| Python | 3.10+ |
| CUDA | 12.x |
| TensorRT | 10.x |
| PostgreSQL | 16 |
| GPU | NVIDIA（TensorRT 使用時） |

主要 Python パッケージ（`requirements.txt` 参照）:

- `torch==2.5.1+cu121` / `torchvision==0.20.1+cu121`
- `tensorrt_cu12==10.16.0.72`
- `ultralytics==8.4.9`
- `opencv-python==4.13.0.92`
- `PySide6`
- `psycopg2`
- `filterpy`

---

## セットアップ

### 1. conda 環境の作成

```bash
conda env create -f environment.yml
conda activate car-speeding-env
```

または pip を使う場合:

```bash
pip install -r requirements.txt
```

### 2. 環境変数の設定

プロジェクトルートに `.env` ファイルを作成し、以下の変数を設定します。

```dotenv
# --- DB 接続 ---
DB_HOST=localhost
DB_PORT=5432
DB_NAME=vehicle_speed_db
DB_USER=vehicle_speed_app
DB_PASSWORD=your_password

# --- 推論設定 ---
USE_TENSORRT=true
USE_GPU=true
CAR_DETECTOR_MODEL=yolo26s     # yolov8s / yolo26n / yolo26s

# --- 速度設定 ---
SPEED_LIMIT=25.0               # 速度超過と判定する閾値 (km/h)

# --- キャリブレーション ---
CALIB_SRC_POINTS=[[279,381],[1255,436],[1066,599],[23,429]]
CALIB_ROAD_WIDTH=10.0          # 道路幅 (m)
CALIB_ROAD_DEPTH=3.5           # 奥行き (m)
```

### 3. データベースの準備

```bash
# PostgreSQL にデータベースとユーザーを作成後、バックアップから復元する場合
psql -U postgres -c "CREATE DATABASE vehicle_speed_db;"
psql -U postgres -c "CREATE USER vehicle_speed_app WITH PASSWORD 'your_password';"
psql -U vehicle_speed_app vehicle_speed_db < backup.sql
```

### 4. TensorRT エンジンのビルド（GPU 使用時）

```bash
python car_speeding_back/export_engine.py
```

事前に `car_speeding_back/models/` へ YOLO `.pt` モデルを配置してください。

---

## 使い方

### バックエンド（動画解析）

```bash
# 監視モード（video/ フォルダを自動ポーリング）
python main.py

# 監視フォルダを指定
python main.py --watch-dir C:\videos\incoming

# 単発モード（動画ファイルを直接指定）
python main.py --once car_speeding_back/video/camera1/20260402_102030.mp4 --camera-ids 1
```

動画ファイルのファイル名形式: `YYYYMMDD_HHMMSS.mp4`（例: `20260402_102030.mp4`）

### GUI（違反車両閲覧）

```bash
python ui/app.py
```

| 画面 | 説明 |
|---|---|
| カメラ選択 | 解析対象カメラと日時範囲を指定 |
| 違反車両一覧 | 速度超過車両の一覧・画像確認 |
| 動画プレイヤー | 該当シーンの動画再生・シーク |

### キャリブレーションツール

**透視変換座標の調整:**

```bash
python car_speeding_back/tools/calibration.py
```

**スケールキャリブレーション（多点対応）:**

```bash
python car_speeding_back/tools/scale_calibration.py
```

- 動画上の点をドラッグして座標を調整し、「Save to DB」でカメラ設定を DB に保存します。
- `D` キーで YOLO 検出 + 速度計測のオーバーレイ表示を ON/OFF できます。

---

## 主要設定項目（config.py）

| 変数 | デフォルト | 説明 |
|---|---|---|
| `USE_TENSORRT` | `true` | TensorRT 推論を使用するか |
| `USE_GPU` | `true` | GPU を使用するか |
| `CAR_DETECTOR_MODEL` | `yolo26s` | 車両検出モデル名 |
| `SPEED_LIMIT` | `25.0` | 速度超過閾値 (km/h) |
| `CONF_TH` | `0.25` | YOLO 検出信頼度しきい値 |
| `PIPELINE_MAX_WORKERS` | `5` | 並列処理ワーカー数 |
| `BYTE_TRACK_USE_GPU` | `false` | ByteTracker の GPU 処理 |
| `VIDEO_FPS` | `30` | 動画 FPS フォールバック値 |

---

## アーキテクチャ

```
動画ファイル
    ↓ (ポーリング検出)
main.py
    ↓ (非同期キュー)
analysis_pipeline.py
    ├── CarDetector (YOLO / TensorRT)
    │       ↓ バウンディングボックス
    ├── ByteTracker (CPU / GPU)
    │       ↓ トラック ID
    ├── SpeedTracker (透視変換 + Kalman)
    │       ↓ 速度 (km/h)
    ├── [速度超過判定]
    │       ↓
    ├── PlateDetector (YOLO / TensorRT)
    ├── image_capture (cv2.imwrite)
    └── db_query (PostgreSQL INSERT)
```

---

## 注意事項

- OCR（ナンバープレート文字認識）は現時点では未実装です。プレート番号は `NULL` で登録されます。
- TensorRT エンジンは GPU アーキテクチャごとに再ビルドが必要です。
- `.env` ファイルおよびモデルファイル（`.pt` / `.engine`）はリポジトリに含まれていません。別途用意してください。
