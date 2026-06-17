#!/usr/bin/env python3
"""
数据库备份脚本
每天凌晨执行，备份 ktv_analysis 数据库
"""
import os
import sys
import shutil
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG, PROJECT_ROOT

BACKUP_DIR = PROJECT_ROOT / "data" / "backup"
BACKUP_DIR.mkdir(exist_ok=True)


def get_backup_filename():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"ktv_analysis_{timestamp}.sql"


def backup_database():
    backup_file = BACKUP_DIR / get_backup_filename()
    temp_file = BACKUP_DIR / "temp_backup.sql"

    host = MYSQL_CONFIG["host"]
    port = MYSQL_CONFIG["port"]
    user = MYSQL_CONFIG["user"]
    password = MYSQL_CONFIG["password"]
    database = MYSQL_CONFIG["database"]

    mysqldump_cmd = f"mysqldump -h{host} -P{port} -u{user} -p{password} {database}"

    print(f"开始备份数据库: {database}")
    print(f"备份文件: {backup_file}")

    result = os.system(f"{mysqldump_cmd} > {temp_file}")

    if result == 0 and temp_file.exists():
        temp_file.rename(backup_file)
        file_size = backup_file.stat().st_size
        print(f"备份成功! 文件大小: {file_size / 1024:.2f} KB")
        cleanup_old_backups()
        return True
    else:
        print("备份失败!")
        if temp_file.exists():
            temp_file.unlink()
        return False


def cleanup_old_backups():
    max_backups = 7
    backups = sorted(BACKUP_DIR.glob("ktv_analysis_*.sql"), key=lambda f: f.stat().st_mtime)
    if len(backups) > max_backups:
        to_delete = backups[:-max_backups]
        print(f"清理旧备份文件 ({len(to_delete)} 个)...")
        for f in to_delete:
            f.unlink()
            print(f"  已删除: {f.name}")


def main():
    print("=" * 60)
    print(f"数据库备份 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    success = backup_database()
    print("=" * 60)
    if success:
        print("备份任务完成")
    else:
        print("备份任务失败")
    print("=" * 60)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
