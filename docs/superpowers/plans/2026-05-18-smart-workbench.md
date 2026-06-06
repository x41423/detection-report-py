# Smart Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Merge pesticide detection and data migration into a unified "Smart Workbench" with 13 automated optimizations across 6 phases.

**Architecture:** Backend services (SmartDetectionService, GapDetectionService, OutputArchiver, ExportService, LowStockNotifier) power a redesigned Vue.js frontend page (SmartDetection.vue) with three-panel vegetable recommendation layout. Data migration runs automatically on startup via unified `scripts/migrate.py` CLI. Configuration consolidates to `config/app.json`.

**Tech Stack:** Python/FastAPI backend, Vue 3 + TypeScript + Element Plus frontend, python-docx, SQLite/MySQL, LibreOffice (headless for PDF)

---

### Task 1: Extract DEFAULT_CONFIG to config/defaults.json

**Files:**
- Create: `config/defaults.json`
- Modify: `app/models/config_model.py:9-54`

- [ ] **Step 1: Create config/defaults.json with all defaults**

```json
{
  "output_dir": "C:\\Users\\34585\\Desktop\\滨鲜\\检测报告py文件夹",
  "inspector_name": "朱林初",
  "date_format": "{y}年{m}月{d}日",
  "high_risk": ["韭菜", "小葱", "毛毛菜", "香菜", "蒜黄", "白萝卜", "小莲藕", "菠菜"],
  "low_risk": ["黄瓜", "玉米", "光玉米", "毛玉米", "冬瓜", "老南瓜", "长豆角", "春笋", "冬笋"],
  "rate_ranges": {
    "high": {"min": 20.0, "max": 60.0, "mean": 40.0, "std": 5.0},
    "low": {"min": 0.5, "max": 15.0, "mean": 6.0, "std": 2.0},
    "other": {"min": 5.0, "max": 40.0, "mean": 20.0, "std": 8.0}
  },
  "big_table_path": "",
  "small_templates": {
    "滨鲜": "", "1号": "", "5号": "", "6号": "", "7号": "", "8号": "", "顾家": ""
  },
  "pesticide_templates": {"big": {}, "small": {}},
  "transfer_templates": {},
  "last_used_small_type": "滨鲜",
  "ui_theme": "light_cyan.xml",
  "data_transfer_use_shared_date": true,
  "data_transfer_last_date": "",
  "data_transfer_big_folder": "",
  "dish_name_aliases": {},
  "funasr_lab_memory": {"recent_hotwords": [], "name_unit_memory": []},
  "funasr_lab_daily_tracking": {"records": {}},
  "weekly_price_aliases": {},
  "weekly_price_output_path": "",
  "weekly_quote_summary_workbook_path": "",
  "weekly_quote_summary_records": {},
  "weekly_quote_summary_unit_memory": {},
  "inventory_low_stock_threshold": 3
}
```

- [ ] **Step 2: Modify config_model.py to load from defaults.json**

```python
import copy
import json
from pathlib import Path

from app.utils.weekly_price_update import get_default_weekly_price_aliases
from shared.project_paths import get_project_paths


def _get_defaults_path() -> Path:
    return Path(__file__).resolve().parent.parent / "config" / "defaults.json"


def _load_defaults() -> dict:
    path = _get_defaults_path()
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            cfg = json.load(f)
    else:
        cfg = {}
    cfg.setdefault("weekly_price_aliases", get_default_weekly_price_aliases())
    return cfg


def _default_config() -> dict:
    """Lazy-loaded default config, cached after first call."""
    return _load_defaults()


def get_config_path() -> str:
    return str(get_project_paths().config_file)


def get_legacy_config_path() -> str:
    return str(get_project_paths().legacy_root_config_file)


def resolve_read_config_path() -> Path:
    paths = get_project_paths()
    if paths.config_file.exists():
        return paths.config_file
    if paths.legacy_root_config_file.exists():
        return paths.legacy_root_config_file
    return paths.config_file


def _merge_and_remove_legacy(cfg: dict):
    """If legacy root config.json exists, merge its unique keys into canonical config/app.json and rename legacy to .bak."""
    paths = get_project_paths()
    legacy = paths.legacy_root_config_file
    canonical = paths.config_file
    if not legacy.exists() or legacy == canonical:
        return
    try:
        with legacy.open("r", encoding="utf-8") as f:
            legacy_cfg = json.load(f)
    except Exception:
        return
    changed = False
    for k, v in legacy_cfg.items():
        if k not in cfg:
            cfg[k] = v
            changed = True
    if changed:
        canonical.parent.mkdir(parents=True, exist_ok=True)
        with canonical.open("w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    bak = legacy.with_suffix(".merged.bak")
    legacy.rename(bak)
    print(f"[CONFIG] 已合并 legacy config.json → {bak}")


def load_config() -> dict:
    path = resolve_read_config_path()
    canonical_path = Path(get_config_path())
    defaults = _default_config()

    if not path.exists():
        save_config(defaults)
        return copy.deepcopy(defaults)

    try:
        with path.open("r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}

    changed = False
    for k, v in defaults.items():
        if k not in cfg:
            cfg[k] = copy.deepcopy(v)
            changed = True

    if changed or path != canonical_path:
        save_config(cfg)

    # Merge legacy root config.json if it still exists
    _merge_and_remove_legacy(cfg)

    return cfg


def save_config(cfg: dict):
    path = Path(get_config_path())
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存配置失败: {e}")
```

- [ ] **Step 3: Remove DEFAULT_CONFIG dict from config_model.py** (replaced by _default_config())

- [ ] **Step 4: Run test to verify config loading still works**

```powershell
python -c "from app.models.config_model import load_config; c = load_config(); print(c.get('high_risk'))"
```
Expected: prints high_risk list from defaults.json

- [ ] **Step 5: Commit**

```bash
git add config/defaults.json app/models/config_model.py
git commit -m "refactor: extract DEFAULT_CONFIG to config/defaults.json, add legacy config merge"
```

---

### Task 2: Create unified migration CLI — scripts/migrate.py

**Files:**
- Create: `scripts/migrate.py`
- Create: `app/db/unified_migration.py`

- [ ] **Step 1: Create app/db/unified_migration.py**

```python
from __future__ import annotations

import logging
from pathlib import Path

from app.db.store import init_database
from app.db.migration import migrate_json_to_db, backup_database, MigrationVersion

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
        import json
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
        for supplier_name, entries in records.items():
            if not isinstance(entries, list):
                continue
            batch_data = []
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                batch_data.append({
                    "date": entry.get("date", ""),
                    "items": entry.get("items", []),
                    "supplier": supplier_name,
                })
            if batch_data:
                try:
                    repo.save_batch(supplier_name, batch_data)
                except Exception as e:
                    logger.warning(f"Failed to migrate quotes for {supplier_name}: {e}")

        # Mark migration version
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
```

- [ ] **Step 2: Create scripts/migrate.py CLI**

```python
#!/usr/bin/env python3
"""Unified migration CLI for detection-report-py.

Usage:
    python scripts/migrate.py check    # Check migration status
    python scripts/migrate.py run      # Run all pending migrations
    python scripts/migrate.py verify   # Verify all migrations
    python scripts/migrate.py status   # Show detailed status
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.unified_migration import verify_all, run_all, MIGRATION_STAGES


def cmd_check():
    results = verify_all()
    all_done = True
    for stage, info in results.items():
        status = "✓" if info["completed"] else "✗"
        if not info["completed"]:
            all_done = False
        print(f"  [{status}] {info['label']}")
    if all_done:
        print("所有迁移已完成")
    else:
        print("存在待执行的迁移，运行: python scripts/migrate.py run")


def cmd_run():
    print("开始执行统一迁移...")
    results = run_all()
    for stage, info in results.items():
        status = info["status"]
        symbol = "✓" if status in ("ok", "already_done") else "✗"
        print(f"  [{symbol}] {info['label']}: {status}")
    failed = any(v["status"] == "failed" for v in results.values())
    if failed:
        print("部分迁移失败，请检查日志")
        sys.exit(1)
    else:
        print("全部迁移完成")


def cmd_verify():
    results = verify_all()
    all_done = all(v["completed"] for v in results.values())
    print(f"迁移验证: {'全部通过' if all_done else '存在未完成的迁移'}")
    for stage, info in results.items():
        status = "✓" if info["completed"] else "✗"
        print(f"  [{status}] {info['label']}")


def cmd_status():
    results = verify_all()
    print("迁移状态:")
    for stage, info in results.items():
        status = "已完成" if info["completed"] else "未迁移"
        print(f"  {info['label']}: {status}")


def main():
    parser = argparse.ArgumentParser(description="统一数据迁移工具")
    parser.add_argument("command", choices=["check", "run", "verify", "status"],
                        help="迁移命令")
    args = parser.parse_args()

    commands = {
        "check": cmd_check,
        "run": cmd_run,
        "verify": cmd_verify,
        "status": cmd_status,
    }
    commands[args.command]()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Test migration check**

```powershell
python scripts/migrate.py check
```

Expected: prints status of each migration stage

- [ ] **Step 4: Commit**

```bash
git add scripts/migrate.py app/db/unified_migration.py
git commit -m "feat: add unified migration CLI with check/run/verify/status commands"
```

---

### Task 3: Update start.bat to auto-run migration

**Files:**
- Modify: `start.bat:20-25` (insert migration step after variable setup)

- [ ] **Step 1: Add migration step before backend start**

Insert between line 39 (`exit /b 1` block for backend check) and line 47 (`[STEP 1/5] Resolving backend...`):

```batch
echo [STEP 0/6] Running data migration check...
pushd "!PD!"
"!PD!\.venv-win10\Scripts\python.exe" scripts\migrate.py run >nul 2>&1
if errorlevel 1 (
    "!PD!\.venv-win11\Scripts\python.exe" scripts\migrate.py run >nul 2>&1
)
if errorlevel 1 (
    "!PD!\.venv\Scripts\python.exe" scripts\migrate.py run >nul 2>&1
)
if errorlevel 1 (
    where.exe py >nul 2>&1 && py -3 scripts\migrate.py run >nul 2>&1
)
if errorlevel 1 (
    echo [WARN] Migration check failed, continuing startup...
)
popd
```

Update step numbering from `[STEP 1/5]` through `[STEP 5/5]` to `[STEP 1/6]` through `[STEP 5/6]`.

- [ ] **Step 2: Update step numbering in start.bat**

Replace all occurrences in order:
- `[STEP 1/5]` → `[STEP 1/6]` (Resolving backend)
- `[STEP 2/5]` → `[STEP 2/6]` (Checking npm)
- `[STEP 3/5]` → `[STEP 3/6]` (Checking frontend deps)
- `[STEP 4/5]` → `[STEP 4/6]` (Starting backend)
- `[STEP 5/5]` → `[STEP 5/6]` (Starting frontend)

- [ ] **Step 3: Verify start.bat syntax**

```powershell
Get-Content start.bat | Select-String "STEP"
```
Expected: shows [STEP 0/6] through [STEP 5/6]

- [ ] **Step 4: Commit**

```bash
git add start.bat
git commit -m "feat: auto-run unified migration on startup"
```

---

### Task 4: Create SmartTemplateMatcher service

**Files:**
- Create: `backend/services/smart_template_matcher.py`
- Test: `tests/test_smart_template_matcher.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_smart_template_matcher.py
import os
import tempfile
from datetime import date
from pathlib import Path
from backend.services.smart_template_matcher import SmartTemplateMatcher


