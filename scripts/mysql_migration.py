from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.db.mysql_schema import create_mysql_schema
from shared.project_paths import get_project_paths


MYSQL_APP_ENV_KEYS = {
    "APP_DB_DRIVER",
    "APP_DB_MYSQL_HOST",
    "APP_DB_MYSQL_PORT",
    "APP_DB_MYSQL_DATABASE",
    "APP_DB_MYSQL_USER",
    "APP_DB_MYSQL_PASSWORD",
    "APP_DB_MYSQL_CHARSET",
}

MIGRATION_ORDER = [
    "Veg",
    "Unit",
    "DailyIntakeSheet",
    "PriceHistory",
    "WeeklyPriceEntry",
    "DailyIntakeItem",
    "InventoryTransaction",
    "Config",
    "MigrationVersion",
    "schema_migrations",
    "auth_users",
    "auth_roles",
    "auth_permissions",
    "auth_user_roles",
    "auth_role_permissions",
    "auth_user_permission_overrides",
    "auth_permission_requests",
    "auth_devices",
    "auth_audit_logs",
    "auth_sessions",
    "auth_pending_logins",
]

SKIPPED_RUNTIME_TABLES = {"auth_sessions", "auth_pending_logins"}

FOREIGN_KEY_CHECKS = [
    ("PriceHistory", "vegetable_id", "Veg", "id"),
    ("PriceHistory", "unit_id", "Unit", "id"),
    ("WeeklyPriceEntry", "vegetable_id", "Veg", "id"),
    ("WeeklyPriceEntry", "unit_id", "Unit", "id"),
    ("DailyIntakeItem", "sheet_id", "DailyIntakeSheet", "id"),
    ("DailyIntakeItem", "veg_id", "Veg", "id"),
    ("DailyIntakeItem", "unit_id", "Unit", "id"),
    ("InventoryTransaction", "veg_id", "Veg", "id"),
    ("InventoryTransaction", "unit_id", "Unit", "id"),
    ("auth_user_roles", "user_id", "auth_users", "id"),
    ("auth_user_roles", "role_id", "auth_roles", "id"),
    ("auth_role_permissions", "role_id", "auth_roles", "id"),
    ("auth_role_permissions", "permission_id", "auth_permissions", "id"),
    ("auth_user_permission_overrides", "user_id", "auth_users", "id"),
    ("auth_user_permission_overrides", "permission_id", "auth_permissions", "id"),
    ("auth_permission_requests", "user_id", "auth_users", "id"),
    ("auth_permission_requests", "permission_id", "auth_permissions", "id"),
    ("auth_permission_requests", "reviewer_id", "auth_users", "id"),
    ("auth_devices", "user_id", "auth_users", "id"),
    ("auth_audit_logs", "actor_user_id", "auth_users", "id"),
    ("auth_audit_logs", "target_user_id", "auth_users", "id"),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate the application SQLite database to local MySQL.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for subparser in (
        subparsers.add_parser("backup"),
        subparsers.add_parser("setup"),
        subparsers.add_parser("migrate"),
        subparsers.add_parser("verify"),
        subparsers.add_parser("run-all"),
    ):
        add_common_args(subparser)

    args = parser.parse_args()
    if args.command == "backup":
        backup_dir = create_backup(args)
        print_json({"backup_dir": str(backup_dir)})
    elif args.command == "setup":
        app_password = ensure_app_password(args)
        setup_mysql(args, [args.dryrun_database, args.database], app_password)
        print_json({"databases": [args.dryrun_database, args.database], "app_user": args.app_user})
    elif args.command == "migrate":
        migrate_database(args, args.database)
    elif args.command == "verify":
        result = verify_database(args, args.database)
        print_json(result)
        if not result["ok"]:
            raise SystemExit(1)
    elif args.command == "run-all":
        backup_dir = create_backup(args)
        app_password = ensure_app_password(args)
        setup_mysql(args, [args.dryrun_database, args.database], app_password)
        migrate_database(args, args.dryrun_database, app_password=app_password)
        dryrun_result = verify_database(args, args.dryrun_database, app_password=app_password)
        if not dryrun_result["ok"]:
            print_json({"backup_dir": str(backup_dir), "dryrun": dryrun_result})
            raise SystemExit(1)
        migrate_database(args, args.database, app_password=app_password)
        formal_result = verify_database(args, args.database, app_password=app_password)
        if formal_result["ok"]:
            write_env_local(args, app_password)
        print_json(
            {
                "backup_dir": str(backup_dir),
                "dryrun": dryrun_result,
                "formal": formal_result,
                "env_updated": formal_result["ok"],
            }
        )
        if not formal_result["ok"]:
            raise SystemExit(1)


def add_common_args(parser: argparse.ArgumentParser) -> None:
    paths = get_project_paths()
    parser.add_argument("--sqlite", default=str(paths.database_file), help="SQLite database file to migrate.")
    parser.add_argument("--legacy-sqlite", default=str(paths.legacy_database_file), help="Legacy SQLite database to back up.")
    parser.add_argument("--backup-root", default=str(ROOT_DIR / "backups"), help="Backup parent directory.")
    parser.add_argument("--host", default=os.getenv("APP_DB_MYSQL_HOST", os.getenv("MYSQL_HOST", "localhost")))
    parser.add_argument("--port", type=int, default=int(os.getenv("APP_DB_MYSQL_PORT", os.getenv("MYSQL_PORT", "3306"))))
    parser.add_argument("--database", default=os.getenv("APP_DB_MYSQL_DATABASE", os.getenv("MYSQL_DATABASE", "inspection_report")))
    parser.add_argument("--dryrun-database", default="inspection_report_dryrun")
    parser.add_argument("--app-user", default=os.getenv("APP_DB_MYSQL_USER", os.getenv("MYSQL_USER", "inspection_app")))
    parser.add_argument("--app-password-env", default="MYSQL_APP_PASSWORD")
    parser.add_argument("--root-user", default=os.getenv("MYSQL_ROOT_USER", "root"))
    parser.add_argument("--root-password-env", default="MYSQL_ROOT_PASSWORD")
    parser.add_argument("--charset", default=os.getenv("APP_DB_MYSQL_CHARSET", os.getenv("MYSQL_CHARSET", "utf8mb4")))
    parser.add_argument("--env-file", default=str(ROOT_DIR / ".env.local"))


def ensure_app_password(args: argparse.Namespace) -> str:
    password = os.getenv(args.app_password_env, "").strip()
    return password or read_env_value(Path(args.env_file), "APP_DB_MYSQL_PASSWORD") or secrets.token_urlsafe(32)


def resolve_app_password(args: argparse.Namespace, provided: str | None = None) -> str:
    password = (provided or "").strip()
    if password:
        return password
    password = os.getenv(args.app_password_env, "").strip()
    if password:
        return password
    password = read_env_value(Path(args.env_file), "APP_DB_MYSQL_PASSWORD")
    if password:
        return password
    raise RuntimeError(f"Set {args.app_password_env}, configure APP_DB_MYSQL_PASSWORD, or run setup/run-all first")


def read_env_value(env_path: Path, key: str) -> str:
    if not env_path.exists():
        return ""
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        current_key, value = stripped.split("=", 1)
        if current_key.strip() == key:
            return value.strip().strip('"').strip("'")
    return ""


def create_backup(args: argparse.Namespace) -> Path:
    sqlite_path = Path(args.sqlite)
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {sqlite_path}")

    backup_dir = Path(args.backup_root) / f"mysql-migration-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    backup_dir.mkdir(parents=True, exist_ok=False)

    checkpoint_sqlite(sqlite_path)
    copy_if_exists(sqlite_path, backup_dir / sqlite_path.name)
    copy_if_exists(sqlite_path.with_name(f"{sqlite_path.name}-wal"), backup_dir / f"{sqlite_path.name}-wal")
    copy_if_exists(sqlite_path.with_name(f"{sqlite_path.name}-shm"), backup_dir / f"{sqlite_path.name}-shm")

    legacy_path = Path(args.legacy_sqlite)
    if legacy_path.exists():
        legacy_dir = backup_dir / "legacy"
        legacy_dir.mkdir()
        copy_if_exists(legacy_path, legacy_dir / legacy_path.name)
        copy_if_exists(legacy_path.with_name(f"{legacy_path.name}-wal"), legacy_dir / f"{legacy_path.name}-wal")
        copy_if_exists(legacy_path.with_name(f"{legacy_path.name}-shm"), legacy_dir / f"{legacy_path.name}-shm")

    env_file = Path(args.env_file)
    if env_file.exists():
        copy_if_exists(env_file, backup_dir / env_file.name)

    snapshot = snapshot_sqlite(sqlite_path)
    (backup_dir / "sqlite_snapshot.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return backup_dir


def checkpoint_sqlite(sqlite_path: Path) -> None:
    conn = sqlite3.connect(sqlite_path)
    try:
        conn.execute("PRAGMA wal_checkpoint(FULL)")
    finally:
        conn.close()


def copy_if_exists(source: Path, target: Path) -> None:
    if source.exists():
        shutil.copy2(source, target)


def snapshot_sqlite(sqlite_path: Path) -> dict[str, Any]:
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    try:
        schema = [
            dict(row)
            for row in conn.execute(
                """
                SELECT type, name, tbl_name, sql
                FROM sqlite_master
                WHERE type IN ('table', 'index', 'trigger', 'view')
                ORDER BY type, name
                """
            ).fetchall()
        ]
        counts = table_counts_sqlite(conn)
        samples = {
            table: [dict(row) for row in conn.execute(f"SELECT * FROM {quote_sqlite_ident(table)} LIMIT 5").fetchall()]
            for table in MIGRATION_ORDER
            if table_exists_sqlite(conn, table)
        }
        files = {}
        for path in [sqlite_path, sqlite_path.with_name(f"{sqlite_path.name}-wal"), sqlite_path.with_name(f"{sqlite_path.name}-shm")]:
            if path.exists():
                files[path.name] = {"size": path.stat().st_size, "sha256": file_sha256(path)}
        return {"created_at": datetime.now().isoformat(timespec="seconds"), "schema": schema, "counts": counts, "samples": samples, "files": files}
    finally:
        conn.close()


def table_counts_sqlite(conn: sqlite3.Connection) -> dict[str, int]:
    return {
        table: int(conn.execute(f"SELECT COUNT(*) FROM {quote_sqlite_ident(table)}").fetchone()[0])
        for table in MIGRATION_ORDER
        if table_exists_sqlite(conn, table)
    }


def table_exists_sqlite(conn: sqlite3.Connection, table: str) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def setup_mysql(args: argparse.Namespace, databases: list[str], app_password: str) -> None:
    root_password = os.getenv(args.root_password_env, "").strip()
    if not root_password:
        raise RuntimeError(f"Set {args.root_password_env} before running MySQL setup")
    with connect_mysql(args, user=args.root_user, password=root_password, database=None) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT VERSION() AS version")
            version = cursor.fetchone()["version"]
            for database in databases:
                cursor.execute(
                    f"CREATE DATABASE IF NOT EXISTS {quote_mysql_ident(database)} "
                    f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            app_password_sql = conn.escape(app_password)
            cursor.execute(f"CREATE USER IF NOT EXISTS {quote_mysql_user(args.app_user)}@'localhost' IDENTIFIED BY {app_password_sql}")
            cursor.execute(f"ALTER USER {quote_mysql_user(args.app_user)}@'localhost' IDENTIFIED BY {app_password_sql}")
            for database in databases:
                cursor.execute(
                    f"GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES, DROP "
                    f"ON {quote_mysql_ident(database)}.* TO {quote_mysql_user(args.app_user)}@'localhost'"
                )
            cursor.execute("FLUSH PRIVILEGES")
        conn.commit()
    print_json({"mysql_version": version, "databases_ready": databases, "app_user": args.app_user})


def migrate_database(args: argparse.Namespace, database: str, *, app_password: str | None = None) -> None:
    sqlite_path = Path(args.sqlite)
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {sqlite_path}")
    password = resolve_app_password(args, app_password)

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    try:
        with connect_mysql(args, user=args.app_user, password=password, database=database) as mysql_conn:
            with mysql_conn.cursor() as cursor:
                create_mysql_schema(cursor)
                clear_mysql_tables(cursor)
                imported_counts = import_sqlite_rows(sqlite_conn, cursor)
            mysql_conn.commit()
    except Exception:
        raise
    finally:
        sqlite_conn.close()

    print_json({"database": database, "imported_counts": imported_counts})


def clear_mysql_tables(cursor) -> None:
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    try:
        for table in reversed(MIGRATION_ORDER):
            if table in SKIPPED_RUNTIME_TABLES:
                cursor.execute(f"DELETE FROM {quote_mysql_ident(table)}")
                continue
            cursor.execute(f"DELETE FROM {quote_mysql_ident(table)}")
            cursor.execute(f"ALTER TABLE {quote_mysql_ident(table)} AUTO_INCREMENT = 1")
    finally:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")


def import_sqlite_rows(sqlite_conn: sqlite3.Connection, cursor) -> dict[str, int]:
    imported_counts: dict[str, int] = {}
    for table in MIGRATION_ORDER:
        if not table_exists_sqlite(sqlite_conn, table):
            imported_counts[table] = 0
            continue
        if table in SKIPPED_RUNTIME_TABLES:
            imported_counts[table] = 0
            continue
        rows = sqlite_conn.execute(f"SELECT * FROM {quote_sqlite_ident(table)}").fetchall()
        imported_counts[table] = len(rows)
        if not rows:
            continue
        columns = rows[0].keys()
        column_sql = ", ".join(quote_mysql_ident(column) for column in columns)
        placeholders = ", ".join(["%s"] * len(columns))
        insert_sql = f"INSERT INTO {quote_mysql_ident(table)} ({column_sql}) VALUES ({placeholders})"
        values = [tuple(normalize_sqlite_value(row[column]) for column in columns) for row in rows]
        cursor.executemany(insert_sql, values)
    return imported_counts


def normalize_sqlite_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return value
    return value


def verify_database(args: argparse.Namespace, database: str, *, app_password: str | None = None) -> dict[str, Any]:
    password = resolve_app_password(args, app_password)

    sqlite_path = Path(args.sqlite)
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    failures: list[str] = []
    try:
        sqlite_counts = table_counts_sqlite(sqlite_conn)
        with connect_mysql(args, user=args.app_user, password=password, database=database) as mysql_conn:
            with mysql_conn.cursor() as cursor:
                mysql_counts = table_counts_mysql(cursor)
                compare_counts(sqlite_counts, mysql_counts, failures)
                primary_key_ranges = compare_primary_key_ranges(sqlite_conn, cursor, failures)
                orphan_counts = check_orphans(cursor, failures)
                pending_duplicates = count_pending_permission_duplicates(cursor)
                if pending_duplicates:
                    failures.append(f"auth_permission_requests has {pending_duplicates} duplicate pending requests")
                chinese_samples = sample_chinese_fields(cursor)
    finally:
        sqlite_conn.close()

    return {
        "ok": not failures,
        "database": database,
        "sqlite_counts": sqlite_counts,
        "mysql_counts": mysql_counts,
        "primary_key_ranges": primary_key_ranges,
        "orphan_counts": orphan_counts,
        "pending_permission_duplicate_groups": pending_duplicates,
        "chinese_samples": chinese_samples,
        "failures": failures,
    }


def table_counts_mysql(cursor) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table in MIGRATION_ORDER:
        cursor.execute(f"SELECT COUNT(*) AS count FROM {quote_mysql_ident(table)}")
        counts[table] = int(cursor.fetchone()["count"])
    return counts


def compare_counts(sqlite_counts: dict[str, int], mysql_counts: dict[str, int], failures: list[str]) -> None:
    for table in MIGRATION_ORDER:
        expected = 0 if table in SKIPPED_RUNTIME_TABLES else sqlite_counts.get(table, 0)
        actual = mysql_counts.get(table, 0)
        if actual != expected:
            failures.append(f"{table} count mismatch: expected {expected}, got {actual}")


def compare_primary_key_ranges(sqlite_conn: sqlite3.Connection, cursor, failures: list[str]) -> dict[str, dict[str, int | None]]:
    ranges: dict[str, dict[str, int | None]] = {}
    for table in MIGRATION_ORDER:
        if table in SKIPPED_RUNTIME_TABLES or not table_exists_sqlite(sqlite_conn, table):
            continue
        if "id" not in sqlite_table_columns(sqlite_conn, table):
            continue
        sqlite_range = sqlite_conn.execute(f"SELECT MIN(id) AS min_id, MAX(id) AS max_id FROM {quote_sqlite_ident(table)}").fetchone()
        cursor.execute(f"SELECT MIN(id) AS min_id, MAX(id) AS max_id FROM {quote_mysql_ident(table)}")
        mysql_range = cursor.fetchone()
        ranges[table] = {
            "sqlite_min": sqlite_range["min_id"],
            "sqlite_max": sqlite_range["max_id"],
            "mysql_min": mysql_range["min_id"],
            "mysql_max": mysql_range["max_id"],
        }
        if sqlite_range["min_id"] != mysql_range["min_id"] or sqlite_range["max_id"] != mysql_range["max_id"]:
            failures.append(f"{table} primary key range mismatch")
    return ranges


def sqlite_table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({quote_sqlite_ident(table)})").fetchall()}


def check_orphans(cursor, failures: list[str]) -> dict[str, int]:
    orphan_counts: dict[str, int] = {}
    for child, child_col, parent, parent_col in FOREIGN_KEY_CHECKS:
        key = f"{child}.{child_col}->{parent}.{parent_col}"
        cursor.execute(
            f"""
            SELECT COUNT(*) AS count
            FROM {quote_mysql_ident(child)} c
            LEFT JOIN {quote_mysql_ident(parent)} p
                ON c.{quote_mysql_ident(child_col)} = p.{quote_mysql_ident(parent_col)}
            WHERE c.{quote_mysql_ident(child_col)} IS NOT NULL
              AND p.{quote_mysql_ident(parent_col)} IS NULL
            """
        )
        count = int(cursor.fetchone()["count"])
        orphan_counts[key] = count
        if count:
            failures.append(f"{key} has {count} orphan rows")
    return orphan_counts


def count_pending_permission_duplicates(cursor) -> int:
    cursor.execute(
        """
        SELECT COUNT(*) AS count
        FROM (
            SELECT user_id, permission_code
            FROM auth_permission_requests
            WHERE status = 'pending'
            GROUP BY user_id, permission_code
            HAVING COUNT(*) > 1
        ) pending_duplicates
        """
    )
    return int(cursor.fetchone()["count"])


def sample_chinese_fields(cursor) -> dict[str, list[str]]:
    samples: dict[str, list[str]] = {}
    for table, column in [("Veg", "name"), ("Unit", "name"), ("auth_permissions", "name")]:
        cursor.execute(
            f"""
            SELECT {quote_mysql_ident(column)} AS value
            FROM {quote_mysql_ident(table)}
            WHERE {quote_mysql_ident(column)} REGEXP '[^ -~]'
            LIMIT 5
            """
        )
        samples[f"{table}.{column}"] = [row["value"] for row in cursor.fetchall()]
    return samples


def write_env_local(args: argparse.Namespace, app_password: str) -> None:
    env_path = Path(args.env_file)
    values = {
        "APP_DB_DRIVER": "mysql",
        "APP_DB_MYSQL_HOST": args.host,
        "APP_DB_MYSQL_PORT": str(args.port),
        "APP_DB_MYSQL_DATABASE": args.database,
        "APP_DB_MYSQL_USER": args.app_user,
        "APP_DB_MYSQL_PASSWORD": app_password,
        "APP_DB_MYSQL_CHARSET": args.charset,
    }
    existing_lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    written_keys: set[str] = set()
    next_lines: list[str] = []
    for line in existing_lines:
        if "=" not in line or line.lstrip().startswith("#"):
            next_lines.append(line)
            continue
        key = line.split("=", 1)[0].strip()
        if key in MYSQL_APP_ENV_KEYS:
            next_lines.append(f"{key}={values[key]}")
            written_keys.add(key)
        else:
            next_lines.append(line)
    for key, value in values.items():
        if key not in written_keys:
            next_lines.append(f"{key}={value}")
    env_path.write_text("\n".join(next_lines) + "\n", encoding="utf-8")


def connect_mysql(args: argparse.Namespace, *, user: str, password: str, database: str | None):
    try:
        import pymysql
        from pymysql.cursors import DictCursor
    except ImportError as exc:  # pragma: no cover - environment guard.
        raise RuntimeError("PyMySQL is required. Install backend requirements before running migration.") from exc

    return pymysql.connect(
        host=args.host,
        port=args.port,
        user=user,
        password=password,
        database=database,
        charset=args.charset,
        cursorclass=DictCursor,
        autocommit=False,
    )


def quote_mysql_ident(identifier: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", identifier):
        raise ValueError(f"Unsafe MySQL identifier: {identifier}")
    return f"`{identifier}`"


def quote_mysql_user(user: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", user):
        raise ValueError(f"Unsafe MySQL user: {user}")
    return f"'{user}'"


def quote_sqlite_ident(identifier: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", identifier):
        raise ValueError(f"Unsafe SQLite identifier: {identifier}")
    return f'"{identifier}"'


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
