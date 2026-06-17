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

# 先清空 source 文件夹
print("清理 source 文件夹...")
for f in source_dir.glob("*.xlsx"):
    f.unlink()
for f in source_dir.glob("*.csv"):
    f.unlink()

print("\n复制5月13日的数据文件...")

# 1. 日营业数据 - 找5月13日的文件
daily_file = None
for f in downloads_dir.glob("日营业数据表*.xlsx"):
    import pandas as pd
    try:
        df = pd.read_excel(f)
        if '日期' in df.columns:
            dates = df['日期'].dropna()
            if len(dates) > 0:
                first_date = dates.iloc[0]
                dt = pd.to_datetime(first_date)
                if dt.strftime('%Y-%m-%d') == '2026-05-13':
                    daily_file = f
                    print(f"✓ 日营业数据：{f.name}")
                    shutil.copy(f, source_dir / f.name)
                    break
    except Exception as e:
        pass

# 2. 会员储值订单表_2026_05_16.xlsx - 内容是5月13日
f = downloads_dir / "会员储值订单表_2026_05_16.xlsx"
if f.exists():
    print(f"✓ 会员储值订单：{f.name}")
    shutil.copy(f, source_dir / f.name)

# 3. 商品销售汇总_2026_05_16.xlsx - 内容是5月13日
f = downloads_dir / "商品销售汇总_2026_05_16.xlsx"
if f.exists():
    print(f"✓ 商品销售汇总：{f.name}")
    shutil.copy(f, source_dir / f.name)

# 4. 商品销售明细_-_商品+包厢维度_2026_05_16.xlsx - 包含5月13日
f = downloads_dir / "商品销售明细_-_商品+包厢维度_2026_05_16.xlsx"
if f.exists():
    print(f"✓ 商品销售明细：{f.name}")
    shutil.copy(f, source_dir / f.name)

print(f"\nsource 文件夹现在有：{[f.name for f in source_dir.glob('*') if f.is_file()]}")

# 检查是否有锁定文件
lock_file = logs_dir / ".import_lock_20260513"
if lock_file.exists():
    print(f"\n删除锁定文件：{lock_file.name}")
    lock_file.unlink()

# 检查是否有今天的锁定文件（如果今天是16号的话）
from datetime import date
today = date.today()
today_lock = logs_dir / f".import_lock_{today.strftime('%Y%m%d')}"
if today_lock.exists():
    print(f"删除今天的锁定文件：{today_lock.name}")
    today_lock.unlink()

# 运行导入脚本
print("\n运行数据导入...")
result = subprocess.run([sys.executable, str(PROJECT_ROOT / "scripts" / "import_data.py")], capture_output=True, text=True, cwd=str(PROJECT_ROOT))
print(result.stdout)
if result.stderr:
    print("错误输出：")
    print(result.stderr)

print("\n完成！")
