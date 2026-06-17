#!/usr/bin/env python3
"""检查5月1日-5月5日所有归档目录里的文件是否完整！"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

print("=" * 80)
print("📊 完整检查5月的归档文件情况")
print("=" * 80)

ARCHIVE_DIR = PROJECT_ROOT / "data" / "archive"
SOURCE_HISTORY_DIR = ARCHIVE_DIR / "source_history"

print("\n1️⃣ 检查 source_2026_05_01 到 source_2026_05_05 目录")
print("=" * 80)

# 每个日期应该有的关键文件
REQUIRED_FILE_PATTERNS = [
    'order_export',     # 订单文件
    '储值订单',
    '储值提成',
    '商品提成',
    '会员余额',
    '商品销售明细',
    '商品销售汇总',
    '日营业数据',
    'card_detail'
]

for day in range(1,6):
    date_str = f"2026_05_{day:02d}"
    archive_dir = ARCHIVE_DIR / f"source_{date_str}"
    print(f"\n{'='*80}")
    print(f"📂 {archive_dir.name}")
    print(f"{'='*80}")
    
    if archive_dir.exists():
        files = list(archive_dir.glob("*"))
        print(f"\n目录中共 {len(files)} 个文件：")
        
        # 检查每个关键类型的文件是否有
        found_files = {p: False for p in REQUIRED_FILE_PATTERNS}
        for f in files:
            print(f"  - {f.name}")
            for pattern in REQUIRED_FILE_PATTERNS:
                if pattern in f.name:
                    found_files[pattern] = True
        
        print(f"\n📌 关键文件检查：")
        all_ok = True
        for pattern in REQUIRED_FILE_PATTERNS:
            status = "✅" if found_files[pattern] else "❌"
            print(f"  {status} {pattern}")
            if not found_files[pattern]:
                all_ok = False
        
        if not all_ok:
            print(f"\n⚠️  该日期缺少关键文件！")
    
    else:
        print(f"\n❌ 目录不存在！")


print(f"\n{'='*80}")
print("2️⃣ 检查 source_history 目录的所有历史文件")
print(f"{'='*80}")

source_history_dir = ARCHIVE_DIR / "source_history"
if source_history_dir.exists():
    print(f"\nsource_history 目录共有 {len(list(source_history_dir.glob('*')))} 个文件：")
    
    order_files = list(source_history_dir.glob("order_export*"))
    print(f"\n   order_export 文件: {len(order_files)} 个")
    for f in sorted(order_files):
        print(f"    - {f.name}")

print(f"\n{'='*80}")

