"""
全局配置 — 统一管理项目路径、常量、分类、数据库连接
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "database" / "ktv_analysis.db"
SOURCE_DIR = PROJECT_ROOT / "data" / "source"
OUTPUT_DIR = PROJECT_ROOT / "data" / "output"

# 数据库切换开关：True=MySQL，False=SQLite（本地开发用）
USE_MYSQL = True

# MySQL 连接配置
MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "CHANGE_ME_MYSQL_PASSWORD",
    "database": "ktv_analysis",
    "charset": "utf8mb4"
}

# 大分类列表（按你提供的顺序）
BIG_CATEGORIES = ['酒水', '下酒菜', '干果', '氛围', '备品', '日场', '其他']

# 商品分类映射规则
CATEGORY_MAP = {
    # 酒水
    '啤酒': '酒水', '饮料': '酒水',
    # 下酒菜
    '冷荤': '下酒菜', '鸭货': '下酒菜', '小海鲜': '下酒菜',
    '简餐': '下酒菜', '烤炸小食': '下酒菜',
    # 干果
    '优选坚果': '干果', '优选蜜饯': '干果', '优选零食': '干果', '精选拼盘': '干果',
    # 氛围
    '礼品': '氛围', '第三方': '氛围', '道具': '氛围', '果盘': '氛围',
    # 备品
    '备品': '备品', '纸抽': '备品', '开机套': '备品',
    # 日场
    '日场零食': '日场',
}

STORE_PREFIXES = ['私人订制KTV', '私人订制 KTV', '糖果华庭KTV', '糖果华庭 KTV']
EXCLUDE_STORES = {'总部', '临河街店'}
NAME_MAP = {'江南秀': '松原一店', '斯堡特': '松原二店'}

TAB_OPTIONS = ["📊 经营总览", "🍺 商品销售分析", "🎤 包房销售分析", "👥 人效分析", "📈 同比分析", "📋 客户存留分析", "📊 日报分析"]

# 储值卡级配置
CARD_LEVEL_INTERVALS = [
    (0, 1000, '普卡'),
    (1000, 3000, '银卡'),
    (3000, 5000, '金卡'),
    (5000, 10000, '铂金卡'),
    (10000, 999999999, '钻石卡')
]

# 颜色配置
COLOR_YOY_2025 = '#2E86AB'
COLOR_YOY_2026 = '#A23B72'
COLOR_CATEGORY = {
    '酒水': '#d62728',
    '下酒菜': '#1f77b4',
    '干果': '#ff7f0e',
    '氛围': '#2ca02c',
    '备品': '#9467bd',
    '日场': '#8c564b',
    '其他': '#7f7f7f'
}
COLOR_PERIOD = {
    '日场': '#1f77b4',
    '黄金场': '#ff7f0e',
    '午夜场': '#2ca02c'
}