def test_match_exact():
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, "big"), exist_ok=True)
        exact = Path(tmpdir) / "big" / "农残检测记录表2026.05.18.docx"
        exact.touch()

        matcher = SmartTemplateMatcher(tmpdir)
        result = matcher.match("big", date(2026, 5, 18))
        assert result is not None
        assert "2026.05.18" in str(result)


def test_match_fuzzy_latest():
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, "big"), exist_ok=True)
        f1 = Path(tmpdir) / "big" / "农残检测记录表2026.05.15.docx"
        f1.touch()
        f2 = Path(tmpdir) / "big" / "农残检测记录表2026.05.17.docx"
        f2.touch()

        matcher = SmartTemplateMatcher(tmpdir)
        result = matcher.match("big", date(2026, 5, 18))
        assert result is not None
        assert "2026.05.17" in str(result)


def test_match_fallback_to_template_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        matcher = SmartTemplateMatcher(tmpdir)
        result = matcher.match("big", date(2026, 5, 18))
        if result is not None:
            assert ".docx" in str(result).lower()
```

- [ ] **Step 2: Run test to verify it fails**

```powershell
pytest tests/test_smart_template_matcher.py -v
```
Expected: FAIL (module not found)

- [ ] **Step 3: Implement SmartTemplateMatcher**

```python
# backend/services/smart_template_matcher.py
import logging
import re
from datetime import date
from pathlib import Path

from backend.services.template_library_service import get_pesticide_template_path

logger = logging.getLogger(__name__)

BIG_PATTERN = re.compile(r"农残检测记录表(\d{4})\.(\d{2})\.(\d{2})", re.IGNORECASE)
SMALL_PATTERN = re.compile(r"单位农残记录表(\d{1,2})\.(\d{1,2})", re.IGNORECASE)


class SmartTemplateMatcher:
    """Intelligently match pesticide detection templates by date, falling back to nearest match."""

    def __init__(self, big_dir: str | None = None, small_dir: str | None = None):
        self.big_dir = Path(big_dir) if big_dir else None
        self.small_dir = Path(small_dir) if small_dir else None

    def match(self, kind: str, target_date: date) -> Path | None:
        """Match a template file for the given kind (big/small) and target date.
        
        Priority:
        1. Exact match by date pattern
        2. Closest date match in same directory
        3. Fallback to template library
        """
        if kind == "big":
            return self._match_big(target_date)
        elif kind == "small":
            return self._match_small(target_date)
        return None

    def _match_big(self, target_date: date) -> Path | None:
        # 1. Exact match
        if self.big_dir and self.big_dir.is_dir():
            exact_name = f"农残检测记录表{target_date.year}.{target_date.month:02d}.{target_date.day:02d}.docx"
            exact_path = self.big_dir / exact_name
            if exact_path.exists():
                return exact_path

            # 2. Closest match
            best = self._find_closest(self.big_dir, BIG_PATTERN, target_date, suffix="-template.docx")
            if best:
                return best

        # 3. Fallback to template library
        try:
            return get_pesticide_template_path("big")
        except FileNotFoundError:
            logger.warning("No big template found in library")
            return None

    def _match_small(self, target_date: date) -> Path | None:
        if self.small_dir and self.small_dir.is_dir():
            exact_name = f"单位农残记录表{target_date.month}.{target_date.day}.docx"
            exact_path = self.small_dir / exact_name
            if exact_path.exists():
                return exact_path

            best = self._find_closest(self.small_dir, SMALL_PATTERN, target_date,
                                      month_format="{m}.{d}", suffix="-template.docx")
            if best:
                return best

        try:
            return get_pesticide_template_path("small")
        except FileNotFoundError:
            logger.warning("No small template found in library")
            return None

    def _find_closest(self, directory: Path, pattern: re.Pattern,
                      target_date: date, suffix: str = "", **fmt_kwargs) -> Path | None:
        candidates = []
        for f in directory.glob("*.docx"):
            match = pattern.search(f.name)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 3:
                        y, m, d = int(groups[0]), int(groups[1]), int(groups[2])
                        file_date = date(y, m, d)
                    elif len(groups) == 2:
                        m, d = int(groups[0]), int(groups[1])
                        file_date = date(target_date.year, m, d)
                    else:
                        continue
                    diff = abs((target_date - file_date).days)
                    candidates.append((diff, f))
                except (ValueError, IndexError):
                    continue

        if candidates:
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1]

        return None
```

- [ ] **Step 4: Run test to verify it passes**

```powershell
pytest tests/test_smart_template_matcher.py -v
```
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/smart_template_matcher.py tests/test_smart_template_matcher.py
git commit -m "feat: add SmartTemplateMatcher with exact/fuzzy/fallback matching"
```

---

### Task 5: Create LowStockNotifier service

**Files:**
- Create: `backend/services/low_stock_notifier.py`
- Test: `tests/test_low_stock_notifier.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_low_stock_notifier.py
from unittest.mock import patch, MagicMock
from backend.services.low_stock_notifier import LowStockNotifier


def test_check_low_stock():
    mock_data = [
        {"item_name": "菠菜", "balance": 2.0, "unit": "斤"},
        {"item_name": "大白菜", "balance": 10.0, "unit": "斤"},
        {"item_name": "白萝卜", "balance": 3.0, "unit": "斤"},
    ]

    with patch.object(LowStockNotifier, "_query_balances", return_value=mock_data):
        notifier = LowStockNotifier(threshold=3)
        alerts = notifier.check()
        assert len(alerts) == 2
        assert alerts[0]["item_name"] == "菠菜"
        assert alerts[1]["item_name"] == "白萝卜"


def test_check_no_alerts():
    mock_data = [
        {"item_name": "菠菜", "balance": 10.0, "unit": "斤"},
    ]
    with patch.object(LowStockNotifier, "_query_balances", return_value=mock_data):
        notifier = LowStockNotifier(threshold=3)
        alerts = notifier.check()
        assert len(alerts) == 0
```

- [ ] **Step 2: Run test to verify it fails**

```powershell
pytest tests/test_low_stock_notifier.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement LowStockNotifier**

```python
# backend/services/low_stock_notifier.py
import logging
from backend.services.config_service import get_config

logger = logging.getLogger(__name__)


class LowStockNotifier:
    """Check inventory balances against low-stock threshold."""

    def __init__(self, threshold: int | None = None):
        if threshold is None:
            threshold = get_config().get("inventory_low_stock_threshold", 3)
        self.threshold = threshold

    def _query_balances(self) -> list[dict]:
        from app.db.inventory_repository import InventoryRepository
        repo = InventoryRepository()
        try:
            return repo.get_balances(limit=1000)
        except Exception as e:
            logger.error(f"Failed to query balances: {e}")
            return []

    def check(self) -> list[dict]:
        balances = self._query_balances()
        alerts = []
        for item in balances:
            balance = item.get("balance", 0)
            if isinstance(balance, (int, float)) and balance <= self.threshold:
                alerts.append({
                    "item_name": item.get("item_name", item.get("veg_name", "")),
                    "balance": balance,
                    "unit": item.get("unit", ""),
                    "threshold": self.threshold,
                })
        if alerts:
            logger.warning(f"Low stock alert: {len(alerts)} items below threshold {self.threshold}")
        return alerts
