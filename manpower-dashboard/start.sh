#!/bin/bash

# 综合经营数据看板 - 启动脚本

cd "$(dirname "$0")"

echo "🚀 启动综合经营数据看板..."

# 检查是否存在 .env 文件
if [ ! -f .env ]; then
    echo "⚠️  未找到 .env 文件，正在从 .env.example 创建..."
    cp .env.example .env
    echo "请编辑 .env 文件配置数据库连接"
fi

# 激活虚拟环境（如果存在）
if [ -d "bin" ]; then
    echo "📦 激活虚拟环境..."
    source bin/activate
fi

# 检查是否使用生产配置
if [ "$1" = "prod" ]; then
    echo "🔧 使用生产配置启动..."
    export STREAMLIT_CONFIG_FILE=.streamlit/config.prod.toml
    streamlit run app.py --server.port 8502 --server.address 0.0.0.0
else
    echo "🔧 使用开发配置启动..."
    streamlit run app.py --server.port 8502
fi
