# main.py
# アプリ起動エントリポイント
#
# 【フォルダ構成】
#   入力  : video/<カメラ名>/<日時>.mp4
#             例) video/camera1/20260402-102030.mp4
#   解析後: video/processed/<カメラ名>/<日時ファイル名>
#             例) video/processed/camera1/20260402-102030.mp4
#
# 【動作モード】
#   監視モード（デフォルト）:
#     指定フォルダを定期的にポーリングし、新しい動画を自動解析する。
#     Ctrl+C で安全に停止できる。
#
#   単発モード（--once）:
#     引数で指定した動画を解析して終了する。
#
# 【使用例】
#   # 監視モード: video/ フォルダを監視（デフォルト）
#   python main.py
#
#   # 監視モード: フォルダを明示指定
#   python main.py --watch-dir C:\videos\incoming
#
#   # 単発モード: 動画を直接指定して解析
#   python main.py --once video/camera1/20260402-102030.mp4 --camera-ids 1

import sys
import argparse
import asyncio
import os
import shutil
import signal
import time
from pathlib import Path

import config
from car_speeding_back.pipeline.analysis_pipeline import VideoTask, run_analysis_pipeline
from db.db_query import get_camera_by_name
from car_speeding_back.utils.logger import get_logger

logger = get_logger(__name__)

# 解析対象の拡張子
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}

# 監視モードで使う停止フラグ
_stop_event = asyncio.Event()


# ---------------------------------------------------------------------------
# シグナルハンドラ（Ctrl+C で安全停止）
# ---------------------------------------------------------------------------

def _handle_signal(sig, frame):
    logger.info("停止シグナルを受信しました。現在の解析が完了後に終了します...")
    _stop_event.set()


# ---------------------------------------------------------------------------
# 解析済みファイル管理
# ---------------------------------------------------------------------------

