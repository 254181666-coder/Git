#!/usr/bin/env python3
"""
每天23:00执行 - 归档source目录文件
将当天导入完成的数据移动到备份文件夹，source清空
"""
import sys
from pathlib import Path
from datetime import datetime
import shutil

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import ARCHIVE_DIR


def main():
    print("=" * 60)
    print(f"数据归档 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    source_dir = PROJECT_ROOT / 'data' / 'source'
    archive_dir = ARCHIVE_DIR / 'source_history'

    if not archive_dir.exists():
        archive_dir.mkdir(parents=True)

    files = list(source_dir.glob('*'))
    archived = []
    failed = []

    for f in files:
        if f.name.startswith('.'):
            continue
        if f.name == '25nian.xlsx':
            print(f'  跳过(保留): {f.name}')
            continue
        try:
            dest = archive_dir / f.name
            shutil.move(str(f), str(dest))
            archived.append(f.name)
            print(f'  已归档: {f.name}')
        except Exception as e:
            failed.append((f.name, str(e)))
            print(f'  归档失败: {f.name} - {e}')

    print()
    print(f"归档完成: {len(archived)}个成功, {len(failed)}个失败")
    print("=" * 60)


if __name__ == "__main__":
    main()
