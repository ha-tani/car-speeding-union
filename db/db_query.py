"""

PostgreSQL データベースへのクエリ用モジュール

"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from db.db_connection import get_db_cursor


def insert_vehicle_violation_events(
    detected_at,
    measured_speed,
    speed_limit,
    excess_speed,
    track_id,
    vehicle_image_path=None,
    plate_image_path=None,
    vehicle_id=None,
    camera_id=None,
    vehicle_color=None,
    vehicle_type=None,
    plate_number=None,
    status="new",
    note=None,
):
    """
    vehicle_violation_events テーブルに速度超過イベントを登録する。

    Parameters
    ----------
    detected_at : datetime
        検知日時。
    measured_speed : float
        実測速度 (km/h)。
    speed_limit : float
        制限速度 (km/h)。
    excess_speed : float
        超過速度 (km/h)。
    track_id : int or str
        動画内トラッキングID。
    vehicle_image_path : str or None
        車両キャプチャ画像のパス。
    plate_image_path : str or None
        ナンバープレート画像のパス。
    vehicle_id : int or None
        vehicles テーブルの外部キー。
    camera_id : int or None
        cameras テーブルの外部キー。
    vehicle_color : str or None
        車の色。
    vehicle_type : str or None
        車種。
    plate_number : str or None
        ナンバープレートの4桁数字。
    status : str
        状態 (例: new / checked / mailed)。
    note : str or None
        備考。

    Returns
    -------
    int
        生成された event_id。
    """
    sql = """
        INSERT INTO vehicle_violation_events (
            vehicle_id, camera_id, detected_at,
            measured_speed, speed_limit, excess_speed,
            vehicle_color, vehicle_type, plate_number,
            vehicle_image_path, plate_image_path,
            track_id, status, note
        ) VALUES (
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s,
            %s, %s, %s
        )
        RETURNING event_id
    """
    params = (
        vehicle_id, camera_id, detected_at,
        measured_speed, speed_limit, excess_speed,
        vehicle_color, vehicle_type, plate_number,
        vehicle_image_path, plate_image_path,
        str(track_id), status, note,
    )
    with get_db_cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
    return row["event_id"]


def search_violation_events(
    detected_at_from: str,
    detected_at_to: str,
    camera_id: int | None = None,
    speed_limit: float | None = None,
) -> list[dict]:
    """
    vehicle_violation_events テーブルから条件に合致する行を取得する。

    Parameters
    ----------
    detected_at_from : str
        検索開始日時 (YYYY-MM-DD HH:MM:00)。
    detected_at_to : str
        検索終了日時 (YYYY-MM-DD HH:MM:00)。
    camera_id : int or None
        絞り込むカメラID。None の場合はすべてのカメラを対象とする。
    speed_limit : float or None
        絞り込む制限速度 (km/h)。None の場合は速度による絞り込みなし。

    Returns
    -------
    list[dict]
        取得した行のリスト。各行は列名をキーとする辞書。
    """
    conditions = ["detected_at >= %s", "detected_at <= %s"]
    params: list = [detected_at_from, detected_at_to]

    if camera_id is not None:
        conditions.append("camera_id = %s")
        params.append(camera_id)

    if speed_limit is not None:
        conditions.append("speed_limit = %s")
        params.append(speed_limit)

    sql = (
        "SELECT * FROM vehicle_violation_events WHERE "
        + " AND ".join(conditions)
        + " ORDER BY detected_at"
    )

    with get_db_cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    return [dict(row) for row in rows]