#!/bin/bash
cd /Users/huatingyule/Desktop/每日报告
PYTHON="/Users/huatingyule/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"
if [ ! -x "$PYTHON" ]; then
  PYTHON="python3"
fi
"$PYTHON" scripts/daily_report.py "$@"