def _load_processed(processed_log: Path) -> set[str]:
    """解析済みファイルパスのセットをログファイルから読み込む。"""
    if not processed_log.exists():
        return set()
    with open(processed_log, encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def _save_processed(processed_log: Path, path: str):
    """解析済みファイルパスをログファイルに追記する。"""
    with open(processed_log, "a", encoding="utf-8") as f:
        f.write(path + "\n")


def _find_new_videos(watch_dir: Path, processed: set[str]) -> list[tuple[Path, str]]:
    """
    監視フォルダ配下の video/<カメラ名>/ サブフォルダから未解析の動画を探す。

    Returns
    -------
    list of (Path, camera_name)
        (動画ファイルパス, カメラ名) のリスト。カメラ名はサブフォルダ名。
        ファイルが書き込み中（サイズが変化している）のものは除外する。
    """
    new_files: list[tuple[Path, str]] = []

    # watch_dir/<カメラ名>/ 以下を走査（processed/ サブフォルダは除外）
    for camera_dir in sorted(watch_dir.iterdir()):
        if not camera_dir.is_dir():
            continue
        if camera_dir.name == "processed":
            continue

        camera_name = camera_dir.name

        # glob は大文字小文字両方で検索（Windows は大小文字無視なので重複が出る）
        # resolve() で正規化してからsetで重複除去
        seen: set[Path] = set()
        candidates: list[Path] = []
        for ext in VIDEO_EXTENSIONS:
            for p in list(camera_dir.glob(f"*{ext}")) + list(camera_dir.glob(f"*{ext.upper()}")):
                rp = p.resolve()
                if rp not in seen:
                    seen.add(rp)
                    candidates.append(p)

        for path in sorted(candidates):
            if str(path) in processed:
                continue
            # 書き込み中チェック: 0.5秒後にサイズが変わっていたら除外
            try:
                size1 = path.stat().st_size
                time.sleep(0.5)
                size2 = path.stat().st_size
                if size1 != size2:
                    logger.debug(f"書き込み中のためスキップ: {path.name}")
                    continue
            except OSError:
                continue
            new_files.append((path, camera_name))

    return new_files


def _move_to_processed(video_path: Path, camera_name: str, processed_base: Path):
    """
    解析済み動画を processed_base/<カメラ名>/<ファイル名> へ移動する。
    同名ファイルが既にある場合は連番を付ける。
    """
    dest_dir = processed_base / camera_name
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest = dest_dir / video_path.name
    if dest.exists():
        stem = video_path.stem
        suffix = video_path.suffix
        i = 1
        while dest.exists():
            dest = dest_dir / f"{stem}_{i}{suffix}"
            i += 1

    shutil.move(str(video_path), str(dest))
    logger.info(f"解析済みフォルダへ移動: {dest}")


# ---------------------------------------------------------------------------
# 解析実行
# ---------------------------------------------------------------------------

async def _analyze(
    video_paths: list[str],
    camera_names: list[str | None],
    speed_limit: float | None,
    fps: float | None,
    max_workers: int | None,
):
    """指定された動画リストを解析してサマリをログ出力する。"""
    tasks = []
    for vp, camera_name in zip(video_paths, camera_names):
        camera_id = None
        src_points = None
        road_width = None
        road_depth = None
        db_speed_limit = None
        if camera_name:
            try:
                cam = get_camera_by_name(camera_name)
                if cam is None:
                    logger.warning(
                        f"cameras テーブルにカメラ名 '{camera_name}' が見つかりません。"
                        f"config のデフォルト値で処理を続行します。"
                    )
                else:
                    camera_id  = cam["camera_id"]
                    src_points = cam["road_range"]
                    road_width = cam["road_width"]
                    road_depth = cam["road_depth"]
                    db_speed_limit = cam["speed_limit"]
                    logger.info(
                        f"カメラ設定取得: camera_name={camera_name}, "
                        f"camera_id={camera_id}, "
                        f"road_width={road_width}, road_depth={road_depth}, "
                        f"speed_limit={db_speed_limit}"
                    )
            except Exception as e:
                logger.warning(
                    f"カメラ情報取得失敗 (camera_name={camera_name}): {e}。"
                    f"config のデフォルト値で処理を続行します。"
                )
        tasks.append(
            VideoTask(
                video_path=vp,
                camera_id=camera_id,
                src_points=src_points,
                road_width=road_width,
                road_depth=road_depth,
                fps=fps,
                speed_limit_kmh=speed_limit or db_speed_limit,
            )
        )

    logger.info(f"解析開始: {len(tasks)} 本")
    for t, name in zip(tasks, camera_names):
        logger.info(f"  - {t.video_path} (camera={name})")

    violations = await run_analysis_pipeline(tasks, max_workers=max_workers)

    # サマリ出力
    print(f"\n=== 解析結果サマリ ===")
    print(f"処理動画数  : {len(tasks)}")
    print(f"違反検出数  : {len(violations)}")
    if violations:
        print(f"{'─' * 60}")
        for v in violations:
            print(
                f"  event_id={v.event_id} | track_id={v.track_id} | "
                f"{v.speed_kmh:.1f}km/h (超過{v.excess_speed:.1f}km/h) | "
                f"camera_id={v.camera_id} | {v.detected_at:%Y-%m-%d %H:%M:%S}"
            )

    return violations


# ---------------------------------------------------------------------------
# 監視モード
# ---------------------------------------------------------------------------

async def run_watch_mode(args):
    """
    video/<カメラ名>/ サブフォルダを定期的にポーリングして新しい動画を自動解析する。
    解析後は video/processed/<カメラ名>/<ファイル名> へ移動する。
    Ctrl+C（SIGINT / SIGTERM）で安全に停止する。
    """
    watch_dir = Path(args.watch_dir).resolve()
    processed_base = watch_dir / "processed"
    processed_log = watch_dir / ".processed.log"

    if not watch_dir.exists():
        logger.error(f"監視フォルダが見つかりません: {watch_dir}")
        sys.exit(1)

    logger.info(f"監視モード開始")
    logger.info(f"  監視フォルダ  : {watch_dir}")
    logger.info(f"  解析済み移動先: {processed_base}/<カメラ名>/")
    logger.info(f"  ポーリング間隔: {args.interval} 秒")
    logger.info(f"  制限速度      : {args.speed_limit or config.SPEED_LIMIT} km/h")
    logger.info("Ctrl+C で停止")

    processed = _load_processed(processed_log)
    loop = asyncio.get_running_loop()

    while not _stop_event.is_set():
        # _find_new_videos は time.sleep を含む同期処理なので
        # スレッドで実行してイベントループをブロックしない
        try:
            new_videos = await loop.run_in_executor(
                None, _find_new_videos, watch_dir, processed
            )
        except Exception as e:
            logger.error(f"フォルダ監視エラー: {e}。{args.interval} 秒後に再試行...")
            try:
                await asyncio.wait_for(_stop_event.wait(), timeout=args.interval)
            except asyncio.TimeoutError:
                pass
            continue

        if new_videos:
            logger.info(f"新しい動画を {len(new_videos)} 本検出")
            video_paths = [str(p) for p, _ in new_videos]
            camera_names = [name for _, name in new_videos]

            try:
                await _analyze(
                    video_paths=video_paths,
                    camera_names=camera_names,
                    speed_limit=args.speed_limit,
                    fps=args.fps,
                    max_workers=args.max_workers,
                )
            except Exception as e:
                logger.error(f"解析エラー: {e}")

            # 解析済みとして記録・移動（移動成功後にログ記録）
            for path, camera_name in new_videos:
                try:
                    _move_to_processed(path, camera_name, processed_base)
                    _save_processed(processed_log, str(path))
                    processed.add(str(path))
                except Exception as e:
                    logger.warning(f"ファイル移動失敗（次のポーリングで再試行します）: {e}")
        else:
            logger.debug(f"新しい動画なし。{args.interval} 秒後に再確認...")

        # 停止フラグを確認しながら待機
        try:
            await asyncio.wait_for(_stop_event.wait(), timeout=args.interval)
        except asyncio.TimeoutError:
            pass

    logger.info("監視モードを終了しました")


# ---------------------------------------------------------------------------
# 単発モード
# ---------------------------------------------------------------------------

async def run_once_mode(args):
    """指定された動画を解析して終了する。"""
    if not args.videos:
        print("error: --once モードでは動画ファイルを指定してください")
        sys.exit(1)

    # camera_names: --camera-ids が指定された場合はその値を文字列として使用、
    # なければ親フォルダ名をカメラ名とする
    if args.camera_ids:
        if len(args.camera_ids) != len(args.videos):
            print(
                f"error: --camera-ids の数({len(args.camera_ids)})が "
                f"動画数({len(args.videos)})と一致しません"
            )
            sys.exit(1)
        camera_names = [str(cid) for cid in args.camera_ids]
    else:
        camera_names = [Path(vp).parent.name for vp in args.videos]

    await _analyze(
        video_paths=args.videos,
        camera_names=camera_names,
        speed_limit=args.speed_limit,
        fps=args.fps,
        max_workers=args.max_workers,
    )


# ---------------------------------------------------------------------------
# 引数パース
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="車両速度違反検出パイプライン",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=r"""
使用例:
  # 監視モード（デフォルト: video/ フォルダを監視）
  python main.py

  # 監視モード（フォルダを明示指定）
  python main.py --watch-dir C:\videos\incoming

  # 単発モード（動画を直接指定して解析後に終了）
  python main.py --once video/camera1/20260402-102030.mp4

フォルダ構成:
  入力  : <watch-dir>/<カメラ名>/<日時>.mp4
  解析後: <watch-dir>/processed/<カメラ名>/<日時>.mp4
""",
    )

    # モード選択
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--watch-dir",
        type=str,
        default=str(config.VIDEO_DIR),
        help=f"監視フォルダのパス（デフォルト: {config.VIDEO_DIR}）",
    )
    mode.add_argument(
        "--once",
        action="store_true",
        help="単発モード: 動画を直接指定して解析後に終了",
    )

    # 単発モード用
    parser.add_argument(
        "videos",
        nargs="*",
        help="解析対象の動画ファイルパス（--once 時に指定）",
    )
    parser.add_argument(
        "--camera-ids",
        nargs="*",
        type=int,
        default=None,
        help="各動画に対応するカメラID（動画数と同数指定、省略時は親フォルダ名を使用）",
    )

    # 監視モード用
    parser.add_argument(
        "--interval",
        type=int,
        default=10,
        help="ポーリング間隔（秒）（デフォルト: 10）",
    )

    # 共通オプション
    parser.add_argument(
        "--speed-limit",
        type=float,
        default=None,
        help=f"制限速度 km/h (デフォルト: config.SPEED_LIMIT={config.SPEED_LIMIT})",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=None,
        help=f"フレームレート (デフォルト: 動画メタデータから自動取得)",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help=f"並列ワーカー数 (デフォルト: config.PIPELINE_MAX_WORKERS={config.PIPELINE_MAX_WORKERS})",
    )

    return parser.parse_args()


# ---------------------------------------------------------------------------
# エントリポイント
# ---------------------------------------------------------------------------

async def main():
    args = parse_args()

    # シグナルハンドラを登録（Ctrl+C / SIGTERM で安全停止）
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    if args.once:
        await run_once_mode(args)
    else:
        await run_watch_mode(args)


if __name__ == "__main__":
    asyncio.run(main())
