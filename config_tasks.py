"""
每日报告项目 - 任务配置
定时任务调度配置
"""

MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "Myww246364",
    "database": "ktv_analysis",
    "charset": "utf8mb4"
}

TASKS = {
    "enabled": True,
    "schedule": "0 10 * * *",
    "output_dir": "data/output",
    "archive_dir": "data/archive",
    "logs_dir": "data/logs",
    "delivery_dir": "/Users/ann/每日日报",

    "steps": {
        "import_data": {
            "enabled": False,
            "description": "数据导入（由Manpower项目负责）"
        },
        "generate_charts": {
            "enabled": True,
            "description": "生成轻舟日报图表（储值率分析图、收入分析综合图）"
        },
        "generate_product_report": {
            "enabled": True,
            "description": "生成商品销售分析报告"
        },
        "copy_to_delivery": {
            "enabled": True,
            "description": "复制报表到交付目录"
        }
    }
}

BIG_CATEGORIES = ["酒水", "下酒菜", "干果", "氛围", "备品", "日场", "其他"]

CATEGORY_MAP = {
    "啤酒": "酒水", "饮料": "酒水",
    "冷荤": "下酒菜", "鸭货": "下酒菜", "小海鲜": "下酒菜",
    "简餐": "下酒菜", "烤炸小食": "下酒菜",
    "优选坚果": "干果", "优选蜜饯": "干果", "优选零食": "干果", "精选拼盘": "干果",
    "礼品": "氛围", "第三方": "氛围", "道具": "氛围", "果盘": "氛围",
    "备品": "备品", "纸抽": "备品", "开机套": "备品",
    "日场零食": "日场",
}