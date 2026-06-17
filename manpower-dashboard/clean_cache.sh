#!/bin/bash

# 缓存清理脚本
echo "🧹 开始清理缓存文件..."

# 清理 .DS_Store 文件
echo "删除 .DS_Store 文件..."
find . -name ".DS_Store" -delete 2>/dev/null | head -20 | xargs -r rm -f
echo "✓ .DS_Store 文件已清除"

# 清理 Python 缓存目录
echo ""
echo "清理 Python 缓存 (__pycache__ 和 .pyc 文件..."
find . -type d -name "__pycache__" -prune -exec rm -rf {} \; 2>/dev/null || true
find . -name "*.pyc" -o -name "*.pyo" -delete 2>/dev/null || true
echo "✓ Python 缓存已清除"

# 清理临时文件
echo ""
echo "清理临时文件..."
find . -name "*~" -o -name "*.bak" -o -name "*.tmp" -delete 2>/dev/null || true
echo "✓ 临时文件已清除"

# 询问是否清理数据库备份
echo ""
read -p "是否清理数据库备份文件？(y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "正在清理数据库备份..."
    rm -f database/backups/* 2>/dev/null || true
    echo "✓ 数据库备份已清除"
fi

echo ""
echo "✅ 缓存清理完成！"
