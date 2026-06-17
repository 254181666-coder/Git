#!/usr/bin/env python3
import sys
import os
import time
import signal
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG, SOURCE_DIR, ARCHIVE_DIR, LOGS_DIR, PROJECT_ROOT

LOGS_DIR.mkdir(exist_ok=True)
BACKUP_DIR = PROJECT_ROOT / "data" / "backup"
BACKUP_DIR.mkdir(exist_ok=True)


class DataImportScheduler:
    def __init__(self):
        self.pid_file = PROJECT_ROOT / ".scheduler_pid"

    def save_pid(self):
        with open(self.pid_file, 'w') as f:
            f.write(str(os.getpid()))

    def load_pid(self):
        if not self.pid_file.exists():
            return None
        with open(self.pid_file, 'r') as f:
            return int(f.read().strip())

    def is_running(self):
        pid = self.load_pid()
        if not pid:
            return False
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def run_import(self):
        from scripts.import_data import main as run_import_data
        run_import_data()

    def run_backup(self):
        from scripts.backup_database import main as run_backup
        run_backup()

    def run_now(self):
        print("=" * 60)
        print(f"立即执行数据导入 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        try:
            self.run_import()
            print("\n数据导入完成")
            return True
        except Exception as e:
            print(f"\n数据导入失败: {e}")
            return False

    def backup_now(self):
        print("=" * 60)
        print(f"立即执行数据库备份 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        try:
            self.run_backup()
            print("\n数据库备份完成")
            return True
        except Exception as e:
            print(f"\n数据库备份失败: {e}")
            return False

    def start_scheduler(self):
        if self.is_running():
            print("定时调度器已在运行中")
            return

        print("=" * 60)
        print("数据导入定时调度器启动")
        print("=" * 60)
        print(f"调度时间:")
        print(f"  - 数据库备份: 每天 03:00")
        print(f"  - 数据导入: 每天 09:40")
        print("=" * 60)

        import schedule

        def job_with_log_import():
            try:
                print(f"\n执行任务: 数据导入 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
                self.run_import()
                print(f"任务完成")
            except Exception as e:
                print(f"任务失败: {e}")

        def job_with_log_backup():
            try:
                print(f"\n执行任务: 数据库备份 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
                self.run_backup()
                print(f"任务完成")
            except Exception as e:
                print(f"任务失败: {e}")

        schedule.every().day.at("03:00").do(job_with_log_backup)
        schedule.every().day.at("09:40").do(job_with_log_import)

        self.save_pid()

        print("调度器已启动")
        print("按 Ctrl+C 停止")

        try:
            while True:
                schedule.run_pending()
                time.sleep(60)
        except KeyboardInterrupt:
            if self.pid_file.exists():
                self.pid_file.unlink()
            print("\n调度器已停止")


def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  start       - 启动定时调度器")
        print("  run         - 立即执行一次数据导入")
        print("  backup      - 立即执行一次数据库备份")
        print("  stop        - 停止定时调度器")
        print("  status      - 查看调度器状态")
        sys.exit(1)

    cmd = sys.argv[1].lower()
    scheduler = DataImportScheduler()

    if cmd == "stop":
        pid = scheduler.load_pid()
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
                print("定时调度器已停止")
            except OSError:
                print("进程不存在")
        if scheduler.pid_file.exists():
            scheduler.pid_file.unlink()

    elif cmd == "start":
        scheduler.start_scheduler()

    elif cmd == "run":
        scheduler.run_now()

    elif cmd == "backup":
        scheduler.backup_now()

    else:
        print(f"未知命令: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()