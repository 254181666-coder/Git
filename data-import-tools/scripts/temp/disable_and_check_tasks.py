#!/usr/bin/env python3
import subprocess
from pathlib import Path

print("=" * 80)
print("1. 检查 launchd 任务状态")
print("=" * 80)

# 列出所有任务
try:
    result = subprocess.run(
        ["launchctl", "list"],
        capture_output=True,
        text=True
    )
    for line in result.stdout.split("\n"):
        if "com.ktv" in line:
            print(line)
except Exception as e:
    print(f"错误: {e}")

print("\n" + "=" * 80)
print("2. 检查任务配置文件位置")
print("=" * 80)

project_root = Path(__file__).resolve().parent
print(f"项目根目录: {project_root}")

plist_files = list(project_root.glob("com.ktv.*.plist"))
for f in plist_files:
    print(f"  - {f.name}")

print("\n" + "=" * 80)
print("3. 停止和禁用 com.ktv.dailyarchive")
print("=" * 80)

# 尝试停止和卸载任务
archive_plist = project_root / "com.ktv.dailyarchive.plist"

try:
    print("- 停止任务:")
    subprocess.run(["launchctl", "stop", "com.ktv.dailyarchive"], check=False)
    print("- 从 launchd 卸载任务:")
    subprocess.run(["launchctl", "unload", "-w", str(archive_plist)], check=False)
    print("✅ dailyarchive 任务已禁用！")
except Exception as e:
    print(f"  警告: {e}")

print("\n" + "=" * 80)
print("4. 确认状态")
print("=" * 80)

try:
    result = subprocess.run(
        ["launchctl", "list"],
        capture_output=True,
        text=True
    )
    print("\n任务列表中还有 com.ktv 开头的吗:")
    for line in result.stdout.split("\n"):
        if "com.ktv" in line:
            print(line)
except Exception as e:
    print(f"错误: {e}")

print("\n" + "=" * 80)
print("5. 检查 stored_commission 和 product_commission 表")
print("=" * 80)

import sys
sys.path.insert(0, str(project_root))
from config import MYSQL_CONFIG
import pymysql

conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor()

for table in ['stored_commission', 'product_commission']:
    print(f"\n【{table}】")
    print("-" * 80)
    try:
        print("表结构:")
        cursor.execute(f"DESCRIBE {table}")
        for col in cursor.fetchall():
            print(f"  {col}")
            
        print("\n前5条数据:")
        cursor.execute(f"SELECT * FROM {table} LIMIT 5")
        for row in cursor.fetchall():
            print(f"  {row}")
            
    except Exception as e:
        print(f"  错误: {e}")

cursor.close()
conn.close()

print("\n" + "=" * 80)
print("完成！")
print("=" * 80)
