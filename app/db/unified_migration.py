from __future__ import annotations

import logging
from pathlib import Path

from app.db.store import init_database
from app.db.migration import migrate_json_to_db

logger = logging.getLogger(__name__)

MIGRATION_STAGES = {
    "json_to_sqlite": "JSON → SQLite (蔬菜 / 抑制率)",
    "weekly_quotes": "每周报价 JSON → SQLite",
    "mysql": "SQLite → MySQL",
}


def check_stage(stage: str) -> bool:
    """Check if a specific migration stage has been completed."""
    if stage == "json_to_sqlite":
        return _check_json_to_sqlite()
    elif stage == "weekly_quotes":
        return _check_weekly_quotes()
    elif stage == "mysql":
        return _check_mysql()
    return False


def _check_json_to_sqlite() -> bool:
    """Check if JSON→SQLite migration v1+v2 has been applied."""
    try:
        from app.db.store import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM app_version WHERE category='migration' AND version='v2'")
        row = cursor.fetchone()
        conn.commit()
        return bool(row and row[0] > 0)
    except Exception:
        return False


def _check_weekly_quotes() -> bool:
    """Check if weekly_quotes migration has been applied."""
    try:
        from app.db.store import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM app_version WHERE category='migration' AND version='weekly_quotes_v1'")
        row = cursor.fetchone()
        conn.commit()
        return bool(row and row[0] > 0)
    except Exception:
        return False


def _check_mysql() -> bool:
    """Check if MySQL is configured."""
    from shared.project_paths import get_project_paths
    env_path = get_project_paths().root / ".env.local"
    if not env_path.exists():
        return False
    content = env_path.read_text(encoding="utf-8")
    return "APP_DB_DRIVER=mysql" in content or "MYSQL_APP_PASSWORD" in content


def run_stage(stage: str) -> bool:
    """Run a specific migration stage. Returns True on success."""
    if stage == "json_to_sqlite":
        return _run_json_to_sqlite()
    elif stage == "weekly_quotes":
        return _run_weekly_quotes()
    elif stage == "mysql":
        return _run_mysql()
    return False


def _run_json_to_sqlite() -> bool:
    """Run JSON→SQLite migration."""
    try:
        init_database()
        migrate_json_to_db()
        logger.info("JSON → SQLite migration completed")
        return True
    except Exception as e:
        logger.error(f"JSON → SQLite migration failed: {e}")
        return False


def _run_weekly_quotes() -> bool:
    """Run weekly quotes migration."""
    try:
        from app.models.config_model import load_config
        from app.db.weekly_quote_repository import WeeklyQuoteRepository
        from app.db.store import get_connection

        cfg = load_config()
        records = cfg.get("weekly_quote_summary_records", {})
        if not records:
            logger.info("No weekly quote records to migrate")
            return True

        repo = WeeklyQuoteRepository()
        conn = get_connection()
        for supplier_name, date_entries in records.items():
            if not isinstance(date_entries, list):
                continue
            for day_entry in date_entries:
                if not isinstance(day_entry, dict):
                    continue
                quote_date = day_entry.get("date", "")
                items = day_entry.get("items", [])
                if not quote_date or not items:
                    continue
                try:
                    repo.save_batch(supplier_name, quote_date, items,
                                    source_label="migrated")
                except Exception as e:
                    logger.warning(f"Failed to migrate quotes for {supplier_name} on {quote_date}: {e}")

        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO app_version (category, version) VALUES ('migration', 'weekly_quotes_v1')"
        )
        conn.commit()
        logger.info("Weekly quotes migration completed")
        return True
    except Exception as e:
        logger.error(f"Weekly quotes migration failed: {e}")
        return False


def _run_mysql() -> bool:
    """Run SQLite→MySQL migration via existing script."""
    try:
        import subprocess
        result = subprocess.run(
            ["python", "scripts/mysql_migration.py", "run-all"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            logger.error(f"MySQL migration failed: {result.stderr}")
            return False
        logger.info("MySQL migration completed")
        return True
    except Exception as e:
        logger.error(f"MySQL migration failed: {e}")
        return False


def verify_all() -> dict:
    """Verify all migration stages. Returns a dict with pass/fail per stage."""
    results = {}
    for stage, label in MIGRATION_STAGES.items():
        results[stage] = {
            "label": label,
            "completed": check_stage(stage),
        }
    return results


def run_all() -> dict:
    """Run all pending migrations. Returns a dict with pass/fail per stage."""
    results = {}
    for stage, label in MIGRATION_STAGES.items():
        if check_stage(stage):
            results[stage] = {"label": label, "status": "already_done"}
        else:
            ok = run_stage(stage)
            results[stage] = {"label": label, "status": "ok" if ok else "failed"}
    return results
