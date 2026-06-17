#!/usr/bin/env python3
import sys
from pathlib import Path
import shutil
import subprocess

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

downloads_dir = Path("/Users/ann/Downloads")
source_dir = PROJECT_ROOT / "data" / "source"
logs_dir = PROJECT_ROOT / "data" / "logs"

# 先清空 source 文件夹（保留已有的，但确保我们只放入需要的文件）
print("清理 source 文件夹...")
for f in source_dir.glob("*.xlsx"):
    f.unlink()
for f in source_dir.glob("*.csv"):
    f.unlink()

# 查找5月13日的日营业数据文件
print("\n复制5月13日的数据文件...")
daily_file = None
for f in downloads_dir.glob("日营业数据表*.xlsx"):
    import pandas as pd
    try:
        df = pd.read_excel(f)
        if '日期' in df.columns:
            dates = df['日期'].dropna()
            if len(dates) > 0:
                file_date = str(dates.iloc[0])[:10]
                if file_date == '2026-05-13':
                    daily_file = f
                    print(f"找到5月13日日营业数据：{f.name}")
                    shutil.copy(f, source_dir / f.name)
                    break
    except Exception as e:
        print(f"跳过 {f.name}：{e}")

if not daily_file:
    print("没有找到5月13日的日营业数据文件！")
    sys.exit(1)

# 检查是否有锁定文件
lock_file = logs_dir / ".import_lock_20260513"
if lock_file.exists():
    print(f"\n删除锁定文件：{lock_file.name}")
    lock_file.unlink()

# 运行导入脚本
print("\n运行数据导入...")
result = subprocess.run([sys.executable, str(PROJECT_ROOT / "scripts" / "import_data.py")], capture_output=True, text=True, cwd=str(PROJECT_ROOT))
print(result.stdout)
if result.stderr:
    print("错误输出：")
    print(result.stderr)

print("\n完成！")