```

- [ ] **Step 4: Run test to verify it passes**

```powershell
pytest tests/test_low_stock_notifier.py -v
```
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/low_stock_notifier.py tests/test_low_stock_notifier.py
git commit -m "feat: add LowStockNotifier for inventory threshold alerts"
```

---

### Task 6: Create OutputArchiver service

**Files:**
- Create: `backend/services/output_archiver.py`
- Test: `tests/test_output_archiver.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_output_archiver.py
import os
import tempfile
from datetime import date
from pathlib import Path
from backend.services.output_archiver import OutputArchiver


def test_archive_single_day():
    with tempfile.TemporaryDirectory() as output_root:
        # Simulate generated files
        big_dir = Path(output_root) / "_workspace"
        big_dir.mkdir(exist_ok=True)
        big_file = big_dir / "农残检测记录表2026.05.18.docx"
        big_file.write_text("fake docx")

        archiver = OutputArchiver(output_root)
        result = archiver.archive(big_dir, date(2026, 5, 18))

        expected_dir = Path(output_root) / "2026" / "05" / "18" / "big"
        assert expected_dir.exists()
        assert (expected_dir / "农残检测记录表2026.05.18.docx").exists()
        assert result["archived_count"] >= 1


def test_archive_structure():
    with tempfile.TemporaryDirectory() as output_root:
        archiver = OutputArchiver(output_root)
        d = date(2026, 5, 18)
        archiver.archive(output_root, d)
        assert (Path(output_root) / "2026" / "05" / "18").exists()
```

- [ ] **Step 2: Run test to verify it fails**

```powershell
pytest tests/test_output_archiver.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement OutputArchiver**

```python
# backend/services/output_archiver.py
import json
import logging
import shutil
from datetime import date, datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class OutputArchiver:
    """Archive generated pesticide detection reports into year/month/day structure."""

    def __init__(self, output_root: str):
        self.output_root = Path(output_root)

    def archive(self, workspace_dir: Path, target_date: date) -> dict:
        year = str(target_date.year)
        month = f"{target_date.month:02d}"
        day = f"{target_date.day:02d}"

        archive_base = self.output_root / year / month / day
        archive_big = archive_base / "big"
        archive_small = archive_base / "small"
        archive_big.mkdir(parents=True, exist_ok=True)
        archive_small.mkdir(parents=True, exist_ok=True)

        counts = {"big": 0, "small": 0}

        for f in workspace_dir.glob("*.docx"):
            name = f.name
            if "农残检测记录表" in name:
                shutil.copy2(f, archive_big / name)
                counts["big"] += 1
            elif "单位农残记录表" in name:
                shutil.copy2(f, archive_small / name)
                counts["small"] += 1

        total = counts["big"] + counts["small"]
        logger.info(f"Archived {total} files to {archive_base}")

        self._update_index()
        return {
            "archived_count": total,
            "big_count": counts["big"],
            "small_count": counts["small"],
            "archive_path": str(archive_base),
        }

    def _update_index(self):
        index_path = self.output_root / "archive.json"
        index = {}
        if index_path.exists():
            try:
                with index_path.open("r", encoding="utf-8") as f:
                    index = json.load(f)
            except Exception:
                pass

        index["last_updated"] = datetime.now().isoformat()

        try:
            with index_path.open("w", encoding="utf-8") as f:
                json.dump(index, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to update archive index: {e}")

    def find_report(self, target_date: date, kind: str = "big") -> Path | None:
        year = str(target_date.year)
        month = f"{target_date.month:02d}"
        day = f"{target_date.day:02d}"
        archive_dir = self.output_root / year / month / day / kind
        if not archive_dir.is_dir():
            return None
        docs = list(archive_dir.glob("*.docx"))
        return docs[0] if docs else None

    def find_missing_dates(self, start_date: date, end_date: date) -> list[date]:
        missing = []
        current = start_date
        while current <= end_date:
            year = str(current.year)
            month = f"{current.month:02d}"
            day = f"{current.day:02d}"
            big_dir = self.output_root / year / month / day / "big"
            if not big_dir.is_dir() or not list(big_dir.glob("*.docx")):
                missing.append(current)
            current = current.replace(day=current.day + 1) if self._can_increment_day(current) else None
            if current is None:
                break
        return missing

    def _can_increment_day(self, d: date) -> bool:
        try:
            d.replace(day=d.day + 1)
            return True
        except ValueError:
            return False
```

- [ ] **Step 4: Run test to verify it passes**

```powershell
pytest tests/test_output_archiver.py -v
```
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/output_archiver.py tests/test_output_archiver.py
git commit -m "feat: add OutputArchiver for year/month/day organization"
```

---

### Task 7: Create ExportService for PDF export

**Files:**
- Create: `backend/services/export_service.py`
- Test: `tests/test_export_service.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_export_service.py
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from backend.services.export_service import ExportService


def test_export_result_structure():
    with tempfile.TemporaryDirectory() as tmpdir:
        service = ExportService()
        result = service.export_detection_report(
            target_date="2026-05-18",
            docx_paths=["/fake/a.docx"],
            output_dir=tmpdir,
            format="docx"
        )
        assert "docx_files" in result
        assert len(result["docx_files"]) == 1


@patch("subprocess.run")
def test_docx_to_pdf_mock(mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    service = ExportService()
    result = service.docx_to_pdf(Path("/fake/test.docx"))
    assert result is not None
```

- [ ] **Step 2: Run test to verify it fails**

```powershell
pytest tests/test_export_service.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement ExportService**

```python
# backend/services/export_service.py
import logging
import shutil
import subprocess
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)


class ExportService:
    """Export detection reports to PDF via LibreOffice headless or just copy DOCX."""

    LIBREOFFICE_PATHS = [
        "soffice",
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]

    def docx_to_pdf(self, docx_path: Path) -> Path | None:
        """Convert a single .docx to .pdf using LibreOffice headless. Returns PDF path or None."""
        if not docx_path.exists():
            logger.warning(f"DOCX not found: {docx_path}")
            return None

        output_dir = docx_path.parent

        for lo_path in self.LIBREOFFICE_PATHS:
            try:
                result = subprocess.run(
                    [lo_path, "--headless", "--convert-to", "pdf",
                     "--outdir", str(output_dir), str(docx_path)],
                    capture_output=True, text=True, timeout=60
                )
                if result.returncode == 0:
                    pdf_path = output_dir / f"{docx_path.stem}.pdf"
                    if pdf_path.exists():
                        return pdf_path
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
            except Exception as e:
                logger.warning(f"LibreOffice convert failed with {lo_path}: {e}")

        logger.warning("LibreOffice not available, PDF conversion skipped")
        return None

    def export_detection_report(self, target_date: str, docx_paths: list[str],
                                 output_dir: str, format: str = "both") -> dict:
        result = {"docx_files": [], "pdf_files": [], "date": target_date}

        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        for docx_str in docx_paths:
            src = Path(docx_str)
            if not src.exists():
                continue
            dst = out / src.name
            shutil.copy2(src, dst)
            result["docx_files"].append(str(dst))

            if format in ("pdf", "both"):
                pdf = self.docx_to_pdf(dst)
                if pdf:
                    result["pdf_files"].append(str(pdf))

        return result
```

- [ ] **Step 4: Run test to verify it passes**

```powershell
pytest tests/test_export_service.py -v
```
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/export_service.py tests/test_export_service.py
git commit -m "feat: add ExportService with LibreOffice PDF conversion"
```

---

### Task 8: Create SmartDetectionService

**Files:**
- Create: `backend/services/smart_detection_service.py`
- Test: `tests/test_smart_detection_service.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_smart_detection_service.py
from datetime import date
from unittest.mock import patch, MagicMock
from backend.services.smart_detection_service import SmartDetectionService


def test_recommend_returns_structure():
    with patch("backend.services.smart_detection_service.DailyIntakeService") as mock_di, \
         patch("backend.services.smart_detection_service.InventoryRepository") as mock_inv:

        mock_di_instance = MagicMock()
        mock_di.return_value = mock_di_instance
        mock_di_instance.get_sheet.return_value = {
            "date": "2026-05-18",
            "items": [
                {"veg_name": "大白菜", "normalized_name": "大白菜"},
                {"veg_name": "黄瓜", "normalized_name": "黄瓜"},
            ]
        }

        mock_inv_instance = MagicMock()
        mock_inv.return_value = mock_inv_instance
        mock_inv_instance.get_balances.return_value = [
            {"veg_name": "菠菜", "balance": 5.0},
        ]

        svc = SmartDetectionService()
        result = svc.recommend(date(2026, 5, 18))

        assert "today_intake" in result
        assert "yesterday_inventory" in result
        assert len(result["today_intake"]) == 2


def test_execute_returns_result():
    with patch("backend.services.smart_detection_service.DataGeneratorService") as mock_gen, \
         patch("backend.services.smart_detection_service.process_documents") as mock_proc, \
         patch("backend.services.smart_detection_service.OutputArchiver") as mock_arch, \
         patch("backend.services.smart_detection_service.LowStockNotifier") as mock_notif:

        mock_gen_instance = MagicMock()
        mock_gen.return_value = mock_gen_instance
        mock_gen_instance.generate_rates.return_value = [
            {"variety": "大白菜", "rate": "5.044%"}
        ]

        mock_notif_instance = MagicMock()
        mock_notif.return_value = mock_notif_instance
        mock_notif_instance.check.return_value = []

        svc = SmartDetectionService()
        result = svc.execute({
            "selected_varieties": ["大白菜"],
            "date": "2026-05-18",
            "big_template": "/fake/big.docx",
            "small_template": "/fake/small.docx",
            "output_dir": "/fake/output",
            "inspector_name": "测试员",
        })

        assert result["success"] is True
        assert "summary" in result
```

