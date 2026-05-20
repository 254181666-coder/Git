#!/bin/bash
# 每日报告项目启动脚本

cd "$(dirname "$0")"
PYTHON="/Users/huatingyule/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"
if [ ! -x "$PYTHON" ]; then
  PYTHON="python3"
fi

case "$1" in
    start)
        echo "🚀 启动每日报告定时调度器..."
        "$PYTHON" run_tasks.py start
        ;;
    stop)
        echo "🛑 停止每日报告定时调度器..."
        "$PYTHON" run_tasks.py stop
        ;;
    run)
        echo "📊 立即执行日报生成..."
        "$PYTHON" run_tasks.py run
        ;;
    status)
        "$PYTHON" run_tasks.py status
        ;;
    health)
        if [ -n "$2" ]; then
            "$PYTHON" scripts/health_check.py "$2"
        else
            "$PYTHON" scripts/health_check.py
        fi
        ;;
    pipeline)
        shift
        "$PYTHON" scripts/run_openapi_pipeline.py "$@"
        ;;
    *)
        echo "用法: $0 {start|stop|run|status|health|pipeline}"
        echo ""
        echo "  start  - 启动定时调度器"
        echo "  stop   - 停止定时调度器"
        echo "  run    - 立即执行一次日报生成"
        echo "  status - 查看调度器状态"
        echo "  health - 执行健康检查"
        echo "  pipeline - 运行 OpenAPI raw -> mart 数据管道"
        exit 1
        ;;
esac
