
#!/usr/bin/env python3
import sys
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

def main():
    print("=" * 80)
    print("检查归档中的旧商品销售文件")
    print("=" * 80)

    archive_dir = Path(PROJECT_ROOT) / "data" / "archive"

    # 检查 source_history 里的旧文件
    history_dir = archive_dir / "source_history"
    for f in sorted(history_dir.glob("商品销售汇总*.xlsx"))[:3]:
        print(f"\n📁 {f.name}:")
        df = pd.read_excel(f, nrows=5)
        print(f"   列名: {df.columns.tolist()}")
        print(f"   前2行:\n{df.head(2).to_string()}")

    # 检查 source_2026_04_28 里的文件
    print("\n" + "=" * 80)
    print("检查 source_2026_04_28 里的文件:")
    old_dir = archive_dir / "source_2026_04_28"
    for f in sorted(old_dir.glob("商品销售汇总*.xlsx")):
        print(f"\n📁 {f.name}:")
        df = pd.read_excel(f, nrows=5)
        print(f"   列名: {df.columns.tolist()}")
        print(f"   前2行:\n{df.head(2).to_string()}")

    print("\n" + "=" * 80)
    print("检查完成！")
    print("=" * 80)

if __name__ == "__main__":
    main()

