#!/usr/bin/env python3
"""
每天23:00执行 - 清理和归档项目文件
清理当日数据文件，保持目录整洁
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import shutil

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import ARCHIVE_DIR, OUTPUT_DIR


def main():
    print("=" * 60)
    print(f"文件清理和归档 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 确保归档目录存在
    archive_date_dir = ARCHIVE_DIR / f"output_{datetime.now().strftime('%Y_%m_%d')}"
    archive_date_dir.mkdir(parents=True, exist_ok=True)
    
    cleaned_files = []
    skipped_files = []
    
    # 清理OUTPUT_DIR中超过7天的文件，但保留最近7天的
    print("\n检查输出目录...")
    seven_days_ago = datetime.now() - timedelta(days=7)
    
    for file_path in OUTPUT_DIR.iterdir():
        if not file_path.is_file() or file_path.name.startswith('.'):
            continue
        
        try:
            # 获取文件修改时间
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            if mtime < seven_days_ago:
                # 归档超过7天的文件
                dest = archive_date_dir / file_path.name
                shutil.move(str(file_path), str(dest))
                cleaned_files.append(file_path.name)
                print(f"  已归档: {file_path.name}")
            else:
                skipped_files.append(file_path.name)
        except Exception as e:
            print(f"  处理失败: {file_path.name} - {e}")
    
    print("\n" + "=" * 60)
    print(f"清理完成: {len(cleaned_files)} 个文件已归档")
    print(f"保留文件: {len(skipped_files)} 个")
    print("=" * 60)


if __name__ == "__main__":
    main()
