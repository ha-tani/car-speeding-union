"""

PostgreSQL データベースへのクエリ用モジュール

"""

import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from db.db_connection import get_db_cursor


def get_camera_by_name(camera_name: str):
    """
    cameras テーブルからカメラ名でカメラ情報を取得する。
    """
    sql = """
        SELECT camera_id, road_range, road_width, road_depth, speed_limit
        FROM cameras
        WHERE camera_name = %s
    """
    with get_db_cursor(autocommit=True) as cur:
        cur.execute(sql, (camera_name,))
        row = cur.fetchone()
    if row is None:
        return None

    road_range = row["road_range"]
    if isinstance(road_range, str):
        try:
            road_range = json.loads(road_range)
        except (json.JSONDecodeError, TypeError):
            road_range = None

    return {
        "camera_id": row["camera_id"],
        "road_range": road_range,
        "road_width": float(row["road_width"]) if row["road_width"] is not None else None,
        "road_depth": float(row["road_depth"]) if row["road_depth"] is not None else None,
        "speed_limit": float(row["speed_limit"]) if row["speed_limit"] is not None else None,
    }

# 後方互換エイリアス
def get_camera_id_by_name(camera_name: str):
    info = get_camera_by_name(camera_name)
    return info["camera_id"] if info else None


def get_camera_params_by_id(camera_id: int | str) -> dict | None:
    """
    cameras テーブルから camera_id でカメラパラメータを取得する。

    Returns:
        road_range, road_width, road_depth, speed_limit を含む dict。
        該当行が存在しない場合は None。
    """
    sql = """
        SELECT road_range, road_width, road_depth, speed_limit
        FROM cameras
        WHERE camera_id = %s
    """
    with get_db_cursor(autocommit=True) as cur:
        cur.execute(sql, (str(camera_id),))
        row = cur.fetchone()
    if row is None:
        return None

    road_range = row["road_range"]
    if isinstance(road_range, str):
        try:
            road_range = json.loads(road_range)
        except (json.JSONDecodeError, TypeError):
            road_range = None

    return {
        "road_range": road_range,
        "road_width": float(row["road_width"]) if row["road_width"] is not None else None,
        "road_depth": float(row["road_depth"]) if row["road_depth"] is not None else None,
        "speed_limit": float(row["speed_limit"]) if row["speed_limit"] is not None else None,
    }


def upsert_vehicle(
    plate_number=None,
    vehicle_type=None,
    detected_at=None,
):
    """
    vehicles テーブルにアップサート（新規登録 or 違反回数更新）。
    """
    if plate_number:
        sql = """
            INSERT INTO vehicles (
                plate_number, vehicle_type, violation_count,
                first_violation_at, last_violation_at, created_at, updated_at
            ) VALUES (%s, %s, 1, %s, %s, NOW(), NOW())
            ON CONFLICT (plate_number) DO UPDATE SET
                violation_count    = vehicles.violation_count + 1,
                last_violation_at  = EXCLUDED.last_violation_at,
                vehicle_type       = COALESCE(EXCLUDED.vehicle_type, vehicles.vehicle_type),
                updated_at         = NOW()
            RETURNING vehicle_id
        """
        params = (plate_number, vehicle_type, detected_at, detected_at)
    else:
        sql = """
            INSERT INTO vehicles (
                plate_number, vehicle_type, violation_count,
                first_violation_at, last_violation_at, created_at, updated_at
            ) VALUES (NULL, %s, 1, %s, %s, NOW(), NOW())
            RETURNING vehicle_id
        """
        params = (vehicle_type, detected_at, detected_at)

    with get_db_cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
    if row is None:
        raise RuntimeError("vehicles INSERT/UPSERT が行を返しませんでした")
    return row["vehicle_id"]


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
    if row is None:
        raise RuntimeError("INSERT...RETURNING が行を返しませんでした")
    return row["event_id"]

