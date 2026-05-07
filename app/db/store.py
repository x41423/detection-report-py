"""Database storage helpers for the local application."""

import logging
import os
import re
import shutil
import sqlite3
import threading
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Protocol

try:
    import pymysql
    from pymysql.cursors import DictCursor
except ImportError:  # pragma: no cover - optional dependency until MySQL mode is used.
    pymysql = None
    DictCursor = None

from app.db.auth_seed import seed_auth_defaults
from shared.project_paths import ProjectPaths, get_project_paths


def resolve_default_db_path(paths: ProjectPaths | None = None) -> Path:
    project_paths = paths or get_project_paths()
    if project_paths.database_file.exists():
        return project_paths.database_file
    if project_paths.legacy_database_file.exists():
        project_paths.data_dir.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(project_paths.legacy_database_file, project_paths.database_file)
            logging.info("Migrated legacy database to %s", project_paths.database_file)
            return project_paths.database_file
        except Exception:
            logging.warning(
                "Failed to copy legacy database to canonical path, continuing with legacy path: %s",
                project_paths.legacy_database_file,
                exc_info=True,
            )
            return project_paths.legacy_database_file
    return project_paths.database_file


DB_PATH = str(resolve_default_db_path())
DB_DIR = os.path.dirname(DB_PATH)
DB_DRIVER = os.getenv("APP_DB_DRIVER", "mysql").strip().lower() or "mysql"
MYSQL_HOST = os.getenv("APP_DB_MYSQL_HOST", os.getenv("MYSQL_HOST", "localhost")).strip() or "localhost"
MYSQL_PORT = int(os.getenv("APP_DB_MYSQL_PORT", os.getenv("MYSQL_PORT", "3306")))
MYSQL_DATABASE = os.getenv("APP_DB_MYSQL_DATABASE", os.getenv("MYSQL_DATABASE", "inspection_report")).strip()
MYSQL_USER = os.getenv("APP_DB_MYSQL_USER", os.getenv("MYSQL_USER", "inspection_app")).strip()
MYSQL_PASSWORD = os.getenv("APP_DB_MYSQL_PASSWORD", os.getenv("MYSQL_PASSWORD", "")).strip()
MYSQL_CHARSET = os.getenv("APP_DB_MYSQL_CHARSET", os.getenv("MYSQL_CHARSET", "utf8mb4")).strip() or "utf8mb4"

DATABASE_INTEGRITY_ERRORS = (
    (sqlite3.IntegrityError, pymysql.err.IntegrityError)
    if pymysql is not None
    else (sqlite3.IntegrityError,)
)


class CursorLike(Protocol):
    description: Any
    lastrowid: int | None
    rowcount: int

    def execute(self, sql: str, params: tuple | list | None = None) -> "CursorLike": ...
    def executemany(self, sql: str, params: list[tuple] | tuple[tuple, ...]) -> "CursorLike": ...
    def fetchone(self) -> Any: ...
    def fetchall(self) -> list[Any]: ...
    def close(self) -> None: ...


class ConnectionLike(Protocol):
    def cursor(self) -> CursorLike: ...
    def execute(self, sql: str, params: tuple | list | None = None) -> CursorLike: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def close(self) -> None: ...


_connection: ConnectionLike | None = None
_mysql_local = threading.local()


def get_db_driver() -> str:
    return DB_DRIVER


def is_mysql_driver() -> bool:
    return os.getenv("APP_DB_DRIVER", "mysql").strip().lower() == "mysql"


class MySQLCursorAdapter:
    def __init__(self, cursor: Any):
        self._cursor = cursor

    @property
    def description(self) -> Any:
        return self._cursor.description

    @property
    def lastrowid(self) -> int | None:
        return self._cursor.lastrowid

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount

    def execute(self, sql: str, params: tuple | list | None = None) -> "MySQLCursorAdapter":
        self._cursor.execute(_translate_sql_for_mysql(sql), params)
        return self

    def executemany(self, sql: str, params: list[tuple] | tuple[tuple, ...]) -> "MySQLCursorAdapter":
        self._cursor.executemany(_translate_sql_for_mysql(sql), params)
        return self

    def fetchone(self) -> Any:
        return _normalize_mysql_row(self._cursor.fetchone())

    def fetchall(self) -> list[Any]:
        return [_normalize_mysql_row(row) for row in self._cursor.fetchall()]

    def close(self) -> None:
        self._cursor.close()


