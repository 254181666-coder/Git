
#!/usr/bin/env python3
import sys
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

SOURCE_DIR = PROJECT_ROOT / "data" / "source"
ARCHIVE_DIR = PROJECT_ROOT / "data" / "archive"
LOGS_DIR = PROJECT_ROOT / "data" / "logs"

def main():
    print("=" * 80)
    print("从归档恢复完整文件并重新导入")
    print("=" * 80)

    # 1. 先清空 source 目录
    print("\n1. 清空 source 目录...")
    for f in SOURCE_DIR.glob("*"):
        if f.name != "25nian.xlsx" and not f.name.startswith("."):
            f.unlink()

    # 2. 从 source_2026_05_02 恢复最新文件
    print("\n2. 从归档恢复最新文件...")
    archive_dir_0502 = ARCHIVE_DIR / "source_2026_05_02"
    for f in archive_dir_0502.glob("*"):
        if f.name != "25nian.xlsx":
            shutil.copy2(f, SOURCE_DIR / f.name)
            print(f"   恢复: {f.name}")

    # 3. 从 source_history 补充缺失文件
    print("\n3. 从 source_history 补充缺失文件...")
    source_history = ARCHIVE_DIR / "source_history"

    missing_files = [
        "card_detail_19863_20260501093046.csv",
        "order_export_19865_20260501093328.csv",
        "会员余额变动明细_2026_05_01.xlsx",
        "储值提成明细表_2026_05_01.xlsx",
        "商品提成明细表_2026_05_01.xlsx"
    ]

    for f_name in missing_files:
        f = source_history / f_name
        if f.exists():
            shutil.copy2(f, SOURCE_DIR / f_name)
            print(f"   恢复: {f_name}")

    # 4. 检查 source 目录文件
    print("\n4. 检查 source 目录文件:")
    for f in sorted(SOURCE_DIR.glob("*")):
        print(f"   {f.name}")

    # 5. 清理数据库错误的 5月2日数据
    print("\n5. 清理数据库错误的 5月2日数据...")
    import pymysql
    from config import MYSQL_CONFIG
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()

    print("   清理 order_detail 中 2026-05-02 数据...")
    cursor.execute("DELETE FROM order_detail WHERE data_date = '2026-05-02'")

    print("   清理 order_daily 中 2026-05-02 数据...")
    cursor.execute("DELETE FROM order_daily WHERE data_date = '2026-05-02'")

    print("   清理 product_sales_detail 中 2026-05-02 数据...")
    cursor.execute("DELETE FROM product_sales_detail WHERE data_date = '2026-05-02'")

    print("   清理 product_sales_summary 中 2026-05-02 数据...")
    cursor.execute("DELETE FROM product_sales_summary WHERE data_date = '2026-05-02'")

    conn.commit()
    cursor.close()
    conn.close()
    print("   清理完成！")

    # 6. 删除导入锁定
    print("\n6. 删除导入锁定...")
    for lock_file in LOGS_DIR.glob(".import_lock_20260502"):
        lock_file.unlink()
        print(f"   删除: {lock_file.name}")

    # 7. 运行完整导入
    print("\n7. 运行完整导入...")
    from scripts.daily_import_with_archive import main as full_import
    full_import()

    print("\n" + "=" * 80)
    print("完成！")
    print("=" * 80)

if __name__ == "__main__":
    main()

