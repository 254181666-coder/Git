#!/bin/zsh
cd "$(dirname "$0")/.."
source ~/.zprofile 2>/dev/null || true
exec /usr/bin/python3 scripts/daily_import_with_archive.py
