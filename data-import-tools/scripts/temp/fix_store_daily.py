#!/usr/bin/env python3
from pathlib import Path
import shutil
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
SOURCE_DIR = PROJECT_ROOT / "data" / "source"
ARCHIVE_DIR = PROJECT_ROOT / "data" / "archive"

sys.path.insert(0, str(PROJECT_ROOT))

print("=" * 80)
print("🔧 修复 store_daily 表 05-09 和 05-10 的数据")
print("=" * 80)

# 1. 把 05-09 的日营业数据复制到 source 目录
file_09_daily = ARCHIVE_DIR / "source_2026_05_09" / "日营业数据表_20531.xlsx"
if file_09_daily.exists():
    dest = SOURCE_DIR / file_09_daily.name
    shutil.copy2(file_09_daily, dest)
    print(f"✅ 复制: {file_09_daily.name} -> source 目录")

# 2. 删除锁定文件，重新运行导入
LOGS_DIR = PROJECT_ROOT / "data" / "logs"
lock_files = list(LOGS_DIR.glob(".import_lock*"))
for f in lock_files:
    f.unlink()
    print(f"✅ 删除锁定文件: {f.name}")

print("\n" + "=" * 80)
print("📦 运行完整数据导入...")
print("=" * 80)

from scripts.import_data import main
main()

print("\n" + "=" * 80)
print("✅ 导入完成！现在验证...")
print("=" * 80)

from config import MYSQL_CONFIG
import pymysql

conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor()

dates_to_check = ["2026-05-07", "2026-05-08", "2026-05-09", "2026-05-10"]

print("\n【store_daily】")
for date_str in dates_to_check:
    cursor.execute("SELECT COUNT(*) FROM store_daily WHERE data_date = %s", (date_str,))
    count = cursor.fetchone()[0]
    status = "✅" if count > 0 else "❌"
    print(f"  {status} {date_str}: {count} 条")

cursor.close()
conn.close()

print("\n" + "=" * 80)
print("🧹 清理 data/source 目录，只保留今天的...")
print("=" * 80)

kept_files = []
moved_files = []

for f in SOURCE_DIR.iterdir():
    if f.name.startswith('.'):
        continue
    
    is_today = False
    if '20260510' in f.name or '_05_10.xlsx' in f.name or '2026_05_10' in f.name:
        is_today = True
    if f.name == '25nian.xlsx':
        is_today = True
    
    if is_today:
        kept_files.append(f)
    else:
        moved_files.append(f)

print(f"\n保留: {len(kept_files)} 个文件")
for f in kept_files:
    print(f"  ✅ {f.name}")

print(f"\n移动: {len(moved_files)} 个文件到归档目录...")
source_history = ARCHIVE_DIR / "source_history"
source_history.mkdir(exist_ok=True)

for f in moved_files:
    # 尝试找到对应日期目录
    date_str = None
    if '20260506' in f.name:
        date_str = '2026_05_06'
    elif '20260507' in f.name:
        date_str = '2026_05_07'
    elif '20260508' in f.name:
        date_str = '2026_05_08'
    elif '20260509' in f.name:
        date_str = '2026_05_09'
    
    dest_dir = None
    if date_str:
        dest_dir = ARCHIVE_DIR / f"source_{date_str}"
        dest_dir.mkdir(exist_ok=True)
    
    if dest_dir and dest_dir.exists():
        dest = dest_dir / f.name
    else:
        dest = source_history / f.name
    
    try:
        shutil.move(str(f), str(dest))
        print(f"  ✅ {f.name} -> {dest.parent.name}")
    except Exception as e:
        print(f"  ⚠️  {f.name}: {e}")

print("\n" + "=" * 80)
print("🎉 全部完成！")
print("=" * 80)
