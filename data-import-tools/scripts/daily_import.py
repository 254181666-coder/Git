#!/usr/bin/env python3
"""
每日数据导入脚本
从 data/source 目录读取所有数据文件，导入到数据库
"""
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.import_data import main as import_main_data
from scripts.import_order_detail import main as import_order_detail
from scripts.import_member_balance import main as import_member_balance


def main():
    print("=" * 60)
    print(f"每日数据导入 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    print("\n【1/3】导入日营业、储值、商品销售数据...")
    import_main_data()

    print("\n【2/3】导入订单消费明细...")
    import_order_detail()

    print("\n【3/3】导入会员余额变动...")
    import_member_balance()

    print("\n" + "=" * 60)
    print("导入完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