# 後方互換エイリアス
def insert_vehicle_speed_events(
    detected_at,
    measured_speed,
    speed_limit,
    excess_speed,
    track_id,
    vehicle_id=None,
    camera_id=None,
    vehicle_color=None,
    vehicle_type=None,
    plate_number=None,
    vehicle_image_path=None,
    plate_image_path=None,
    status="new",
    note=None,
):
    """
    vehicle_violation_events テーブルに速度超過イベントを登録する。
    """
    return insert_vehicle_violation_events(
        detected_at=detected_at,
        measured_speed=measured_speed,
        speed_limit=speed_limit,
        excess_speed=excess_speed,
        track_id=track_id,
        vehicle_image_path=vehicle_image_path,
        plate_image_path=plate_image_path,
        vehicle_id=vehicle_id,
        camera_id=camera_id,
        vehicle_color=vehicle_color,
        vehicle_type=vehicle_type,
        plate_number=plate_number,
        status=status,
        note=note,
    )


def search_violation_events(
    detected_at_from: str,
    detected_at_to: str,
    camera_id: int | None = None,
    speed_limit: float | None = None,
) -> list[dict]:
    """
    vehicle_violation_events テーブルから条件に合致する行を取得する。
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


def update_event_vehicle_id(event_id: int, vehicle_id: int):
    """
    vehicle_violation_events の vehicle_id を後から更新する。
    vehicles アップサート後に呼び出す。

    Parameters
    ----------
    event_id : int
        更新対象の event_id。
    vehicle_id : int
        vehicles テーブルの vehicle_id。
    """
    sql = """
        UPDATE vehicle_violation_events
        SET vehicle_id = %s
        WHERE event_id = %s
    """
    with get_db_cursor() as cur:
        cur.execute(sql, (vehicle_id, event_id))


def register_violation(
    detected_at,
    measured_speed,
    speed_limit,
    excess_speed,
    track_id,
    camera_id=None,
    vehicle_type=None,
    plate_number=None,
    vehicle_image_path=None,
    plate_image_path=None,
) -> tuple[int, int]:
    """
    速度違反の登録を1トランザクションで実行する。

    1) vehicle_violation_events に INSERT
    2) vehicles に UPSERT
    3) vehicle_violation_events.vehicle_id を UPDATE

    Returns
    -------
    (event_id, vehicle_id) : tuple[int, int]
    """
    with get_db_cursor() as cur:
        # Step 1: INSERT event
        cur.execute(
            """
            INSERT INTO vehicle_violation_events (
                vehicle_id, camera_id, detected_at,
                measured_speed, speed_limit, excess_speed,
                vehicle_color, vehicle_type, plate_number,
                vehicle_image_path, plate_image_path,
                track_id, status, note
            ) VALUES (
                NULL, %s, %s,
                %s, %s, %s,
                NULL, %s, %s,
                %s, %s,
                %s, 'new', NULL
            )
            RETURNING event_id
            """,
            (
                camera_id, detected_at,
                measured_speed, speed_limit, excess_speed,
                vehicle_type, plate_number,
                vehicle_image_path, plate_image_path,
                str(track_id),
            ),
        )
        event_id = cur.fetchone()["event_id"]

        # Step 2: UPSERT vehicle
        if plate_number:
            cur.execute(
                """
                INSERT INTO vehicles (
                    plate_number, vehicle_type, violation_count,
                    first_violation_at, last_violation_at, created_at, updated_at
                ) VALUES (%s, %s, 1, %s, %s, NOW(), NOW())
                ON CONFLICT (plate_number) DO UPDATE SET
                    violation_count    = vehicles.violation_count + 1,
                    last_violation_at  = EXCLUDED.last_violation_at,
                    vehicle_type       = COALESCE(EXCLUDED.vehicle_type, vehicles.vehicle_type),
                    updated_at         = NOW()
                RETURNING vehicle_id
                """,
                (plate_number, vehicle_type, detected_at, detected_at),
            )
        else:
            cur.execute(
                """
                INSERT INTO vehicles (
                    plate_number, vehicle_type, violation_count,
                    first_violation_at, last_violation_at, created_at, updated_at
                ) VALUES (NULL, %s, 1, %s, %s, NOW(), NOW())
                RETURNING vehicle_id
                """,
                (vehicle_type, detected_at, detected_at),
            )
        vehicle_id = cur.fetchone()["vehicle_id"]

        # Step 3: UPDATE event with vehicle_id
        cur.execute(
            "UPDATE vehicle_violation_events SET vehicle_id = %s WHERE event_id = %s",
            (vehicle_id, event_id),
        )

    return event_id, vehicle_id