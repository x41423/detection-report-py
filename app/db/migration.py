"""数据迁移模块 - 将JSON数据迁移到SQLite数据库"""
import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, List
import app.db.store as store
from app.db.store import init_database, get_connection, query
from app.db.veg_repository import VegRepository
from app.db.unit_repository import UnitRepository
from app.db.price_repository import PriceHistoryRepository
from app.models.config_model import load_config
from shared.project_paths import get_project_paths


# 迁移版本表
MIGRATION_VERSION_TABLE = """
CREATE TABLE IF NOT EXISTS MigrationVersion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version INTEGER NOT NULL,
    description TEXT,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


def get_current_migration_version() -> int:
    """获取当前迁移版本"""
    try:
        result = query("SELECT MAX(version) as max_version FROM MigrationVersion")
        if result and result[0]['max_version']:
            return result[0]['max_version']
    except:
        pass
    return 0


def set_migration_version(version: int, description: str = None):
    """设置迁移版本"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO MigrationVersion (version, description) VALUES (?, ?)",
            (version, description)
        )
        conn.commit()
        logging.info(f"迁移版本已更新: v{version}")
    except Exception as e:
        conn.rollback()
        logging.error(f"更新迁移版本失败: {e}")
        raise
    finally:
        cursor.close()


def migrate_json_to_db():
    """
    将JSON数据迁移到数据库
    
    迁移内容：
    1. config.json 中的 high_risk, low_risk 蔬菜列表
    2. history_rates.json 中的历史抑制率数据
    """
    logging.info("开始JSON数据迁移...")
    
    # 确保数据库已初始化
    init_database()
    
    # 创建迁移版本表
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(MIGRATION_VERSION_TABLE)
    conn.commit()
    cursor.close()
    
    current_version = get_current_migration_version()
    
    # 迁移版本1：蔬菜数据
    if current_version < 1:
        logging.info("执行迁移v1: 蔬菜数据")
        _migrate_vegetables()
        set_migration_version(1, "迁移蔬菜数据")
    
    # 迁移版本2：历史抑制率数据
    if current_version < 2:
        logging.info("执行迁移v2: 历史抑制率数据")
        _migrate_history_rates()
        set_migration_version(2, "迁移历史抑制率数据")
    
    logging.info("JSON数据迁移完成")


def _migrate_vegetables():
    """迁移蔬菜数据"""
    try:
        config = load_config()
        
        # 迁移高风险蔬菜
        high_risk = config.get("high_risk", [])
        for name in high_risk:
            if name.strip():
                VegRepository.get_or_create_vegetable(name.strip(), "high")
        
        # 迁移低风险蔬菜
        low_risk = config.get("low_risk", [])
        for name in low_risk:
            if name.strip():
                VegRepository.get_or_create_vegetable(name.strip(), "low")
        
        logging.info(f"迁移蔬菜数据完成: 高风险{len(high_risk)}个, 低风险{len(low_risk)}个")
        
    except Exception as e:
        logging.error(f"迁移蔬菜数据失败: {e}")
        raise


def _migrate_history_rates():
    """迁移历史抑制率数据"""
    try:
        paths = get_project_paths()
        history_file = paths.history_rates_file
        if not history_file.exists() and paths.legacy_history_rates_file.exists():
            history_file = paths.legacy_history_rates_file
        
        if not history_file.exists():
            logging.info("历史数据文件不存在，跳过迁移")
            return
        
        with history_file.open('r', encoding='utf-8') as f:
            history_data = json.load(f)
        
        # 创建默认单位
        default_unit = "默认"
        unit_id = UnitRepository.get_or_create_unit(default_unit, "默认单位（用于历史抑制率数据）")
        
        # 迁移各类别的历史数据
        migrated_count = 0
        for category in ["high", "low", "other"]:
            if category in history_data and history_data[category]:
                # 为每个类别创建一个代表性的蔬菜
                veg_name = f"历史数据_{category}"
                veg_id = VegRepository.get_or_create_vegetable(veg_name, category)
                
                # 添加价格记录（使用日期作为区分）
                base_date = datetime.now()
                for i, rate in enumerate(history_data[category][-50:]):  # 只迁移最近50条
                    date = base_date.strftime("%Y-%m-%d")
                    # 使用抑制率作为价格存储
                    PriceHistoryRepository.add_price(
                        vegetable_name=veg_name,
                        unit_name=default_unit,
                        price=float(rate),
                        date=date,
                        source=f"history_rates.json_{category}"
                    )
                    migrated_count += 1
        
        # 迁移品种级别历史数据
        if "variety_rates" in history_data:
            for veg_name, rate in history_data["variety_rates"].items():
                if veg_name and rate:
                    PriceHistoryRepository.add_price(
                        vegetable_name=veg_name,
                        unit_name=default_unit,
                        price=float(rate),
                        date=datetime.now().strftime("%Y-%m-%d"),
                        source="history_rates.json_variety"
                    )
                    migrated_count += 1
        
        logging.info(f"迁移历史抑制率数据完成: 共{migrated_count}条记录")
        
    except Exception as e:
        logging.error(f"迁移历史抑制率数据失败: {e}")
        raise


def backup_database():
    """备份数据库"""
    import shutil
    from datetime import datetime
    
    db_path = store.DB_PATH
    
    if not os.path.exists(db_path):
        logging.warning("数据库文件不存在，无法备份")
        return None
    
    backup_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "backups"
    )
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"app_backup_{timestamp}.db")
    
    try:
        shutil.copy2(db_path, backup_path)
        logging.info(f"数据库备份成功: {backup_path}")
        return backup_path
    except Exception as e:
        logging.error(f"数据库备份失败: {e}")
        return None


def export_to_json(output_path: str = None):
    """
    导出数据库数据到JSON文件
    
    Args:
        output_path: 输出文件路径，默认为 export_YYYYMMDD_HHMMSS.json
    """
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(get_project_paths().data_dir / f"export_{timestamp}.json")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    try:
        # 导出蔬菜数据
        vegetables = VegRepository.get_all_vegetables()
        
        # 导出单位数据
        units = UnitRepository.get_all_units()
        
        # 导出价格历史
        price_history = query("""
            SELECT ph.*, v.name as vegetable_name, u.name as unit_name
            FROM PriceHistory ph
            JOIN Veg v ON ph.vegetable_id = v.id
            JOIN Unit u ON ph.unit_id = u.id
            ORDER BY ph.date DESC
        """)
        
        export_data = {
            "export_time": datetime.now().isoformat(),
            "vegetables": vegetables,
            "units": units,
            "price_history": price_history
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        logging.info(f"数据导出成功: {output_path}")
        return output_path
        
    except Exception as e:
        logging.error(f"数据导出失败: {e}")
        raise
