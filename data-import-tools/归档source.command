#!/bin/zsh
cd "$(dirname "$0")"
source ~/.zprofile 2>/dev/null || true
python3 scripts/daily_archive.py
echo "按任意键退出..."
read -k 1 -s
