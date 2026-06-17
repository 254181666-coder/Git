#!/usr/bin/env python3
from pathlib import Path
import pandas as pd

HOME = Path.home()
DOWNLOADS = HOME / "Downloads"

print("=" * 80)
print("📂 检查下载文件夹里所有 Excel 文件")
print("=" * 80)

if DOWNLOADS.exists():
    files = sorted(DOWNLOADS.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
    for f in files:
        if not f.name.startswith('.') and f.is_file() and f.name.endswith('.xlsx'):
            print(f"\n📄 {f.name}")
            try:
                df = pd.read_excel(f)
                if '日期' in df.columns:
                    dates = df['日期'].dropna().unique()
                    print(f"   包含日期: {sorted(dates)}")
                if '门店' in df.columns:
                    stores = df['门店'].dropna().unique()
                    print(f"   包含门店: {len(stores)} 家")
            except Exception as e:
                print(f"   读取失败: {e}")

print("\n" + "=" * 80)
