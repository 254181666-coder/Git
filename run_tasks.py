#!/usr/bin/env python3
"""
每日报告项目 - 定时任务调度器
负责每天定时生成报表

使用方法:
    python3 run_tasks.py start     # 启动定时调度器
    python3 run_tasks.py run      # 立即执行一次日报生成
    python3 run_tasks.py stop     # 停止定时调度器
"""
import sys
import os
import time
import signal
import subprocess
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from config_tasks import TASKS, MYSQL_CONFIG
except ImportError:
    print("❌ 找不到 config_tasks.py 配置文件")
    sys.exit(1)


class DailyReportScheduler:
    def __init__(self):
        self.process = None
        self.pid_file = PROJECT_ROOT / ".scheduler_pid"

    def save_pid(self):
        if self.process:
            with open(self.pid_file, 'w') as f:
                f.write(str(self.process.pid))

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

    def stop(self):
        pid = self.load_pid()
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
                print("🛑 定时调度器已停止")
            except OSError:
                print("⚠️ 进程不存在")
        if self.pid_file.exists():
            self.pid_file.unlink()

    def check_data_ready(self, target_date):
        """检查数据是否就绪（检查store_daily表）"""
        try:
            from src.database import query
            sql = "SELECT COUNT(*) as cnt FROM store_daily WHERE data_date = %s"
            df = query(sql, (target_date,))
            if not df.empty and df.iloc[0]['cnt'] > 0:
                return True
            return False
        except Exception as e:
            print(f"   ⚠️  数据检查失败：{e}")
            return False
    
    def run_daily_report(self):
        """执行日报生成主流程。"""
        from datetime import date, timedelta
        from scripts.daily_report import main as run_report

        target_date = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
        print(f"📊 生成日报：{target_date}")
        result = run_report([target_date])
        if result != 0:
            raise RuntimeError(f"日报生成失败，退出码: {result}")

    def generate_charts_only(self, target_date=None):
        """仅生成轻舟日报图表（使用数据库版本，完全独立）"""
        if target_date is None:
            from datetime import date, timedelta
            target_date = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')

        from scripts.generate_qingzhou_charts import main as generate_charts
        sys.argv = ['generate_qingzhou_charts.py', target_date]
        generate_charts()

    def generate_product_report_only(self, target_date=None):
        """仅生成商品销售报告"""
        if target_date is None:
            from datetime import date, timedelta
            target_date = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')

        from scripts.generate_product_sales_report import generate_html_report
        generate_html_report(target_date)

    def run_now(self):
        """立即执行一次完整的日报生成"""
        print("=" * 60)
        print(f"📊 立即执行日报生成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        try:
            self.run_daily_report()
            print("\n✅ 日报生成完成")
            return True
        except Exception as e:
            print(f"\n❌ 日报生成失败: {e}")
            return False

    def start_scheduler(self):
        """启动定时调度器"""
        if self.is_running():
            print("⚠️ 定时调度器已在运行中")
            return

        print("=" * 60)
        print("⏰ 每日报告定时调度器启动")
        print("=" * 60)
        print(f"调度时间:")
        print(f"  - 日报生成: 每天 10:10")
        print(f"  - 文件清理: 每天 23:00")
        print(f"任务内容:")
        print(f"  - 生成轻舟日报图表 + 商品销售报告")
        print(f"  - 清理归档7天前的输出文件")
        print("=" * 60)

        self.process = subprocess.Popen(
            [sys.executable, __file__, "_scheduler_loop"],
            cwd=PROJECT_ROOT
        )
        self.save_pid()

        print("✅ 调度器已启动（后台运行）")
        print(f"📋 进程ID: {self.process.pid}")
        print("💡 可以安全关闭终端窗口")
        print("   如需停止: python3 run_tasks.py stop")

    def run_cleanup(self):
        """执行文件清理任务"""
        print(f"\n{'='*50}")
        print(f"🧹 执行任务: 文件清理 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
        try:
            from scripts.daily_cleanup import main as cleanup_main
            cleanup_main()
            print(f"✅ 清理任务完成")
        except Exception as e:
            print(f"❌ 清理任务失败: {e}")
        print(f"{'='*50}\n")

    def scheduler_loop(self):
        """调度器循环（供子进程使用）"""
        import schedule
        import time

        def job_report_with_log():
            from datetime import datetime
            try:
                print(f"\n{'='*50}")
                print(f"⏰ 执行任务: 日报生成 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
                self.run_daily_report()
                print(f"✅ 任务完成")
            except Exception as e:
                print(f"❌ 任务失败: {e}")
            print(f"{'='*50}\n")

        def job_cleanup_with_log():
            from datetime import datetime
            try:
                print(f"\n{'='*50}")
                print(f"🧹 执行任务: 文件清理 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
                self.run_cleanup()
                print(f"✅ 任务完成")
            except Exception as e:
                print(f"❌ 任务失败: {e}")
            print(f"{'='*50}\n")

        schedule.every().day.at("10:10").do(job_report_with_log)
        schedule.every().day.at("23:00").do(job_cleanup_with_log)

        while True:
            schedule.run_pending()
            time.sleep(60)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\n可用命令:")
        print("  start   - 启动定时调度器（后台运行）")
        print("  run     - 立即执行一次日报生成")
        print("  stop    - 停止定时调度器")
        sys.exit(1)

    cmd = sys.argv[1].lower()
    scheduler = DailyReportScheduler()

    if cmd == "stop":
        scheduler.stop()

    elif cmd == "start":
        scheduler.start_scheduler()

    elif cmd == "run":
        scheduler.run_now()

    elif cmd == "_scheduler_loop":
        scheduler.scheduler_loop()

    else:
        print(f"❓ 未知命令: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