- [ ] **Step 2: Run test to verify it fails**

```powershell
pytest tests/test_smart_detection_service.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement SmartDetectionService**

```python
# backend/services/smart_detection_service.py
import json
import logging
from datetime import date, timedelta
from pathlib import Path

from backend.services.config_service import get_config
from backend.services.pesticide_service import PesticideService
from backend.services.data_gen_service import DataGeneratorService
from backend.services.low_stock_notifier import LowStockNotifier
from backend.services.output_archiver import OutputArchiver
from backend.services.export_service import ExportService
from app.utils.doc_handler import process_documents

logger = logging.getLogger(__name__)


class SmartDetectionService:
    """Orchestrates intelligent pesticide detection workflow — recommend veggies, generate reports."""

    def __init__(self):
        cfg = get_config()
        self._gen = DataGeneratorService(
            high_risk=cfg.get("high_risk", []),
            low_risk=cfg.get("low_risk", []),
            rate_ranges=cfg.get("rate_ranges", {}),
        )
        self.output_root = cfg.get("output_dir", "")

    def recommend(self, target_date: date) -> dict:
        """Recommend vegetables to test based on today's intake and yesterday's untested inventory."""
        result = {
            "today_intake": [],
            "yesterday_inventory": [],
            "missing_dates": [],
        }

        try:
            from backend.services.daily_intake_service import DailyIntakeService
            di_service = DailyIntakeService()
            sheet = di_service.get_sheet(target_date.isoformat())
            seen = set()
            for item in sheet.get("items", []):
                name = item.get("normalized_name") or item.get("veg_name", "")
                if name and name not in seen:
                    seen.add(name)
                    result["today_intake"].append({
                        "name": name,
                        "source": "daily_intake",
                        "category": item.get("category", ""),
                    })
        except Exception as e:
            logger.warning(f"Failed to load daily intake for {target_date}: {e}")

        try:
            yesterday = target_date - timedelta(days=1)
            archiver = OutputArchiver(self.output_root)
            yesterday_reports = archiver.find_report(yesterday, "big")

            if not yesterday_reports:
                from backend.services.daily_intake_service import DailyIntakeService
                di_service = DailyIntakeService()
                yesterday_sheet = di_service.get_sheet(yesterday.isoformat())
                for item in yesterday_sheet.get("items", []):
                    name = item.get("normalized_name") or item.get("veg_name", "")
                    if name and name not in seen:
                        seen.add(name)
                        result["yesterday_inventory"].append({
                            "name": name,
                            "source": "yesterday_inventory",
                            "reason": "昨日未检",
                        })
        except Exception as e:
            logger.warning(f"Failed to check yesterday inventory: {e}")

        return result

    def execute(self, request: dict) -> dict:
        """
        Execute the full detection pipeline.
        request keys: selected_varieties, date, big_template, small_template,
                       output_dir, inspector_name, manual_additions (optional),
                       export_format (optional: 'docx', 'pdf', 'both')
        """
        selected = list(request.get("selected_varieties", []))
        manual = request.get("manual_additions", [])
        all_veggies = selected + manual

        if not all_veggies:
            return {"success": False, "error": "没有选择任何蔬菜"}

        big_template = request.get("big_template", "")
        small_template = request.get("small_template", "")
        target_date = request.get("date", "")
        output_dir = request.get("output_dir", self.output_root)
        inspector_name = request.get("inspector_name", "检测员")
        export_format = request.get("export_format", "docx")

        if not big_template or not small_template:
            return {"success": False, "error": "模板路径未设置"}

        # Generate rates
        try:
            rates = self._gen.generate_rates(all_veggies)
        except Exception as e:
            return {"success": False, "error": f"抑制率生成失败: {e}"}

        # Build JSON
        json_data = json.dumps(rates, ensure_ascii=False)

        # Process documents
        try:
            process_documents(
                big_template, small_template, rates,
                target_date, Path(output_dir), inspector_name
            )
        except Exception as e:
            return {"success": False, "error": f"文档生成失败: {e}"}

        # Archive output
        archiver = OutputArchiver(output_dir)
        workspace = Path(output_dir) / ".pesticide_workspace" if Path(output_dir).exists() else Path(output_dir)
        archive_result = {"archived_count": 0}
        try:
            archive_result = archiver.archive(Path(output_dir), self._parse_date(target_date))
        except Exception as e:
            logger.warning(f"Archive failed: {e}")

        # PDF export
        pdf_files = []
        if export_format in ("pdf", "both"):
            try:
                exporter = ExportService()
                export_result = exporter.export_detection_report(
                    target_date,
                    [str(p) for p in Path(output_dir).glob("*.docx")],
                    output_dir,
                    format=export_format
                )
                pdf_files = export_result.get("pdf_files", [])
            except Exception as e:
                logger.warning(f"PDF export failed: {e}")

        # Low stock check
        alerts = []
        try:
            notifier = LowStockNotifier()
            alerts = notifier.check()
        except Exception as e:
            logger.warning(f"Low stock check failed: {e}")

        return {
            "success": True,
            "output_paths": archive_result,
            "pdf_files": pdf_files,
            "low_stock_alerts": alerts,
            "summary": {
                "total_varieties": len(all_veggies),
                "generated_date": target_date,
                "inspector": inspector_name,
            }
        }

    def _parse_date(self, date_str: str) -> date:
        try:
            return date.fromisoformat(date_str)
        except (ValueError, TypeError):
            return date.today()
```

- [ ] **Step 4: Run test to verify it passes**

```powershell
pytest tests/test_smart_detection_service.py -v
```
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/smart_detection_service.py tests/test_smart_detection_service.py
git commit -m "feat: add SmartDetectionService with recommend+execute pipeline"
```

---

### Task 9: Create GapDetectionService

**Files:**
- Create: `backend/services/gap_detection_service.py`
- Test: `tests/test_gap_detection_service.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_gap_detection_service.py
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import patch
from backend.services.gap_detection_service import GapDetectionService


def test_detect_gaps():
    with tempfile.TemporaryDirectory() as tmpdir:
        Path(tmpdir, "2026", "05", "18", "big").mkdir(parents=True)
        (Path(tmpdir) / "2026" / "05" / "18" / "big" / "test.docx").touch()

        svc = GapDetectionService(output_root=tmpdir)
        gaps = svc.detect_gaps(date(2026, 5, 15), date(2026, 5, 20))

        # 05-18 has report, others are gaps
        assert len(gaps) == 3  # 15, 16, 17 missing; 18 present; 19, 20 missing
        assert date(2026, 5, 18) not in gaps


def test_no_gaps():
    with tempfile.TemporaryDirectory() as tmpdir:
        svc = GapDetectionService(output_root=tmpdir)
        gaps = svc.detect_gaps(date(2026, 5, 15), date(2026, 5, 20))
        assert len(gaps) == 6  # all dates missing
```

- [ ] **Step 2: Run test to verify it fails**

```powershell
pytest tests/test_gap_detection_service.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement GapDetectionService**

```python
# backend/services/gap_detection_service.py
import logging
from datetime import date, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class GapDetectionService:
    """Detect missing pesticide detection reports and support batch backfill."""

    def __init__(self, output_root: str = ""):
        self.output_root = Path(output_root) if output_root else None

    def detect_gaps(self, from_date: date, to_date: date) -> list[date]:
        """Return list of dates between from_date and to_date that lack detection reports."""
        if not self.output_root or not self.output_root.exists():
            return []

        missing = []
        current = from_date
        while current <= to_date:
            big_dir = self._report_dir(current, "big")
            if not big_dir.is_dir() or not list(big_dir.glob("*.docx")):
                missing.append(current)
            current = self._next_day(current)
        return missing

    def detect_recent_gaps(self, days: int = 7) -> list[date]:
        """Check recent N days for gaps."""
        end = date.today()
        start = end - timedelta(days=days)
        return self.detect_gaps(start, end)

    def _report_dir(self, target: date, kind: str) -> Path:
        return (self.output_root / str(target.year) /
                f"{target.month:02d}" / f"{target.day:02d}" / kind)

    def _next_day(self, d: date) -> date:
        return d + timedelta(days=1)
```

- [ ] **Step 4: Run test to verify it passes**

```powershell
pytest tests/test_gap_detection_service.py -v
```
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/gap_detection_service.py tests/test_gap_detection_service.py
git commit -m "feat: add GapDetectionService for missing report detection"
```

---

### Task 10: Create Smart Detection API routes

**Files:**
- Create: `backend/api/routes/smart_detection.py`
- Modify: `backend/models/schemas.py` (add request/response models)
- Modify: `backend/main.py` (register router)

