# ui/search_video.py
"""
動画検索・切り出しユーティリティ

find_and_clip_video(detected_at, camera_id) -> str | None
  detected_at   : datetime または "YYYY-MM-DD HH:MM:SS" 形式の文字列
  camera_id     : int (1=cameraA, 2=cameraB, 3=cameraC)
  戻り値        : ffmpeg で切り出した一時ファイルのパス。失敗時は None。
"""
from __future__ import annotations

import logging
import os
import re
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

log = logging.getLogger(__name__)

_BASE_DIR: Path = Path(__file__).resolve().parent.parent
_FFMPEG_EXE: Path = _BASE_DIR / "ffmpeg" / "ffmpeg" / "bin" / "ffmpeg.exe"
_VIDEOS_DIR: Path = _BASE_DIR / "videos"
_CAMERA_FOLDER_MAP: dict[int, str] = {1: "cameraA", 2: "cameraB", 3: "cameraC"}
_VIDEO_PATTERN = re.compile(r"^(\d{8}_\d{6})\.(avi|mp4)$", re.IGNORECASE)


def find_and_clip_video(
    detected_at: datetime | str,
    camera_id: int,
) -> str | None:
    """
    detected_at と camera_id から動画ファイルを特定し、
    ffmpeg で検知時刻からの切り出しを行って一時ファイルのパスを返す。
    失敗した場合は None を返す。
    """
    # detected_at を datetime に統一
    if isinstance(detected_at, str):
        try:
            detected_at_dt = datetime.strptime(detected_at[:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            log.error("detected_at の解析に失敗しました: %s", detected_at)
            return None
    else:
        detected_at_dt = datetime(
            detected_at.year, detected_at.month, detected_at.day,
            detected_at.hour, detected_at.minute, detected_at.second,
        )

    folder = _CAMERA_FOLDER_MAP.get(camera_id)
    if folder is None:
        log.warning("未知の camera_id: %s", camera_id)
        return None

    videos_dir = _VIDEOS_DIR / folder
    if not videos_dir.is_dir():
        log.warning("動画フォルダが存在しません: %s", videos_dir)
        return None

    # ファイル名から開始時刻を解析し候補を収集
    candidates: list[tuple[datetime, Path]] = []
    for f in videos_dir.iterdir():
        m = _VIDEO_PATTERN.match(f.name)
        if m:
            try:
                file_dt = datetime.strptime(m.group(1), "%Y%m%d_%H%M%S")
                candidates.append((file_dt, f))
            except ValueError:
                continue

    # detected_at_dt 以前で最も近い（開始時刻が最大の）ファイルを選択
    valid = [(dt, f) for dt, f in candidates if dt <= detected_at_dt]
    if not valid:
        log.warning("検知時刻以前の動画ファイルがありません: %s", detected_at_dt)
        return None
    file_dt, video_path = max(valid, key=lambda x: x[0])

    offset_seconds = int((detected_at_dt - file_dt).total_seconds())
    log.info(
        "再生: %s  開始オフセット=%s 秒  ファイル=%s",
        detected_at_dt, offset_seconds, video_path,
    )

    # ffmpeg で offset 秒以降を切り取り → 一時ファイル
    suffix = video_path.suffix
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    os.close(tmp_fd)

    cmd = [
        str(_FFMPEG_EXE),
        "-ss", str(offset_seconds),
        "-i", str(video_path),
        "-t", "30",
        "-c", "copy",
        "-y",
        tmp_path,
    ]
    log.info("ffmpeg実行: %s", " ".join(cmd))
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        if result.returncode != 0:
            log.error(
                "ffmpegエラー (rc=%d): %s",
                result.returncode,
                result.stderr.decode(errors="replace"),
            )
            os.remove(tmp_path)
            return None
    except Exception as exc:
        log.error("ffmpeg実行例外: %s", exc)
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        return None

    return tmp_path


def find_and_clip_video_range(
    start_at: datetime | str,
    end_at: datetime | str,
    camera_id: int,
) -> str | None:
    """
    start_at から end_at までの動画ファイルをすべて結合し、
    その範囲のみを ffmpeg で切り出して一時ファイルのパスを返す。
    失敗した場合は None を返す。
    """

    def _parse(s: datetime | str) -> datetime:
        if isinstance(s, str):
            try:
                return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                raise ValueError(f"日時の解析に失敗しました: {s}")
        return datetime(s.year, s.month, s.day, s.hour, s.minute, s.second)

    try:
        start_dt = _parse(start_at)
        end_dt = _parse(end_at)
    except ValueError as exc:
        log.error("%s", exc)
        return None

    if end_dt <= start_dt:
        log.warning("終了時刻が開始時刻以前です: %s ~ %s", start_dt, end_dt)
        return None

    folder = _CAMERA_FOLDER_MAP.get(camera_id)
    if folder is None:
        log.warning("未知の camera_id: %s", camera_id)
        return None

    videos_dir = _VIDEOS_DIR / folder
    if not videos_dir.is_dir():
        log.warning("動画フォルダが存在しません: %s", videos_dir)
        return None

    # ファイル一覧をソート
    all_files: list[tuple[datetime, Path]] = []
    for f in videos_dir.iterdir():
        m = _VIDEO_PATTERN.match(f.name)
        if m:
            try:
                file_dt = datetime.strptime(m.group(1), "%Y%m%d_%H%M%S")
                all_files.append((file_dt, f))
            except ValueError:
                continue
    all_files.sort(key=lambda x: x[0])

    if not all_files:
        log.warning("動画ファイルが見つかりません: %s", videos_dir)
        return None

    # start_dt を含むファイル（start_dt 以前で最後のもの）を特定
    # start_dt より2時間以上前のファイルしかない場合は start_dt ～ end_dt 内の最初のファイルを使用
    _TWO_HOURS = 1800  # 秒
    start_file_idx: int | None = None
    for i, (file_dt, _) in enumerate(all_files):
        if file_dt <= start_dt:
            start_file_idx = i

    if start_file_idx is None or (start_dt - all_files[start_file_idx][0]).total_seconds() >= _TWO_HOURS:
        start_file_idx = None
        for i, (file_dt, _) in enumerate(all_files):
            if start_dt <= file_dt < end_dt:
                start_file_idx = i
                break

    if start_file_idx is None:
        log.warning("検索範囲内に動画ファイルがありません: %s ~ %s", start_dt, end_dt)
        return None

    # start_file から end_dt 以前のファイルをすべて収集
    selected: list[tuple[datetime, Path]] = []
    for file_dt, file_path in all_files[start_file_idx:]:
        if file_dt <= end_dt:
            selected.append((file_dt, file_path))
        else:
            break

    if not selected:
        log.warning("対象の動画ファイルが見つかりません")
        return None

    first_dt = selected[0][0]
    start_offset_s = (start_dt - first_dt).total_seconds()
    total_duration_s = (end_dt - start_dt).total_seconds()

    log.info(
        "範囲再生: %s ~ %s  ファイル数=%d  開始オフセット=%.1f秒  再生時間=%.1f秒",
        start_dt, end_dt, len(selected), start_offset_s, total_duration_s,
    )

    # concat リストファイルを作成
    # inpoint/outpoint で重複排除（パターン②）・末尾の超過防止（パターン①）を処理する
    concat_fd, concat_list_path = tempfile.mkstemp(suffix=".txt")
    try:
        with os.fdopen(concat_fd, "w", encoding="utf-8") as cf:
            for i, (file_dt, p) in enumerate(selected):
                safe_path = str(p).replace("\\", "/")
                cf.write(f"file '{safe_path}'\n")
                # 先頭ファイルのみ: start_dt から開始（ファイル開始がstart_dtより後の場合は0）
                if i == 0:
                    inpoint_s = max(0.0, (start_dt - file_dt).total_seconds())
                    cf.write(f"inpoint {inpoint_s:.3f}\n")
                # 中間ファイル: 次ファイルの開始時刻で打ち切る（重複部分を先頭ファイル側から除外）
                # 末尾ファイル: end_dt で打ち切る（ギャップがあっても期間を超過しない）
                if i < len(selected) - 1:
                    next_file_dt = selected[i + 1][0]
                    outpoint_s = (next_file_dt - file_dt).total_seconds()
                else:
                    outpoint_s = (end_dt - file_dt).total_seconds()
                cf.write(f"outpoint {outpoint_s:.3f}\n")
    except OSError as exc:
        log.error("concat リストファイルの書き込みに失敗しました: %s", exc)
        return None

    suffix = selected[0][1].suffix
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    os.close(tmp_fd)

    cmd = [
        str(_FFMPEG_EXE),
        "-f", "concat",
        "-safe", "0",
        "-i", concat_list_path,
        "-c", "copy",
        "-y",
        tmp_path,
    ]
    log.info("ffmpeg実行(range): %s", " ".join(cmd))
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=300)
        if result.returncode != 0:
            log.error(
                "ffmpegエラー (rc=%d): %s",
                result.returncode,
                result.stderr.decode(errors="replace"),
            )
            os.remove(tmp_path)
            return None
    except Exception as exc:
        log.error("ffmpeg実行例外: %s", exc)
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        return None
    finally:
        try:
            os.remove(concat_list_path)
        except OSError:
            pass

    return tmp_path


def find_and_clip_video_centered(
    detected_at: datetime | str,
    camera_id: int,
    before_seconds: float = 3.0,
    after_seconds: float = 3.0,
) -> str | None:
    """
    detected_at を中心に、before_seconds 前から after_seconds 後までを切り出す。
    失敗した場合は None を返す。
    """
    # detected_at を datetime に統一
    if isinstance(detected_at, str):
        try:
            detected_at_dt = datetime.strptime(detected_at[:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            log.error("detected_at の解析に失敗しました: %s", detected_at)
            return None
    else:
        detected_at_dt = datetime(
            detected_at.year, detected_at.month, detected_at.day,
            detected_at.hour, detected_at.minute, detected_at.second,
        )

    if before_seconds < 0:
        before_seconds = 0.0
    if after_seconds < 0:
        after_seconds = 0.0

    clip_start_dt = detected_at_dt - timedelta(seconds=before_seconds)
    clip_duration_s = before_seconds + after_seconds
    if clip_duration_s <= 0:
        log.warning("切り出し時間が0以下です: before=%.3f after=%.3f", before_seconds, after_seconds)
        return None

    folder = _CAMERA_FOLDER_MAP.get(camera_id)
    if folder is None:
        log.warning("未知の camera_id: %s", camera_id)
        return None

    videos_dir = _VIDEOS_DIR / folder
    if not videos_dir.is_dir():
        log.warning("動画フォルダが存在しません: %s", videos_dir)
        return None

    # ファイル名から開始時刻を解析し候補を収集
    candidates: list[tuple[datetime, Path]] = []
    for f in videos_dir.iterdir():
        m = _VIDEO_PATTERN.match(f.name)
        if m:
            try:
                file_dt = datetime.strptime(m.group(1), "%Y%m%d_%H%M%S")
                candidates.append((file_dt, f))
            except ValueError:
                continue

    # clip_start_dt 以前で最も近い（開始時刻が最大の）ファイルを選択
    valid = [(dt, f) for dt, f in candidates if dt <= clip_start_dt]
    if not valid:
        # clip_start_dt より前の動画がない場合は detected_at 基準にフォールバック
        valid = [(dt, f) for dt, f in candidates if dt <= detected_at_dt]
        if not valid:
            log.warning("検知時刻以前の動画ファイルがありません: %s", detected_at_dt)
            return None
        file_dt, video_path = max(valid, key=lambda x: x[0])
        offset_seconds = (detected_at_dt - file_dt).total_seconds()
    else:
        file_dt, video_path = max(valid, key=lambda x: x[0])
        offset_seconds = (clip_start_dt - file_dt).total_seconds()

    if offset_seconds < 0:
        offset_seconds = 0.0

    suffix = video_path.suffix
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    os.close(tmp_fd)

    cmd = [
        str(_FFMPEG_EXE),
        "-ss", f"{offset_seconds:.3f}",
        "-i", str(video_path),
        "-t", f"{clip_duration_s:.3f}",
        "-c", "copy",
        "-y",
        tmp_path,
    ]
    log.info("ffmpeg実行(centered): %s", " ".join(cmd))
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        if result.returncode != 0:
            log.error(
                "ffmpegエラー (rc=%d): %s",
                result.returncode,
                result.stderr.decode(errors="replace"),
            )
            os.remove(tmp_path)
            return None
    except Exception as exc:
        log.error("ffmpeg実行例外: %s", exc)
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        return None

    return tmp_path