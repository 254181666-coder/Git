#!/bin/bash
cd "$(dirname "$0")"

case "$1" in
    start)
        echo "启动数据导入定时调度器..."
        nohup python3 scripts/run_tasks.py start > /dev/null 2>&1 &
        echo "调度器已启动"
        ;;
    stop)
        echo "停止数据导入定时调度器..."
        python3 scripts/run_tasks.py stop
        ;;
    run)
        echo "立即执行数据导入..."
        python3 scripts/run_tasks.py run
        ;;
    backup)
        echo "立即执行数据库备份..."
        python3 scripts/run_tasks.py backup
        ;;
    status)
        if [ -f .scheduler_pid ]; then
            PID=$(cat .scheduler_pid)
            if kill -0 $PID 2>/dev/null; then
                echo "调度器正在运行 (PID: $PID)"
            else
                echo "调度器未运行"
            fi
        else
            echo "调度器未运行"
        fi
        ;;
    *)
        echo "用法: $0 {start|stop|run|backup|status}"
        exit 1
        ;;
esac