- [ ] **Step 1: Add schemas to backend/models/schemas.py**

Insert at end of file:

```python
# ==================== Smart Detection ====================

from pydantic import BaseModel, Field
from datetime import date as date_type
from typing import Optional


class SmartRecommendResponse(BaseModel):
    today_intake: list[dict] = []
    yesterday_inventory: list[dict] = []
    missing_dates: list[str] = []


class SmartExecuteRequest(BaseModel):
    selected_varieties: list[str] = Field(default_factory=list)
    date: str = ""
    big_template: str = ""
    small_template: str = ""
    output_dir: str = ""
    inspector_name: str = "检测员"
    manual_additions: list[str] = Field(default_factory=list)
    export_format: str = "docx"  # docx, pdf, both


class SmartExecuteResponse(BaseModel):
    success: bool = False
    error: Optional[str] = None
    output_paths: dict = Field(default_factory=dict)
    pdf_files: list[str] = Field(default_factory=list)
    low_stock_alerts: list[dict] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)


class BackfillRequest(BaseModel):
    start_date: str
    end_date: str
    inspector_name: str = "检测员"


class BackfillResponse(BaseModel):
    success: bool = False
    results: list[dict] = Field(default_factory=list)


class GapResponse(BaseModel):
    missing_dates: list[str] = Field(default_factory=list)
    last_detection_date: Optional[str] = None
    total_missing: int = 0
```

- [ ] **Step 2: Create routes**

```python
# backend/api/routes/smart_detection.py
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from backend.auth.dependencies import require_permission
from backend.models.schemas import (
    SmartRecommendResponse, SmartExecuteRequest, SmartExecuteResponse,
    BackfillRequest, BackfillResponse, GapResponse,
)
from backend.services.smart_detection_service import SmartDetectionService
from backend.services.gap_detection_service import GapDetectionService
from backend.services.config_service import get_config

router = APIRouter()
detection_service = SmartDetectionService()


def _get_gap_service() -> GapDetectionService:
    cfg = get_config()
    return GapDetectionService(output_root=cfg.get("output_dir", ""))


@router.get("/smart/recommend", response_model=SmartRecommendResponse,
            dependencies=[Depends(require_permission("pesticide:view"))])
async def smart_recommend(target_date: str | None = None):
    if target_date:
        try:
            dt = date.fromisoformat(target_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format, use YYYY-MM-DD")
    else:
        dt = date.today()

    result = detection_service.recommend(dt)
    return SmartRecommendResponse(**result)


@router.post("/smart/execute", response_model=SmartExecuteResponse,
             dependencies=[Depends(require_permission("pesticide:execute"))])
async def smart_execute(req: SmartExecuteRequest):
    result = detection_service.execute(req.model_dump())
    return SmartExecuteResponse(**result)


@router.get("/smart/gaps", response_model=GapResponse,
            dependencies=[Depends(require_permission("pesticide:view"))])
async def smart_gaps(days: int = 7):
    gap_svc = _get_gap_service()
    missing = gap_svc.detect_recent_gaps(days=days)
    return GapResponse(
        missing_dates=[d.isoformat() for d in missing],
        last_detection_date=None,
        total_missing=len(missing),
    )


@router.post("/smart/backfill", response_model=BackfillResponse,
             dependencies=[Depends(require_permission("pesticide:execute"))])
async def smart_backfill(req: BackfillRequest):
    try:
        start = date.fromisoformat(req.start_date)
        end = date.fromisoformat(req.end_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format, use YYYY-MM-DD")

    gap_svc = _get_gap_service()
    missing = gap_svc.detect_gaps(start, end)

    results = []
    from backend.services.pesticide_service import PesticideService

    try:
        from backend.services.template_library_service import get_pesticide_template_path
        big_template = str(get_pesticide_template_path("big"))
        small_template = str(get_pesticide_template_path("small"))
    except FileNotFoundError:
        return BackfillResponse(success=False, results=[{"error": "模板未设置"}])

    cfg = get_config()
    output_dir = cfg.get("output_dir", "")

    for d in missing:
        try:
            date_str = d.isoformat()
            # Use smart detection service for each day
            result = detection_service.execute({
                "selected_varieties": [],
                "date": date_str,
                "big_template": big_template,
                "small_template": small_template,
                "output_dir": output_dir,
                "inspector_name": req.inspector_name,
            })
            results.append({
                "date": date_str,
                "success": result.get("success", False),
                "error": result.get("error"),
            })
        except Exception as e:
            results.append({"date": d.isoformat(), "success": False, "error": str(e)})

    return BackfillResponse(success=True, results=results)
```

- [ ] **Step 3: Register router in backend/main.py**

Find the section where other routers are included and add:

```python
from backend.api.routes import smart_detection
# ... existing routers ...
app.include_router(smart_detection.router, prefix="/api/pesticide", tags=["农残检测-智能"])
```

- [ ] **Step 4: Test endpoint is registered**

```powershell
python -c "from backend.main import app; routes = [r.path for r in app.routes]; print('/api/pesticide/smart/recommend' in routes)"
```
Expected: True

- [ ] **Step 5: Commit**

```bash
git add backend/api/routes/smart_detection.py backend/models/schemas.py backend/main.py
git commit -m "feat: add smart detection API routes (recommend/execute/gaps/backfill)"
```

---

### Task 11: Add inspector/operator roles to auth_seed

**Files:**
- Modify: `app/db/auth_seed.py:14-56`

- [ ] **Step 1: Add inspector and operator roles**

In `DEFAULT_ROLES`, after the `member` entry:

```python
    {
        "code": "inspector",
        "name": "检测员",
        "description": "可执行农残检测并生成报告",
    },
    {
        "code": "operator",
        "name": "操作员",
        "description": "可录入每日点货数据，查看库存",
    },
```

- [ ] **Step 2: Add role-permission mappings**

After the existing `DEFAULT_ROLE_PERMISSIONS` section (around line 100+), add:

```python
# inspector permissions
ROLE_PERMISSIONS = {
    "super_admin": ["*"],
    "admin": [
        "dashboard:view", "device:view", "device:rename", "device:revoke",
        "permission_request:view", "permission_request:approve",
        "user:view", "role:view",
    ],
    "inspector": [
        "dashboard:view",
        "pesticide:view", "pesticide:execute",
        "daily_check:view",
        "inventory:view",
    ],
    "operator": [
        "dashboard:view",
        "daily_check:view", "daily_check:create", "daily_check:update",
        "inventory:view",
    ],
    "member": [
        "dashboard:view", "device:view", "device:rename", "device:revoke",
        "permission_request:create",
    ],
}
```

- [ ] **Step 3: Verify seed script still valid**

```powershell
python -c "from app.db.auth_seed import DEFAULT_ROLES; print(len(DEFAULT_ROLES))"
```
Expected: 5 (super_admin, admin, member, inspector, operator)

- [ ] **Step 4: Commit**

```bash
git add app/db/auth_seed.py
git commit -m "feat: add inspector and operator roles to auth seed"
```

---

### Task 12: Inspector identity binding

**Files:**
- Modify: `backend/services/auth_service.py`
- Create: `backend/services/inspector_binding.py`

- [ ] **Step 1: Create inspector identity helper**

```python
# backend/services/inspector_binding.py
"""Bind inspector_name to authenticated user identity for report traceability."""

from backend.services.auth_service import get_current_user_optional
from backend.services.config_service import get_config


def get_inspector_name() -> str:
    """Get inspector name — prefers logged-in user's display_name, falls back to config."""
    user = get_current_user_optional()
    if user and hasattr(user, "display_name") and user.display_name:
        return user.display_name

    cfg = get_config()
    return cfg.get("inspector_name", "检测员")


def get_inspector_user_id() -> str | None:
    """Get the user_id of the current inspector for audit logging."""
    user = get_current_user_optional()
    if user and hasattr(user, "id"):
        return str(user.id)
    return None
```

- [ ] **Step 2: Update SmartDetectionService to use inspector binding**

In `backend/services/smart_detection_service.py`, modify the `execute` method's `inspector_name` resolution:

```python
# Replace direct inspector_name usage with:
inspector_name = request.get("inspector_name", "检测员")
# If not explicitly provided in request, try auth binding
if not request.get("inspector_name") or request.get("inspector_name") == "检测员":
    try:
        from backend.services.inspector_binding import get_inspector_name
        inspector_name = get_inspector_name()
    except ImportError:
        pass
```

- [ ] **Step 3: Verify import works**

```powershell
python -c "from backend.services.inspector_binding import get_inspector_name; print(get_inspector_name())"
```
Expected: prints "朱林初" (or default config value)

- [ ] **Step 4: Commit**

```bash
git add backend/services/inspector_binding.py backend/services/smart_detection_service.py
git commit -m "feat: bind inspector identity to authenticated user display_name"
```

---

### Task 13: Template version management

**Files:**
- Modify: `backend/services/template_library_service.py`

- [ ] **Step 1: Add version control to template save**

In `backend/services/template_library_service.py`, modify `save_pesticide_template`:

```python
def _archive_previous_version(target_path: Path, target_dir: Path, kind: str) -> None:
    """Archive the previous version of a template before overwriting."""
    if not target_path.exists():
        return

    from datetime import date
    version_suffix = date.today().strftime("%Y-%m-%d")
    stem = target_path.stem
    suffix = target_path.suffix
    archived = target_dir / f"{stem}.{version_suffix}{suffix}"
    shutil.copy2(target_path, archived)

    # Update versions.json
    versions_path = target_dir / "versions.json"
    versions = {}
    if versions_path.exists():
        try:
            import json
            with versions_path.open("r", encoding="utf-8") as f:
                versions = json.load(f)
        except Exception:
            pass

    key = f"pesticide_{kind}"
    if key not in versions:
        versions[key] = []

    versions[key].append({
        "version": len(versions[key]) + 1,
        "date": version_suffix,
        "file": archived.name,
    })

    with versions_path.open("w", encoding="utf-8") as f:
        json.dump(versions, f, ensure_ascii=False, indent=2)
```

Modify `save_pesticide_template` to call `_archive_previous_version` before copying:

```python
def save_pesticide_template(kind: str, source_path: Path, original_name: str | None = None) -> dict:
    if kind not in {"big", "small"}:
        raise ValueError("模板类型只能是 big 或 small")

    target_dir = _template_root() / "pesticide"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_name = f"{kind}-template{_safe_suffix(original_name)}"
    target_path = target_dir / target_name

    # Archive previous version before overwriting
    _archive_previous_version(target_path, target_dir, kind)

    shutil.copy2(source_path, target_path)

    cfg = get_config()
    templates = dict(cfg.get("pesticide_templates") or {})
    templates[kind] = {
        "path": str(target_path),
        "filename": original_name or target_name,
        "updated_at": _now_text(),
    }
    update_config({"pesticide_templates": templates})
    return get_pesticide_templates()
```

- [ ] **Step 2: Add version list and rollback functions**

```python
def get_pesticide_template_versions(kind: str) -> list[dict]:
    versions_path = _template_root() / "pesticide" / "versions.json"
    if not versions_path.exists():
        return []
    import json
    try:
        with versions_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get(f"pesticide_{kind}", [])
    except Exception:
        return []


def rollback_pesticide_template(kind: str, version_date: str) -> dict:
    target_dir = _template_root() / "pesticide"
    target_name = f"{kind}-template.docx"
    target_path = target_dir / target_name

    archived_name = f"{kind}-template.{version_date}.docx"
    archived_path = target_dir / archived_name

    if not archived_path.exists():
        raise FileNotFoundError(f"版本不存在: {version_date}")

    # Archive current before rollback
    _archive_previous_version(target_path, target_dir, kind)

    shutil.copy2(archived_path, target_path)

    cfg = get_config()
    templates = dict(cfg.get("pesticide_templates") or {})
    templates[kind] = {
        "path": str(target_path),
        "filename": target_name,
        "updated_at": _now_text(),
    }
    update_config({"pesticide_templates": templates})
    return get_pesticide_templates()


def delete_pesticide_template_version(kind: str, version_date: str) -> bool:
    target_dir = _template_root() / "pesticide"
    archived_name = f"{kind}-template.{version_date}.docx"
    archived_path = target_dir / archived_name

    if not archived_path.exists():
        return False
    archived_path.unlink()

    # Update versions.json
    versions_path = target_dir / "versions.json"
    if versions_path.exists():
        import json
        try:
            with versions_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            key = f"pesticide_{kind}"
            if key in data:
                data[key] = [v for v in data[key] if v.get("date") != version_date]
            with versions_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    return True
```

- [ ] **Step 3: Add API endpoints for version management**

In `backend/api/routes/pesticide.py`, add:

```python
from backend.services.template_library_service import (
    get_pesticide_template_versions, rollback_pesticide_template,
    delete_pesticide_template_version
)


@router.get("/templates/{kind}/versions",
            dependencies=[Depends(require_permission("pesticide:view"))])
async def list_template_versions(kind: str):
    kind = kind.strip().lower()
    if kind not in {"big", "small"}:
        raise HTTPException(status_code=400, detail="模板类型只能是 big 或 small")
    return {"kind": kind, "versions": get_pesticide_template_versions(kind)}


@router.post("/templates/{kind}/rollback",
             dependencies=[Depends(require_permission("pesticide:execute"))])
async def rollback_template(kind: str, version_date: str = Form(...)):
    kind = kind.strip().lower()
    try:
        result = rollback_pesticide_template(kind, version_date)
        return {"success": True, "templates": result}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/templates/{kind}/versions/{version_date}",
               dependencies=[Depends(require_permission("pesticide:execute"))])
async def delete_template_version(kind: str, version_date: str):
    kind = kind.strip().lower()
    ok = delete_pesticide_template_version(kind, version_date)
    if not ok:
        raise HTTPException(status_code=404, detail="版本不存在")
    return {"success": True}
```

- [ ] **Step 4: Test version management**

```powershell
python -c "from backend.services.template_library_service import get_pesticide_template_versions; print(get_pesticide_template_versions('big'))"
```
Expected: prints version list or empty list

- [ ] **Step 5: Commit**

```bash
git add backend/services/template_library_service.py backend/api/routes/pesticide.py
git commit -m "feat: add template version management (archive/rollback/delete)"
```

---

### Task 14: Batch import endpoint for daily intake

**Files:**
- Modify: `backend/api/routes/daily_intake.py`

- [ ] **Step 1: Add batch import endpoint**

Add to `backend/api/routes/daily_intake.py`:

```python
import csv
import io
import openpyxl


@router.post("/import",
             dependencies=[Depends(require_permission("daily_check:create"))])
async def import_daily_intake(
    file: UploadFile = File(...),
    date: str = Form(...),
):
    """Batch import daily intake from CSV or Excel file."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="没有选择文件")

    ext = Path(file.filename).suffix.lower()
    rows = []

    try:
        content = await file.read()
        if ext == ".csv":
            text = content.decode("utf-8-sig")
            reader = csv.reader(io.StringIO(text))
            for row in reader:
                if len(row) >= 2:
                    rows.append({
                        "name": row[0].strip(),
                        "quantity": row[1].strip(),
                        "unit": row[2].strip() if len(row) > 2 else "斤",
                        "category": row[3].strip() if len(row) > 3 else "",
                    })
        elif ext in (".xlsx", ".xls"):
            wb = openpyxl.load_workbook(io.BytesIO(content))
            ws = wb.active
            for row in ws.iter_rows(min_row=2, values_only=True):  # skip header
                if row and len(row) >= 2 and row[0] and row[1]:
                    rows.append({
                        "name": str(row[0]).strip(),
                        "quantity": str(row[1]).strip(),
                        "unit": str(row[2]).strip() if len(row) > 2 else "斤",
                        "category": str(row[3]).strip() if len(row) > 3 else "",
                    })
        else:
            raise HTTPException(status_code=400, detail="不支持的文件格式，请上传 .csv 或 .xlsx")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件解析失败: {e}")

    if not rows:
        raise HTTPException(status_code=400, detail="文件中没有有效数据")

    results = []
    errors = []
    for row in rows:
        try:
            item = await run_in_threadpool(
                service.add_item,
                date=date,
                name=row["name"],
                quantity=float(row["quantity"]),
                unit=row["unit"],
                category=row.get("category", ""),
            )
            results.append(item)
        except Exception as e:
            errors.append({"row": row, "error": str(e)})

    return {
        "success": True,
        "imported": len(results),
        "errors": len(errors),
        "error_details": errors[:10],  # limit error details
    }
```

Ensure imports added at top:
```python
import csv
import io
from pathlib import Path
```

- [ ] **Step 2: Verify route is registered**

```powershell
python -c "from backend.main import app; routes = [r.path for r in app.routes]; print('/api/daily-intake/import' in routes)"
```
Expected: True

- [ ] **Step 3: Commit**

```bash
git add backend/api/routes/daily_intake.py
git commit -m "feat: add batch import endpoint for daily intake CSV/Excel"
```

---

### Task 15: Create frontend useSmartDetection composable

**Files:**
- Create: `frontend/src/features/smart-detection/composables/useSmartDetection.ts`
- Create: `frontend/src/api/smart-detection.ts`

- [ ] **Step 1: Create API client**

```typescript
// frontend/src/api/smart-detection.ts
import api from './authInterceptors'

export interface SmartRecommendItem {
  name: string
  source: 'daily_intake' | 'yesterday_inventory'
  category?: string
  reason?: string
}

export interface SmartRecommendResponse {
  today_intake: SmartRecommendItem[]
  yesterday_inventory: SmartRecommendItem[]
  missing_dates: string[]
}

export interface SmartExecuteRequest {
  selected_varieties: string[]
  date: string
  big_template: string
  small_template: string
  output_dir: string
  inspector_name: string
  manual_additions: string[]
  export_format: 'docx' | 'pdf' | 'both'
}

export interface SmartExecuteResponse {
  success: boolean
  error?: string
  output_paths: Record<string, unknown>
  pdf_files: string[]
  low_stock_alerts: Array<{ item_name: string; balance: number; unit: string }>
  summary: { total_varieties: number; generated_date: string; inspector: string }
}

export interface GapResponse {
  missing_dates: string[]
  last_detection_date: string | null
  total_missing: number
}

export interface BackfillRequest {
  start_date: string
  end_date: string
  inspector_name: string
}

export interface BackfillResponse {
  success: boolean
  results: Array<{ date: string; success: boolean; error?: string }>
}

export async function getSmartRecommend(date?: string): Promise<SmartRecommendResponse> {
  const params = date ? `?target_date=${date}` : ''
  const { data } = await api.get(`/api/pesticide/smart/recommend${params}`)
  return data
}

export async function postSmartExecute(req: SmartExecuteRequest): Promise<SmartExecuteResponse> {
  const { data } = await api.post('/api/pesticide/smart/execute', req)
  return data
}

export async function getSmartGaps(days = 7): Promise<GapResponse> {
  const { data } = await api.get(`/api/pesticide/smart/gaps?days=${days}`)
  return data
}

export async function postSmartBackfill(req: BackfillRequest): Promise<BackfillResponse> {
  const { data } = await api.post('/api/pesticide/smart/backfill', req)
  return data
}
```