class MySQLConnectionAdapter:
    def __init__(self, connection: Any):
        self._connection = connection

    def cursor(self) -> MySQLCursorAdapter:
        return MySQLCursorAdapter(self._connection.cursor())

    def execute(self, sql: str, params: tuple | list | None = None) -> MySQLCursorAdapter:
        cursor = self.cursor()
        cursor.execute(sql, params)
        return cursor

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def close(self) -> None:
        self._connection.close()

    def ping(self) -> None:
        self._connection.ping(reconnect=True)


def _translate_sql_for_mysql(sql: str) -> str:
    translated = sql.strip() if sql.strip().upper() == "BEGIN IMMEDIATE" else sql
    if translated.upper() == "BEGIN IMMEDIATE":
        translated = "START TRANSACTION"
    translated = re.sub(r"\bINSERT\s+OR\s+IGNORE\s+INTO\b", "INSERT IGNORE INTO", translated, flags=re.IGNORECASE)
    translated = re.sub(
        r"\bON\s+CONFLICT\s*\([^)]*\)\s+DO\s+UPDATE\s+SET\b",
        "ON DUPLICATE KEY UPDATE",
        translated,
        flags=re.IGNORECASE,
    )
    translated = re.sub(
        r"\bexcluded\.([A-Za-z_][A-Za-z0-9_]*)\b",
        lambda match: f"VALUES({match.group(1)})",
        translated,
        flags=re.IGNORECASE,
    )
    return _convert_qmark_placeholders(translated)


def _convert_qmark_placeholders(sql: str) -> str:
    result: list[str] = []
    in_single = False
    in_double = False
    index = 0
    while index < len(sql):
        char = sql[index]
        if char == "'" and not in_double:
            result.append(char)
            if in_single and index + 1 < len(sql) and sql[index + 1] == "'":
                result.append(sql[index + 1])
                index += 2
                continue
            in_single = not in_single
        elif char == '"' and not in_single:
            result.append(char)
            in_double = not in_double
        elif char == "?" and not in_single and not in_double:
            result.append("%s")
        else:
            result.append(char)
        index += 1
    return "".join(result)


def _normalize_mysql_row(row: Any) -> Any:
    if isinstance(row, dict):
        return {key: _normalize_mysql_value(value) for key, value in row.items()}
    return row


def _normalize_mysql_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, (date, time)):
        return value.isoformat()
    return value


def get_connection() -> ConnectionLike:
    """Return a shared database connection."""
    global _connection
    if is_mysql_driver():
        mysql_connection = getattr(_mysql_local, "connection", None)
        if mysql_connection is not None:
            try:
                mysql_connection.ping()
                return mysql_connection
            except Exception:
                _drop_mysql_thread_connection()
        mysql_connection = _create_mysql_connection()
        _mysql_local.connection = mysql_connection
        logging.info(
            "MySQL database connection established for thread %s: %s:%s/%s",
            threading.get_ident(),
            MYSQL_HOST,
            MYSQL_PORT,
            MYSQL_DATABASE,
        )
        return mysql_connection

    if _connection is None:
        os.makedirs(DB_DIR, exist_ok=True)
        sqlite_connection = sqlite3.connect(DB_PATH, check_same_thread=False)
        sqlite_connection.row_factory = sqlite3.Row
        sqlite_connection.execute("PRAGMA journal_mode = WAL")
        sqlite_connection.execute("PRAGMA foreign_keys = ON")
        _connection = sqlite_connection
        logging.info("数据库连接已建立: %s", DB_PATH)
    return _connection


def _create_mysql_connection() -> MySQLConnectionAdapter:
    if pymysql is None or DictCursor is None:
        raise RuntimeError("APP_DB_DRIVER=mysql requires PyMySQL to be installed")
    if not MYSQL_DATABASE or not MYSQL_USER:
        raise RuntimeError("MySQL database and user must be configured for APP_DB_DRIVER=mysql")
    connection = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset=MYSQL_CHARSET,
        cursorclass=DictCursor,
        autocommit=False,
    )
    with connection.cursor() as cursor:
        cursor.execute("SET time_zone = '+00:00'")
    return MySQLConnectionAdapter(connection)


