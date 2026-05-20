"""
全局配置 — 每日报告项目
"""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def load_local_env():
    for filename in (".env.local", ".env"):
        path = PROJECT_ROOT / filename
        if not path.exists():
            continue
        with open(path, "r", encoding="utf-8") as env_file:
            for raw_line in env_file:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_local_env()

DB_PATH = PROJECT_ROOT / "database" / "daily_reports.db"
OUTPUT_DIR = PROJECT_ROOT / "data" / "output"
LOGS_DIR = PROJECT_ROOT / "data" / "logs"
ARCHIVE_DIR = PROJECT_ROOT / "data" / "archive"
DELIVERY_DIR = Path(os.getenv("DAILY_REPORT_DELIVERY_DIR", PROJECT_ROOT / "data" / "delivery"))

FUN360_BASE_URL = os.getenv("FUN360_BASE_URL", "https://open-api.fun360.cn")
FUN360_REPORT_BASE_URL = os.getenv("FUN360_REPORT_BASE_URL", FUN360_BASE_URL)
FUN360_DEFAULT_PHASE = "production"

BIG_CATEGORIES = ["酒水", "下酒菜", "干果", "氛围", "备品", "日场", "其他类"]

CATEGORY_MAP = {
    "啤酒": "酒水", "饮料": "酒水",
    "冷荤": "下酒菜", "鸭货": "下酒菜", "小海鲜": "下酒菜",
    "简餐": "下酒菜", "烤炸小食": "下酒菜",
    "优选坚果": "干果", "优选蜜饯": "干果", "优选零食": "干果", "精选拼盘": "干果", "雪糕": "干果",
    "礼炮": "氛围", "礼品": "氛围", "第三方": "氛围", "道具": "氛围", "果盘": "氛围",
    "备品": "备品", "纸抽": "备品", "开机套": "备品", "其他": "备品",
    "日场零食": "日场",
    "其他类": "其他类",
}

CATEGORY_KEYWORDS = [
    ("啤酒", "酒水"),
    ("饮料", "酒水"),
    ("冷荤", "下酒菜"),
    ("鸭货", "下酒菜"),
    ("小海鲜", "下酒菜"),
    ("简餐", "下酒菜"),
    ("烤炸小食", "下酒菜"),
    ("坚果", "干果"),
    ("蜜饯", "干果"),
    ("零食", "干果"),
    ("拼盘", "干果"),
    ("雪糕", "干果"),
    ("礼炮", "氛围"),
    ("第三方", "氛围"),
    ("道具", "氛围"),
    ("果盘", "氛围"),
    ("纸抽", "备品"),
    ("开机套", "备品"),
    ("日场零食", "日场"),
    ("日场", "日场"),
]


def resolve_big_category(category="", product_name=""):
    category = (category or "").strip()
    product_name = (product_name or "").strip()

    if category in CATEGORY_MAP:
        return CATEGORY_MAP[category]
    if category in BIG_CATEGORIES:
        return category

    for keyword, big_category in CATEGORY_KEYWORDS:
        if keyword and (keyword in category or keyword in product_name):
            return big_category

    return "其他类"