- [ ] **Step 2: Create useSmartDetection composable**

```typescript
// frontend/src/features/smart-detection/composables/useSmartDetection.ts
import { ref, computed } from 'vue'
import {
  getSmartRecommend,
  postSmartExecute,
  type SmartRecommendItem,
  type SmartExecuteRequest,
  type SmartExecuteResponse,
} from '@/api/smart-detection'

export function useSmartDetection() {
  const todayIntakeItems = ref<SmartRecommendItem[]>([])
  const yesterdayInventoryItems = ref<SmartRecommendItem[]>([])
  const manualAdditions = ref<string[]>([])
  const missingDates = ref<string[]>([])

  const selectedToday = ref<Set<string>>(new Set())
  const selectedYesterday = ref<Set<string>>(new Set())

  const loading = ref(false)
  const executing = ref(false)
  const lastResult = ref<SmartExecuteResponse | null>(null)

  const allSelected = computed(() =>
    [...selectedToday.value, ...selectedYesterday.value, ...manualAdditions.value]
  )

  const totalRecommended = computed(() =>
    todayIntakeItems.value.length + yesterdayInventoryItems.value.length
  )

  const selectedCount = computed(() =>
    selectedToday.value.size + selectedYesterday.value.size + manualAdditions.value.length
  )

  const error = ref<string | null>(null)

  async function loadRecommendations(date?: string) {
    loading.value = true
    error.value = null
    try {
      const result = await getSmartRecommend(date)
      todayIntakeItems.value = result.today_intake
      yesterdayInventoryItems.value = result.yesterday_inventory
      missingDates.value = result.missing_dates

      // Auto-select all
      selectedToday.value = new Set(result.today_intake.map(i => i.name))
      selectedYesterday.value = new Set(result.yesterday_inventory.map(i => i.name))
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '加载推荐清单失败'
    } finally {
      loading.value = false
    }
  }

  function toggleToday(name: string) {
    const s = new Set(selectedToday.value)
    if (s.has(name)) s.delete(name)
    else s.add(name)
    selectedToday.value = s
  }

  function toggleYesterday(name: string) {
    const s = new Set(selectedYesterday.value)
    if (s.has(name)) s.delete(name)
    else s.add(name)
    selectedYesterday.value = s
  }

  function selectAllToday() {
    selectedToday.value = new Set(todayIntakeItems.value.map(i => i.name))
  }

  function deselectAllToday() {
    selectedToday.value = new Set()
  }

  function selectAllYesterday() {
    selectedYesterday.value = new Set(yesterdayInventoryItems.value.map(i => i.name))
  }

  function deselectAllYesterday() {
    selectedYesterday.value = new Set()
  }

  function addManual(name: string) {
    if (name && !manualAdditions.value.includes(name)) {
      manualAdditions.value.push(name)
    }
  }

  function removeManual(index: number) {
    manualAdditions.value.splice(index, 1)
  }

  async function execute(options: Omit<SmartExecuteRequest, 'selected_varieties' | 'manual_additions'>) {
    executing.value = true
    error.value = null
    try {
      const result = await postSmartExecute({
        ...options,
        selected_varieties: [...selectedToday.value, ...selectedYesterday.value],
        manual_additions: manualAdditions.value,
      })
      lastResult.value = result
      return result
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '执行检测失败'
      return null
    } finally {
      executing.value = false
    }
  }

  function reset() {
    todayIntakeItems.value = []
    yesterdayInventoryItems.value = []
    manualAdditions.value = []
    selectedToday.value = new Set()
    selectedYesterday.value = new Set()
    lastResult.value = null
    error.value = null
  }

  return {
    todayIntakeItems,
    yesterdayInventoryItems,
    manualAdditions,
    missingDates,
    selectedToday,
    selectedYesterday,
    loading,
    executing,
    lastResult,
    error,
    allSelected,
    totalRecommended,
    selectedCount,
    loadRecommendations,
    toggleToday,
    toggleYesterday,
    selectAllToday,
    deselectAllToday,
    selectAllYesterday,
    deselectAllYesterday,
    addManual,
    removeManual,
    execute,
    reset,
  }
}
```

- [ ] **Step 3: Create useGapDetection composable**

```typescript
// frontend/src/features/smart-detection/composables/useGapDetection.ts
import { ref } from 'vue'
import { getSmartGaps, postSmartBackfill, type GapResponse, type BackfillResponse } from '@/api/smart-detection'

export function useGapDetection() {
  const gaps = ref<GapResponse | null>(null)
  const loading = ref(false)
  const backfilling = ref(false)
  const backfillResult = ref<BackfillResponse | null>(null)
  const error = ref<string | null>(null)

  async function checkGaps(days = 7) {
    loading.value = true
    error.value = null
    try {
      gaps.value = await getSmartGaps(days)
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '检查遗漏失败'
    } finally {
      loading.value = false
    }
  }

  async function backfill(startDate: string, endDate: string, inspectorName: string) {
    backfilling.value = true
    error.value = null
    try {
      backfillResult.value = await postSmartBackfill({
        start_date: startDate,
        end_date: endDate,
        inspector_name: inspectorName,
      })
      return backfillResult.value
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '补做失败'
      return null
    } finally {
      backfilling.value = false
    }
  }

  return { gaps, loading, backfilling, backfillResult, error, checkGaps, backfill }
}
```

- [ ] **Step 4: Verify TypeScript compilation**

