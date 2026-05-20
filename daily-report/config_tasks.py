"""
每日报告项目 - 任务配置
定时任务调度配置
"""

from src.config import ARCHIVE_DIR, BIG_CATEGORIES, CATEGORY_MAP, DELIVERY_DIR, LOGS_DIR, OUTPUT_DIR

TASKS = {
    "enabled": True,
    "schedule": "0 10 * * *",
    "output_dir": str(OUTPUT_DIR),
    "archive_dir": str(ARCHIVE_DIR),
    "logs_dir": str(LOGS_DIR),
    "delivery_dir": str(DELIVERY_DIR),

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