def close_connection():
    """Close the shared database connection if it exists."""
    global _connection
    if is_mysql_driver():
        _drop_mysql_thread_connection()
        return

    if _connection is not None:
        _connection.close()
        _connection = None
        logging.info("数据库连接已关闭")


def _drop_mysql_thread_connection() -> None:
    mysql_connection = getattr(_mysql_local, "connection", None)
    if mysql_connection is None:
        return
    try:
        mysql_connection.close()
    except Exception:
        pass
    finally:
        _mysql_local.connection = None


def _is_mysql_connection_error(exc: Exception) -> bool:
    if pymysql is not None and isinstance(
        exc,
        (
            pymysql.err.OperationalError,
            pymysql.err.InternalError,
            pymysql.err.InterfaceError,
        ),
    ):
        return True
    message = str(exc).lower()
    return any(
        marker in message
        for marker in (
            "packet sequence number wrong",
            "read of closed file",
            "non-socket",
            "not a socket",
            "closed socket",
            "lost connection",
            "server has gone away",
        )
    )


def init_database():
    """Create all known database tables and indexes."""
    conn = get_connection()
    if is_mysql_driver():
        from app.db.mysql_schema import init_mysql_database

        init_mysql_database(conn, seed_auth_defaults)
        return

    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Veg (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                category TEXT DEFAULT 'other',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Unit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS PriceHistory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vegetable_id INTEGER NOT NULL,
                unit_id INTEGER NOT NULL,
                price REAL NOT NULL,
                date TEXT NOT NULL,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vegetable_id) REFERENCES Veg(id) ON DELETE CASCADE,
                FOREIGN KEY (unit_id) REFERENCES Unit(id) ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS WeeklyPriceEntry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week_start TEXT NOT NULL,
                vegetable_id INTEGER NOT NULL,
                unit_id INTEGER NOT NULL,
                price REAL NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vegetable_id) REFERENCES Veg(id) ON DELETE CASCADE,
                FOREIGN KEY (unit_id) REFERENCES Unit(id) ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS WeeklyQuoteBatch (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier TEXT NOT NULL,
                quote_date TEXT NOT NULL,
                source_label TEXT DEFAULT '',
                source_path TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(supplier, quote_date)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS WeeklyQuoteEntry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL REFERENCES WeeklyQuoteBatch(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                unit TEXT NOT NULL DEFAULT '斤',
                price REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS DailyIntakeSheet (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                intake_date TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS DailyIntakeItem (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sheet_id INTEGER NOT NULL,
                veg_id INTEGER,
                raw_name TEXT NOT NULL,
                normalized_name TEXT NOT NULL,
                category TEXT NOT NULL,
                unit_id INTEGER NOT NULL,
                quantity REAL NOT NULL,
                source TEXT NOT NULL DEFAULT 'manual',
                transcript TEXT DEFAULT '',
                last_source TEXT NOT NULL DEFAULT 'manual',
                last_transcript TEXT DEFAULT '',
                merge_count INTEGER NOT NULL DEFAULT 1,
                last_confirmed_at TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sheet_id) REFERENCES DailyIntakeSheet(id) ON DELETE CASCADE,
                FOREIGN KEY (veg_id) REFERENCES Veg(id) ON DELETE SET NULL,
                FOREIGN KEY (unit_id) REFERENCES Unit(id) ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS InventoryTransaction (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                veg_id INTEGER,
                display_name TEXT NOT NULL,
                normalized_name TEXT NOT NULL,
                unit_id INTEGER NOT NULL,
                direction TEXT NOT NULL,
                quantity_delta REAL NOT NULL,
                business_date TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_ref_id INTEGER,
                note TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (veg_id) REFERENCES Veg(id) ON DELETE SET NULL,
                FOREIGN KEY (unit_id) REFERENCES Unit(id) ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Config (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        _create_auth_schema(cursor)
        _ensure_auth_schema_columns(cursor)

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_price_veg_unit_date
            ON PriceHistory (vegetable_id, unit_id, date DESC)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_weekly_veg_unit_week
            ON WeeklyPriceEntry (vegetable_id, unit_id, week_start DESC)
            """
        )

        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_intake_sheet_date
            ON DailyIntakeSheet (intake_date)
            """
        )

        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_intake_item_merge_key
            ON DailyIntakeItem (sheet_id, normalized_name, unit_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_daily_intake_item_sheet
            ON DailyIntakeItem (sheet_id, updated_at DESC)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_inventory_transaction_item
            ON InventoryTransaction (normalized_name, unit_id, updated_at DESC)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_inventory_transaction_business_date
            ON InventoryTransaction (business_date DESC, id DESC)
            """
        )

        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_inventory_transaction_source_ref
            ON InventoryTransaction (source_type, source_ref_id)
            WHERE source_ref_id IS NOT NULL
            """
        )

        _create_auth_indexes(cursor)

        cursor.execute(
            """
            INSERT OR IGNORE INTO schema_migrations (version, name)
            VALUES (1, 'auth_core_schema')
            """
        )

        seed_auth_defaults(cursor)

        conn.commit()
        logging.info("数据库表结构初始化完成")
    except Exception:
        conn.rollback()
        logging.exception("数据库初始化失败")
        raise
    finally:
        cursor.close()


def _create_auth_schema(cursor: sqlite3.Cursor) -> None:
    """Create authentication and authorization tables without seeding data."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL DEFAULT '',
            password_hash TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            is_super_admin INTEGER NOT NULL DEFAULT 0,
            must_change_password INTEGER NOT NULL DEFAULT 0,
            failed_login_count INTEGER NOT NULL DEFAULT 0,
            locked_until TEXT,
            last_failed_login_at TEXT,
            last_login_at TEXT,
            password_changed_at TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CHECK (is_active IN (0, 1)),
            CHECK (is_super_admin IN (0, 1)),
            CHECK (must_change_password IN (0, 1))
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            is_system INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CHECK (is_system IN (0, 1))
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            module TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_user_roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id, role_id),
            FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE,
            FOREIGN KEY (role_id) REFERENCES auth_roles(id) ON DELETE CASCADE
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_role_permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role_id INTEGER NOT NULL,
            permission_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (role_id, permission_id),
            FOREIGN KEY (role_id) REFERENCES auth_roles(id) ON DELETE CASCADE,
            FOREIGN KEY (permission_id) REFERENCES auth_permissions(id) ON DELETE CASCADE
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_user_permission_overrides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            permission_id INTEGER NOT NULL,
            effect TEXT NOT NULL,
            reason TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id, permission_id),
            CHECK (effect IN ('allow', 'deny')),
            FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE,
            FOREIGN KEY (permission_id) REFERENCES auth_permissions(id) ON DELETE CASCADE
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_permission_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            permission_id INTEGER,
            permission_code TEXT NOT NULL,
            reason TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            reviewer_id INTEGER,
            review_comment TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reviewed_at TEXT,
            CHECK (status IN ('pending', 'approved', 'rejected', 'cancelled')),
            FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE,
            FOREIGN KEY (permission_id) REFERENCES auth_permissions(id) ON DELETE SET NULL,
            FOREIGN KEY (reviewer_id) REFERENCES auth_users(id) ON DELETE SET NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            device_name TEXT NOT NULL DEFAULT '',
            device_fingerprint TEXT NOT NULL,
            user_agent TEXT NOT NULL DEFAULT '',
            browser TEXT NOT NULL DEFAULT '',
            os TEXT NOT NULL DEFAULT '',
            ip_address TEXT NOT NULL DEFAULT '',
            first_login_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_revoked INTEGER NOT NULL DEFAULT 0,
            revoked_at TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id, device_fingerprint),
            CHECK (is_revoked IN (0, 1)),
            FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            device_id INTEGER NOT NULL,
            access_token_hash TEXT NOT NULL UNIQUE,
            refresh_token_hash TEXT UNIQUE,
            access_expires_at TEXT NOT NULL,
            refresh_expires_at TEXT,
            revoked_at TEXT,
            revoke_reason TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT NOT NULL DEFAULT '',
            user_agent TEXT NOT NULL DEFAULT '',
            FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE,
            FOREIGN KEY (device_id) REFERENCES auth_devices(id) ON DELETE CASCADE
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_pending_logins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            pending_token_hash TEXT NOT NULL UNIQUE,
            ip_address TEXT NOT NULL DEFAULT '',
            user_agent TEXT NOT NULL DEFAULT '',
            device_name TEXT NOT NULL DEFAULT '',
            expires_at TEXT NOT NULL,
            used_at TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_user_id INTEGER,
            target_user_id INTEGER,
            action TEXT NOT NULL,
            module TEXT NOT NULL DEFAULT 'auth',
            description TEXT NOT NULL DEFAULT '',
            ip_address TEXT NOT NULL DEFAULT '',
            user_agent TEXT NOT NULL DEFAULT '',
            result TEXT NOT NULL DEFAULT 'success',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (actor_user_id) REFERENCES auth_users(id) ON DELETE SET NULL,
            FOREIGN KEY (target_user_id) REFERENCES auth_users(id) ON DELETE SET NULL
        )
        """
    )


def _ensure_auth_schema_columns(cursor: sqlite3.Cursor) -> None:
    """Apply small idempotent auth table shape updates until a full migration layer exists."""
    pending_columns = _table_columns(cursor, "auth_pending_logins")
    if "device_name" not in pending_columns:
        cursor.execute(
            """
            ALTER TABLE auth_pending_logins
            ADD COLUMN device_name TEXT NOT NULL DEFAULT ''
            """
        )


def _table_columns(cursor: sqlite3.Cursor, table_name: str) -> set[str]:
    cursor.execute(f"PRAGMA table_info({table_name})")
    return {row["name"] for row in cursor.fetchall()}


def _create_auth_indexes(cursor: sqlite3.Cursor) -> None:
    """Create indexes that auth lookups will rely on in later phases."""
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_auth_user_roles_user
        ON auth_user_roles (user_id)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_auth_role_permissions_role
        ON auth_role_permissions (role_id)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_auth_permission_overrides_user
        ON auth_user_permission_overrides (user_id)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_auth_permission_requests_user_status
        ON auth_permission_requests (user_id, status, created_at DESC)
        """
    )
    cursor.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_auth_permission_requests_pending
        ON auth_permission_requests (user_id, permission_code)
        WHERE status = 'pending'
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_auth_devices_user_active
        ON auth_devices (user_id, is_revoked, last_active_at DESC)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_device
        ON auth_sessions (user_id, device_id, revoked_at)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_auth_sessions_active_access
        ON auth_sessions (access_token_hash, access_expires_at)
        WHERE revoked_at IS NULL
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_auth_sessions_active_refresh
        ON auth_sessions (refresh_token_hash, refresh_expires_at)
        WHERE revoked_at IS NULL AND refresh_token_hash IS NOT NULL
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_auth_pending_logins_user_expires
        ON auth_pending_logins (user_id, expires_at)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_auth_audit_actor_created
        ON auth_audit_logs (actor_user_id, created_at DESC)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_auth_audit_target_created
        ON auth_audit_logs (target_user_id, created_at DESC)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_auth_audit_module_action_created
        ON auth_audit_logs (module, action, created_at DESC)
        """
    )


def run(sql: str, params: tuple | None = None):
    """Execute an INSERT/UPDATE/DELETE statement."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        conn.commit()
        return cursor.lastrowid
    except Exception as exc:
        conn.rollback()
        if _is_mysql_connection_error(exc):
            _drop_mysql_thread_connection()
        logging.exception("SQL执行失败: %s, 参数: %s", sql, params)
        raise
    finally:
        cursor.close()


def query(sql: str, params: tuple | None = None) -> list[dict]:
    """Execute a SELECT query and return rows as dicts."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)

        rows = cursor.fetchall()
        if not rows:
            return []
        if isinstance(rows[0], dict):
            result = [dict(row) for row in rows]
            if is_mysql_driver():
                conn.commit()
            return result
        columns = [description[0] for description in cursor.description]
        result = [dict(zip(columns, row)) for row in rows]
        if is_mysql_driver():
            conn.commit()
        return result
    except Exception as exc:
        if _is_mysql_connection_error(exc):
            _drop_mysql_thread_connection()
        logging.exception("查询失败: %s, 参数: %s", sql, params)
        raise
    finally:
        cursor.close()


def query_one(sql: str, params: tuple | None = None) -> dict | None:
    """Return the first row from a query or None."""
    results = query(sql, params)
    return results[0] if results else None