```powershell
Set-Location frontend; npx vue-tsc --noEmit 2>&1 | Select-Object -First 20
```
Expected: no new errors from the composable files

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/smart-detection.ts frontend/src/features/smart-detection/composables/useSmartDetection.ts frontend/src/features/smart-detection/composables/useGapDetection.ts
git commit -m "feat: add smart detection and gap detection composables"
```

---

### Task 16: Create SmartDetection.vue page

**Files:**
- Create: `frontend/src/views/SmartDetection.vue`
- Modify: `frontend/src/router/index.ts`

- [ ] **Step 1: Create SmartDetection.vue**

```vue
<template>
  <div class="smart-detection">
    <el-card class="header-card">
      <div class="header-row">
        <h2>🧪 智能检测工作台</h2>
        <span class="inspector">检查员: {{ inspectorName }}</span>
      </div>
      <el-radio-group v-model="dataSource" class="source-switch">
        <el-radio-button value="auto">自动推荐</el-radio-button>
        <el-radio-button value="manual">完全手动</el-radio-button>
      </el-radio-group>
    </el-card>

    <!-- Gap Alert -->
    <el-alert v-if="gaps && gaps.total_missing > 0" type="warning" :closable="false" show-icon>
      <template #title>
        ⚠ 发现 {{ gaps.total_missing }} 天遗漏检测:
        {{ gaps.missing_dates.slice(0, 3).join(', ') }}{{ gaps.missing_dates.length > 3 ? '...' : '' }}
        <el-button type="warning" size="small" @click="showBackfillDialog">批量补做</el-button>
      </template>
    </el-alert>

    <!-- Loading -->
    <el-skeleton v-if="loading" :rows="6" animated />

    <!-- Three-panel layout -->
    <div v-else class="panels" :class="{ 'manual-mode': dataSource === 'manual' }">
      <!-- Panel 1: Today's intake -->
      <div v-if="dataSource === 'auto'" class="panel">
        <div class="panel-header">
          <span>今日进货需检 ({{ todayIntakeItems.length }} 种)</span>
          <div class="panel-actions">
            <el-button size="small" text @click="selectAllToday">全选</el-button>
            <el-button size="small" text @click="deselectAllToday">反选</el-button>
          </div>
        </div>
        <el-checkbox-group :model-value="[...selectedToday]" class="veg-list">
          <el-checkbox
            v-for="item in todayIntakeItems"
            :key="item.name"
            :value="item.name"
            @change="toggleToday(item.name)"
          >
            {{ item.name }}
          </el-checkbox>
        </el-checkbox-group>
        <div v-if="todayIntakeItems.length === 0" class="empty-hint">暂无今日点货数据</div>
      </div>

      <!-- Panel 2: Yesterday's untested -->
      <div v-if="dataSource === 'auto'" class="panel">
        <div class="panel-header">
          <span>昨日库存未检 ({{ yesterdayInventoryItems.length }} 种)</span>
          <div class="panel-actions">
            <el-button size="small" text @click="selectAllYesterday">全选</el-button>
            <el-button size="small" text @click="deselectAllYesterday">反选</el-button>
          </div>
        </div>
        <el-checkbox-group :model-value="[...selectedYesterday]" class="veg-list">
          <el-checkbox
            v-for="item in yesterdayInventoryItems"
            :key="item.name"
            :value="item.name"
            @change="toggleYesterday(item.name)"
          >
            {{ item.name }}
            <el-tag size="small" type="warning">未检</el-tag>
          </el-checkbox>
        </el-checkbox-group>
        <div v-if="yesterdayInventoryItems.length === 0" class="empty-hint">昨日均已检测</div>
      </div>

      <!-- Panel 3: Manual additions -->
      <div class="panel manual-panel">
        <div class="panel-header">
          <span>手动补充 ({{ manualAdditions.length }} 种)</span>
        </div>
        <div class="manual-input">
          <el-input v-model="newVegName" placeholder="输入蔬菜名称" size="small" @keyup.enter="addManualVeg">
            <template #append>
              <el-button @click="addManualVeg">添加</el-button>
            </template>
          </el-input>
        </div>
        <el-tag
          v-for="(name, idx) in manualAdditions"
          :key="idx"
          closable
          class="manual-tag"
          @close="removeManual(idx)"
        >
          {{ name }}
        </el-tag>
      </div>
    </div>

    <!-- Action Bar -->
    <div v-if="!loading" class="action-bar">
      <div class="action-info">
        <span>检测日期: <strong>{{ detectionDate }}</strong></span>
        <span>已选 <strong>{{ selectedCount }}</strong> 种蔬菜</span>
        <span>模板: 自动匹配</span>
      </div>
      <div class="action-buttons">
        <el-button type="primary" size="large" :loading="executing" @click="runDetection">
          一键生成报告
        </el-button>
        <el-button size="large" :loading="executing" @click="runDetectionWithPdf">
          生成并导出 PDF
        </el-button>
      </div>
    </div>

    <!-- Result -->
    <el-card v-if="lastResult" class="result-card">
      <template #header>检测结果</template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="状态">
          <el-tag :type="lastResult.success ? 'success' : 'danger'">
            {{ lastResult.success ? '成功' : '失败' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="检测日期">{{ detectionDate }}</el-descriptions-item>
        <el-descriptions-item label="蔬菜数量">{{ lastResult.summary?.total_varieties || 0 }} 种</el-descriptions-item>
        <el-descriptions-item label="检测员">{{ lastResult.summary?.inspector || inspectorName }}</el-descriptions-item>
      </el-descriptions>

      <!-- Low stock alerts -->
      <el-alert
        v-if="lastResult.low_stock_alerts && lastResult.low_stock_alerts.length > 0"
        type="warning"
        :closable="false"
        show-icon
        style="margin-top: 12px"
      >
        <template #title>
          库存低量提醒:
          <el-tag
            v-for="a in lastResult.low_stock_alerts"
            :key="a.item_name"
            size="small"
            type="warning"
            style="margin-left: 4px"
          >
            {{ a.item_name }} ({{ a.balance }}{{ a.unit }})
          </el-tag>
        </template>
      </el-alert>
    </el-card>

    <!-- Error -->
    <el-alert v-if="smartError" :title="smartError" type="error" show-icon />

    <!-- Backfill Dialog -->
    <el-dialog v-model="backfillDialogVisible" title="批量补做遗漏检测" width="500px">
      <el-form label-width="100px">
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="backfillDateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="backfillDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="backfilling" @click="runBackfill">开始补做</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useSmartDetection } from '@/features/smart-detection/composables/useSmartDetection'
import { useGapDetection } from '@/features/smart-detection/composables/useGapDetection'
import { useAuth } from '@/composables/useAuth'

const { user } = useAuth()
const inspectorName = ref(user.value?.display_name || '检测员')

const dataSource = ref<'auto' | 'manual'>('auto')
const detectionDate = ref(new Date().toISOString().split('T')[0])
const newVegName = ref('')

const {
  todayIntakeItems, yesterdayInventoryItems, manualAdditions,
  selectedToday, selectedYesterday,
  loading, executing, lastResult,
  selectedCount, error: smartError,
  loadRecommendations, toggleToday, toggleYesterday,
  selectAllToday, deselectAllToday, selectAllYesterday, deselectAllYesterday,
  addManual, removeManual, execute,
} = useSmartDetection()

const { gaps, backfilling, checkGaps, backfill } = useGapDetection()

const backfillDialogVisible = ref(false)
const backfillDateRange = ref<[string, string] | null>(null)

function addManualVeg() {
  if (newVegName.value.trim()) {
    addManual(newVegName.value.trim())
    newVegName.value = ''
  }
}

async function runDetection() {
  await execute({ date: detectionDate.value, big_template: '', small_template: '',
    output_dir: '', inspector_name: inspectorName.value, export_format: 'docx' })
}

async function runDetectionWithPdf() {
  await execute({ date: detectionDate.value, big_template: '', small_template: '',
    output_dir: '', inspector_name: inspectorName.value, export_format: 'both' })
}

function showBackfillDialog() {
  backfillDateRange.value = null
  backfillDialogVisible.value = true
}

async function runBackfill() {
  if (!backfillDateRange.value) {
    ElMessage.warning('请选择日期范围')
    return
  }
  await backfill(backfillDateRange.value[0], backfillDateRange.value[1], inspectorName.value)
  backfillDialogVisible.value = false
  ElMessage.success('补做完成')
}

onMounted(() => {
  loadRecommendations(detectionDate.value)
  checkGaps(7)
})
</script>

<style scoped>
.smart-detection { padding: 16px; max-width: 1400px; margin: 0 auto; }
.header-card { margin-bottom: 12px; }
.header-row { display: flex; justify-content: space-between; align-items: center; }
.header-row h2 { margin: 0; font-size: 20px; }
.inspector { color: #909399; font-size: 14px; }
.source-switch { margin-top: 8px; }

.panels { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin: 16px 0; }
.panels.manual-mode { grid-template-columns: 1fr; }
.panel { background: #fff; border: 1px solid #ebeef5; border-radius: 8px; padding: 12px; }
.panel-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; font-weight: 600; }
.panel-actions { display: flex; gap: 4px; }
.veg-list { display: flex; flex-direction: column; gap: 6px; max-height: 400px; overflow-y: auto; }
.empty-hint { color: #c0c4cc; font-size: 13px; text-align: center; padding: 20px 0; }
.manual-input { margin-bottom: 8px; }
.manual-tag { margin: 2px; }

.action-bar { display: flex; justify-content: space-between; align-items: center; padding: 16px; background: #fff; border-radius: 8px; border: 1px solid #ebeef5; margin: 12px 0; }
.action-info { display: flex; gap: 20px; color: #606266; }
.action-buttons { display: flex; gap: 8px; }

.result-card { margin-top: 16px; }
</style>
```

- [ ] **Step 2: Add route**

In `frontend/src/router/index.ts`, add:

```typescript
{
  path: '/smart-detection',
  name: 'SmartDetection',
  component: () => import('@/views/SmartDetection.vue'),
  meta: { title: '智能检测工作台', permission: 'pesticide:view' },
},
```

- [ ] **Step 3: Verify frontend compiles**

```powershell
Set-Location frontend; npx vue-tsc --noEmit 2>&1 | Select-Object -First 20
```
Expected: no new errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/SmartDetection.vue frontend/src/router/index.ts
git commit -m "feat: add SmartDetection.vue page with three-panel layout"
```

---

### Task 17: Final integration — wire everything together

**Files:**
- Modify: `backend/main.py` (ensure all imports)
- Verify: `start.bat` integration test

- [ ] **Step 1: Verify backend main.py has all router registrations**

Ensure `backend/main.py` includes:
```python
from backend.api.routes import pesticide
from backend.api.routes import smart_detection
from backend.api.routes import daily_intake

app.include_router(pesticide.router, prefix="/api/pesticide", tags=["农残检测"])
app.include_router(smart_detection.router, prefix="/api/pesticide", tags=["农残检测-智能"])
app.include_router(daily_intake.router, prefix="/api/daily-intake", tags=["每日点货"])
```

- [ ] **Step 2: Test the full startup flow**

```powershell
# Test migration check first
python scripts/migrate.py check

# Test backend starts
python -c "from backend.main import app; print('Backend OK, routes:', len(app.routes))"
```

Expected: Backend imports succeed, prints route count > 0

- [ ] **Step 3: Commit**

```bash
git add backend/main.py
git commit -m "feat: wire all smart detection routes into backend main"
```

---

### Task 18: Run full verification

**Files:** none (verification only)

- [ ] **Step 1: Run all backend tests**

```powershell
pytest tests/test_smart_template_matcher.py tests/test_low_stock_notifier.py tests/test_output_archiver.py tests/test_export_service.py tests/test_smart_detection_service.py tests/test_gap_detection_service.py -v
```

Expected: all PASS

- [ ] **Step 2: Verify migration CLI works**

```powershell
python scripts/migrate.py status
```

Expected: prints migration status without errors

- [ ] **Step 3: Verify config loading**

```powershell
python -c "from app.models.config_model import load_config; c = load_config(); print('inspector:', c.get('inspector_name'))"
```

Expected: prints inspector name

- [ ] **Step 4: Commit final verification**

```bash
git add . && git commit -m "test: verification of all smart workbench components"
```
