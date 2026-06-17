#!/usr/bin/env python3
from pathlib import Path
import shutil
import sys

HOME = Path.home()
DOWNLOADS = HOME / "Downloads"
PROJECT_ROOT = Path(__file__).resolve().parent
SOURCE_DIR = PROJECT_ROOT / "data" / "source"
ARCHIVE_DIR = PROJECT_ROOT / "data" / "archive"

print("=" * 80)
print("📂 检查下载文件夹")
print("=" * 80)

if DOWNLOADS.exists():
    print(f"\n📂 下载文件夹路径: {DOWNLOADS}")
    files = sorted(DOWNLOADS.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
    print(f"\n最近 20 个文件:\n")
    for f in files[:20]:
        if not f.name.startswith('.') and f.is_file():
            print(f"  - {f.name}")

print("\n" + "=" * 80)
print("🔍 查找日营业数据 Excel 文件")
print("=" * 80)

found_file = None

# 先检查下载文件夹
if DOWNLOADS.exists():
    for f in DOWNLOADS.iterdir():
        if f.is_file() and '日营业数据' in f.name and f.name.endswith('.xlsx'):
            found_file = f
            print(f"✅ 找到文件: {f.name}")
            break

# 也检查 source_history 文件夹，看看有没有
if not found_file and (ARCHIVE_DIR / "source_history").exists():
    for f in (ARCHIVE_DIR / "source_history").iterdir():
        if f.is_file() and '日营业数据' in f.name and f.name.endswith('.xlsx'):
            found_file = f
            print(f"✅ 找到归档文件: {f.name}")
            break

if found_file:
    print(f"\n📍 源文件: {found_file}")
    
    # 先删除那个 textClipping 文件
    text_clipping = SOURCE_DIR / "日营业数据表_20644.textClipping"
    if text_clipping.exists():
        print(f"\n🗑️ 删除 textClipping 文件: {text_clipping.name}")
        text_clipping.unlink()
    
    # 复制文件到 source 目录
    dest_file = SOURCE_DIR / found_file.name
    print(f"📦 复制到: {dest_file}")
    shutil.copy2(found_file, dest_file)
    print("✅ 复制完成！")

print("\n" + "=" * 80)
