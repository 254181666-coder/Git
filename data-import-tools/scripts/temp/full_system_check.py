#!/usr/bin/env python3
"""完整系统检查：定时任务、归档、数据库表、导入日志"""
import sys
from pathlib import Path
from datetime import datetime
from config import MYSQL_CONFIG
import pymysql

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

print("=" * 80)
print("📊 完整系统检查报告")
print("=" * 80)

print("\n" + "=" * 80)
print("1️⃣  检查定时任务：")
print("=" * 80)

print("\n📅 检查定时任务配置文件：")
plist_files = list(PROJECT_ROOT.glob("*.plist"))
for plist in plist_files:
    print(f"\n📂 {plist.name}")
    with open(plist, 'r') as f:
        content = f.read()
        for keyword in ['ProgramArguments', 'StartCalendarInterval', 'Hour', 'Minute']:
            if keyword in content:
                print(f"  {keyword}")
    print(f"  文件内容预览：\n{content[:600]}")

print("\n" + "=" * 80)
print("2️⃣  检查所有归档目录：")
print("=" * 80)

ARCHIVE_DIR = PROJECT_ROOT / "data" / "archive"
SOURCE_HISTORY_DIR = ARCHIVE_DIR / "source_history"

print(f"\n📂 ARCHIVE_DIR: {ARCHIVE_DIR}")
print(f"  {ARCHIVE_DIR.exists()}, 子目录：")
for subdir in sorted(ARCHIVE_DIR.iterdir()):
    if subdir.is_dir():
        print(f"    - {subdir.name}")

print(f"\n📂 source_history 目录: {SOURCE_HISTORY_DIR}")
if SOURCE_HISTORY_DIR.exists():
    print(f"  文件数：{len(list(SOURCE_HISTORY_DIR.glob('*')))}")
    files = sorted(SOURCE_HISTORY_DIR.glob("*"))
    print(f"\n  前20个文件：")
    for f in files[:20]:
        print(f"    - {f.name}")

print("\n" + "=" * 80)
print("3️⃣  检查数据库表（SHOW TABLES）：")
print("=" * 80)

conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor()

cursor.execute("SHOW TABLES")
tables = [row[0] for row in cursor.fetchall()]
print(f"\n数据库中的表：{tables}")

print("\n详细检查每个表的结构和数据：")
for table in tables:
    print(f"\n{'='*80}")
    print(f"【{table}】")
    print(f"{'='*80}")

    try:
        cursor.execute(f"DESCRIBE {table}")
        print("\n表结构：")
        for col in cursor.fetchall():
            print(f"  {col}")

        # 检查表有多少数据
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        total = cursor.fetchone()[0]
        print(f"\n总记录数：{total}")

        # 检查有没有日期相关字段和最新的数据
        date_fields = []
        cursor.execute(f"DESCRIBE {table}")
        for col in cursor.fetchall():
            col_name = col[0]
            if 'date' in col_name.lower() or 'time' in col_name.lower():
                date_fields.append(col_name)

        if date_fields:
            print(f"\n日期相关字段：{date_fields}")
            for df in date_fields:
                try:
                    cursor.execute(f"""
                        SELECT MIN({df}), MAX({df}), COUNT(DISTINCT {df})
                        FROM {table}
                        WHERE {df} IS NOT NULL
                    """)
                    min_val, max_val, distinct = cursor.fetchone()
                    print(f"  {df}: {min_val} ~ {max_val}, 共 {distinct} 个不同值")

                    if min_val and max_val:
                        cursor.execute(f"""
                            SELECT {df}, COUNT(*) as cnt
                            FROM {table}
                            WHERE {df} >= '2026-05-01'
                            GROUP BY {df}
                            ORDER BY {df}
                        """)
                        may_data = cursor.fetchall()
                        if may_data:
                            print(f"\n    5月数据：")
                            for row in may_data:
                                print(f"      {row[0]}: {row[1]} 条")

                except Exception as e:
                    pass
        else:
            print("\n  没有明显的日期相关字段")
            # 看看前5条数据
            cursor.execute(f"SELECT * FROM {table} LIMIT 5")
            print("\n  前5条数据：")
            for row in cursor.fetchall():
                print(f"    {row}")

    except Exception as e:
        print(f"  ❌ 检查出错：{e}")

print("\n" + "=" * 80)
print("4️⃣  检查最近的导入日志：")
print("=" * 80)

LOG_DIR = PROJECT_ROOT / "data" / "logs"

if LOG_DIR.exists():
    log_files = sorted(LOG_DIR.glob("*.log"))
    print(f"\n共有 {len(log_files)} 个日志文件")
    for log in log_files[-7:]:  # 最近7天的
        print(f"\n--- {log.name} ---")
        content = None
        for enc in ['utf-8', 'gbk', 'latin1']:
            try:
                with open(log, 'r', encoding=enc) as f:
                    content = f.readlines()
                break
            except:
                continue
        
        if content:
            for line in content[-30:]:
                print(f"  {line[:80].strip()}")
else:
    print("\n❌ LOG_DIR 不存在！")

cursor.close()
conn.close()

print("\n" + "=" * 80)
print("✅ 完整系统检查完成！")
print("=" * 80)

