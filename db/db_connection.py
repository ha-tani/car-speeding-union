"""

PostgreSQL 接続・共通ユーティリティモジュール

"""

import logging
import os
import sys
from contextlib import contextmanager
from typing import Optional

import psycopg2
import psycopg2.extras
import psycopg2.pool

# 上位階層の config.py を参照
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import config


# ─────────────────────────────────────────────
# ロガー設定
# ─────────────────────────────────────────────
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    logger.addHandler(handler)


# ─────────────────────────────────────────────
# 接続設定（config.py から組み立て）
# ─────────────────────────────────────────────
_DB_CONFIG = {
    "host":            config.DB_HOST,
    "port":            config.DB_PORT,
    "dbname":          config.DB_NAME,
    "user":            config.DB_USER,
    "password":        config.DB_PASSWORD,
    "connect_timeout": config.DB_CONNECT_TIMEOUT,
    "options":         f"-c client_encoding={config.DB_CLIENT_ENCODING}",
}

# ─────────────────────────────────────────────
# コネクションプール
# ─────────────────────────────────────────────
_pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None


def _get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    """スレッドセーフなコネクションプールを返す（遅延初期化）。"""
    global _pool
    if _pool is None or _pool.closed:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=5,
            **_DB_CONFIG,
        )
        logger.info("DB コネクションプールを初期化しました (maxconn=5)")
    return _pool


# ─────────────────────────────────────────────
# 接続関数
# ─────────────────────────────────────────────
def get_connection() -> psycopg2.extensions.connection:
    """
    コネクションプールから接続を取得して返す。
    使用後は必ず返却すること。通常は get_db_cursor() コンテキストマネージャの利用を推奨。

    Returns:
        psycopg2 connection オブジェクト

    Raises:
        psycopg2.OperationalError: 接続失敗時
    """
    try:
        conn = _get_pool().getconn()
        logger.debug("プールから接続を取得")
        return conn
    except psycopg2.OperationalError as e:
        logger.error("DB接続失敗: %s", e)
        raise


# ─────────────────────────────────────────────
# コンテキストマネージャ
# ─────────────────────────────────────────────
@contextmanager
def get_db_cursor(
    autocommit: bool = False,
    cursor_factory=psycopg2.extras.RealDictCursor,
):
    """
    DB接続とカーソルをコンテキストマネージャとして提供する。
    正常終了時は commit、例外発生時は rollback を自動実行。

    Args:
        autocommit (bool): True にすると自動コミットモード。
                           SELECT のみの処理に適している。
        cursor_factory   : カーソルの種類（デフォルト: RealDictCursor＝辞書形式）

    Yields:
        psycopg2 cursor オブジェクト

    Example:
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM vehicle_speed_records")
            rows = cur.fetchall()
    """
    conn: Optional[psycopg2.extensions.connection] = None
    try:
        conn = get_connection()
        conn.autocommit = autocommit
        with conn.cursor(cursor_factory=cursor_factory) as cur:
            yield cur
            if not autocommit:
                conn.commit()
                logger.debug("トランザクションをコミットしました")
    except Exception as e:
        if conn and not autocommit:
            conn.rollback()
            logger.warning("例外発生のためロールバックしました: %s", e)
        raise
    finally:
        if conn:
            _get_pool().putconn(conn)
            logger.debug("接続をプールに返却しました")


# ─────────────────────────────────────────────
# ユーティリティ関数
# ─────────────────────────────────────────────
def test_connection() -> bool:
    """
    DB接続の疎通確認。

    Returns:
        bool: 接続成功なら True
    """
    try:
        with get_db_cursor(autocommit=True) as cur:
            cur.execute("SELECT 1")
        logger.info("DB接続テスト: OK")
        return True
    except Exception as e:
        logger.error("DB接続テスト: NG (%s)", e)
        return False


def execute_query(sql: str, params: Optional[tuple] = None) -> list[dict]:
    """
    SELECT 用の汎用クエリ実行。

    Args:
        sql    (str)            : 実行する SQL 文
        params (tuple, optional): バインドパラメータ

    Returns:
        list[dict]: 取得結果の辞書リスト（0件の場合は空リスト）

    Example:
        rows = execute_query(
            "SELECT * FROM vehicle_speed_records WHERE vehicle_id = %s",
            (vehicle_id,)
        )
    """
    with get_db_cursor(autocommit=True) as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def execute_command(sql: str, params: Optional[tuple] = None) -> int:
    """
    INSERT / UPDATE / DELETE 用の汎用コマンド実行。

    Args:
        sql    (str)            : 実行する SQL 文
        params (tuple, optional): バインドパラメータ

    Returns:
        int: 影響を受けた行数

    Example:
        affected = execute_command(
            "DELETE FROM vehicle_speed_records WHERE id = %s",
            (record_id,)
        )
    """
    with get_db_cursor() as cur:
        cur.execute(sql, params)
        return cur.rowcount


def execute_many(sql: str, params_list: list[tuple]) -> int:
    """
    バルク INSERT / UPDATE 用の一括実行。

    Args:
        sql         (str)         : 実行する SQL 文
        params_list (list[tuple]) : バインドパラメータのリスト

    Returns:
        int: 処理件数

    Example:
        execute_many(
            "INSERT INTO vehicle_speed_records (vehicle_id, speed_kmh) VALUES (%s, %s)",
            [(v_id, speed) for v_id, speed in data_list]
        )
    """
    with get_db_cursor() as cur:
        psycopg2.extras.execute_batch(cur, sql, params_list)
        return len(params_list)


# ─────────────────────────────────────────────
# 動作確認用（直接実行時のみ）
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=== DB接続テスト ===")
    result = test_connection()
    print(f"  結果: {'OK' if result else 'NG'}")