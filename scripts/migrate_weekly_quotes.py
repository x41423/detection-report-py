#!/usr/bin/env python
"""从 config/app.json 导入旧的每周报价记录到数据库"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.store import init_database
from app.db.weekly_quote_repository import WeeklyQuoteRepository


def main():
    init_database()
    repo = WeeklyQuoteRepository()

    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "app.json")
    if not os.path.exists(config_path):
        print(f"[ERROR] Config file not found: {config_path}")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    records = config.get("weekly_quote_summary_records", {})
    if not records:
        print("[INFO] No weekly_quote_summary_records found in config/app.json")
        return

    total_imported = 0
    total_skipped = 0

    for supplier, dates in records.items():
        for date_str, record in dates.items():
            entries = record.get("entries", []) if isinstance(record, dict) else []
            valid_entries = []
            for e in entries:
                name = (e.get("name") or "").strip()
                price = e.get("price")
                if not name or price is None:
                    total_skipped += 1
                    continue
                valid_entries.append({
                    "name": name,
                    "unit": e.get("unit", "斤"),
                    "price": float(price),
                })

            if not valid_entries:
                continue

            try:
                repo.save_batch(
                    supplier=supplier,
                    quote_date=date_str,
                    entries=valid_entries,
                    source_label="历史数据导入",
                )
                total_imported += len(valid_entries)
                print(f"  {supplier} {date_str}: {len(valid_entries)} 条")
            except Exception as exc:
                print(f"  [ERROR] {supplier} {date_str}: {exc}")

    print(f"\n总计导入 {total_imported} 条记录，跳过 {total_skipped} 条空记录")

    for supplier in sorted(records.keys()):
        batches = repo.list_batches(supplier)
        entry_count = sum(b.get("entry_count", 0) for b in batches)
        print(f"  {supplier}: {len(batches)} 批次, {entry_count} 条")


if __name__ == "__main__":
    main()
