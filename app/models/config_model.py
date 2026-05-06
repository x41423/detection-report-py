import copy
import json
from pathlib import Path

from app.utils.weekly_price_update import get_default_weekly_price_aliases
from shared.project_paths import get_project_paths


DEFAULT_CONFIG = {
    "output_dir": r"C:\Users\34585\Desktop\滨鲜\检测报告py文件夹",
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
        "滨鲜": "",
        "1号": "",
        "5号": "",
        "6号": "",
        "7号": "",
        "8号": "",
        "顾家": ""
    },
    "pesticide_templates": {
        "big": {},
        "small": {},
    },
    "transfer_templates": {},
    "last_used_small_type": "滨鲜",
    "ui_theme": "light_cyan.xml",
    "data_transfer_use_shared_date": True,
    "data_transfer_last_date": "",
    "data_transfer_big_folder": "",
    "dish_name_aliases": {},
    "funasr_lab_memory": {
        "recent_hotwords": [],
        "name_unit_memory": [],
    },
    "funasr_lab_daily_tracking": {
        "records": {},
    },
    "weekly_price_aliases": get_default_weekly_price_aliases(),
    "weekly_price_output_path": "",
    "weekly_quote_summary_workbook_path": "",
    "weekly_quote_summary_records": {},
    "weekly_quote_summary_unit_memory": {},
    "inventory_low_stock_threshold": 3,
}


def get_config_path() -> str:
    """返回 config.json 的绝对路径（项目根目录）。"""
    # 获取当前文件所在目录的上两级（根目录）
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


def load_config() -> dict:
    """加载配置文件，如果不存在则以默认值创建并返回。"""
    path = resolve_read_config_path()
    canonical_path = Path(get_config_path())
    if not path.exists():
        save_config(DEFAULT_CONFIG)
        return copy.deepcopy(DEFAULT_CONFIG)

    try:
        with path.open("r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}

    changed = False
    for k, v in DEFAULT_CONFIG.items():
        if k not in cfg:
            cfg[k] = copy.deepcopy(v)
            changed = True

    if changed or path != canonical_path:
        save_config(cfg)

    return cfg

def save_config(cfg: dict):
    """保存配置到 config.json。"""
    path = Path(get_config_path())
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存配置失败: {e}")
