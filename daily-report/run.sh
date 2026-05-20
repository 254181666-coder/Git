#!/bin/bash
# 每日报告项目启动脚本

cd "$(dirname "$0")"

case "$1" in
    start)
        echo "🚀 启动每日报告定时调度器..."
        nohup python3 run_tasks.py start > /dev/null 2>&1 &
        echo "✅ 调度器已启动"
        echo "使用 './run.sh stop' 停止"
        ;;
    stop)
        echo "🛑 停止每日报告定时调度器..."
        python3 run_tasks.py stop
        ;;
    run)
        echo "📊 立即执行日报生成..."
        python3 run_tasks.py run
        ;;
    status)
        if [ -f .scheduler_pid ]; then
            PID=$(cat .scheduler_pid)
            if kill -0 $PID 2>/dev/null; then
                echo "✅ 调度器正在运行 (PID: $PID)"
            else
                echo "❌ 调度器未运行"
            fi
        else
            echo "❌ 调度器未运行"
        fi
        ;;
    *)
        echo "用法: $0 {start|stop|run|status}"
        echo ""
        echo "  start  - 启动定时调度器"
        echo "  stop   - 停止定时调度器"
        echo "  run    - 立即执行一次日报生成"
        echo "  status - 查看调度器状态"
        exit 1
        ;;
esac